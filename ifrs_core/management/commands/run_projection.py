from __future__ import annotations

from decimal import Decimal, getcontext
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from contracts.models import ContractGroup
from assumptions.models import DiscountCurve, CurveType, RiskAdjustmentParams, RAMethod
from results.models import ResultSet, RollforwardLine, Component, MovementType

getcontext().prec = 28


def _dfs(rates: list[float], start_idx: int = 0) -> list[Decimal]:
    dfs: list[Decimal] = []
    acc = Decimal("1.0")
    for r in rates[start_idx:]:
        acc *= (Decimal("1.0") + Decimal(str(r)))
        dfs.append(Decimal("1.0") / acc)
    return dfs


def _pv(cfs: list[Decimal], dfs: list[Decimal]) -> Decimal:
    total = Decimal("0.0")
    for t, cf in enumerate(cfs):
        total += cf * dfs[t]
    return total


class Command(BaseCommand):
    help = "Multi-period projection (toy): initial recognition (t=0) + t=1..N rollforwards."

    def handle(self, *args, **options):
        group = (
            ContractGroup.objects.select_related("portfolio", "product")
            .order_by("id")
            .first()
        )
        if not group:
            raise CommandError("No ContractGroup found. Load contracts fixtures first.")

        li_curve = DiscountCurve.objects.filter(curve_type=CurveType.LOCKED_IN).first()
        curr_curve = DiscountCurve.objects.filter(curve_type=CurveType.CURRENT).first()
        if not (li_curve and curr_curve):
            raise CommandError("Missing DiscountCurve(s). Load assumptions fixtures.")

        ra_params = RiskAdjustmentParams.objects.first()
        if not ra_params or ra_params.method != RAMethod.TOY_FACTOR:
            raise CommandError("Need RiskAdjustmentParams with method=TOY_FACTOR for Phase 2 step 1.")

        # Guards
        n = group.coverage_term_years
        if len(li_curve.rates) < n or len(curr_curve.rates) < n:
            raise CommandError(
                f"Curve length too short: need ≥{n} rates for both curves."
            )

        # Toy projections
        prem_per = Decimal(group.written_premium) / Decimal(group.premium_term_years or 1)
        premiums = [prem_per if t < group.premium_term_years else Decimal("0.0") for t in range(n)]
        claims = [prem_per * Decimal("0.60") for _ in range(n)]
        expenses = [prem_per * Decimal("0.05") for _ in range(n)]
        acq_t0 = Decimal(group.written_premium) * Decimal("0.10")
        ra_factor = Decimal(ra_params.factor)
        ra_vec = [c * ra_factor for c in claims]

        # DFs (locked-in and current)
        dfs_curr0 = _dfs(curr_curve.rates, 0)
        dfs_li = _dfs(li_curve.rates, 0)

        # Initial recognition (t=0)
        pv_in = _pv(premiums, dfs_curr0)
        pv_out = _pv([c + e for c, e in zip(claims, expenses)], dfs_curr0) + acq_t0  # include t0 acquisition
        pv_ra = _pv(ra_vec, dfs_curr0)
        fcf0 = pv_out - pv_in + pv_ra

        csm0 = -fcf0 if fcf0 <= 0 else Decimal("0.0")
        loss0 = fcf0 if fcf0 > 0 else Decimal("0.0")

        # Create/overwrite a ResultSet for today
        meas_date = timezone.now().date()
        rs, _ = ResultSet.objects.update_or_create(
            group=group,
            scenario_name="BASE",
            measurement_date=meas_date,
            defaults={
                "code": f"PROJ_{group.code}_{meas_date.isoformat()}",
                "name": f"Projection run for {group.name}",
                "currency": group.currency,
                "notes": "Phase 2 step 1: toy multi-period projection.",
            },
        )
        # Clear old lines
        rs.lines.all().delete()

        def put(t: int, comp: str, amt: Decimal, mt: MovementType | str = MovementType.OTHER):
            RollforwardLine.objects.update_or_create(
                result=rs,
                period_index=t,
                component=comp,
                defaults={
                    "amount": amt.quantize(Decimal("0.000001")),
                    "movement_type": MovementType(mt).value if isinstance(mt, str) else mt.value,
                },
            )


        # Record t=0
        put(0, Component.INIT_PV_IN, pv_in, MovementType.INIT)
        put(0, Component.INIT_PV_OUT, pv_out, MovementType.INIT)
        put(0, Component.INIT_RA, pv_ra, MovementType.INIT)
        put(0, Component.INIT_FCF, fcf0, MovementType.INIT)
        put(0, Component.INIT_CSM, csm0, MovementType.INIT)
        put(0, Component.INIT_LOSS_COMP, loss0, MovementType.INIT)


        # Equal coverage units (toy)
        cu_share = Decimal("1.0") / Decimal(n)
        ra_open = pv_ra
        csm_open = csm0

        # Iterate periods t = 1..n
        for t in range(1, n + 1):
            # Interest on CSM at locked-in rate r_{t-1}
            li_rate = Decimal(str(li_curve.rates[t - 1]))
            csm_int = csm_open * li_rate
            csm_after_int = csm_open + csm_int
            csm_rel = csm_after_int * cu_share
            csm_close = csm_after_int - csm_rel

            # RA release proportional (equal share)
            ra_rel = ra_open * cu_share
            ra_close = ra_open - ra_rel

            # Service amounts (expected) in period t
            exp_prem = premiums[t - 1]          # optional diagnostic (not used in IFRS revenue)
            exp_claims = claims[t - 1]
            exp_exp = expenses[t - 1]
            acq_amort = acq_t0 * cu_share       # spread by CU (toy)

            # Revenue / service result (IFRS toy mapping)
            revenue = csm_rel + ra_rel + exp_claims + exp_exp + acq_amort
            service_exp = exp_claims + exp_exp + acq_amort
            service_result = revenue - service_exp  # = CSM_rel + RA_rel

            # BEL open = PV of remaining (t..n-1) on current curve
            dfs_curr_t = _dfs(curr_curve.rates, t)
            pv_in_rem = _pv(premiums[t:], dfs_curr_t)
            pv_out_rem = _pv([c + e for c, e in zip(claims[t:], expenses[t:])], dfs_curr_t)
            pv_ra_rem = _pv(ra_vec[t:], dfs_curr_t)
            bel_open = pv_out_rem - pv_in_rem + pv_ra_rem

            # Finance result split: unwind on BEL_open (current) + interest on CSM (locked-in)
            curr_rate = Decimal(str(curr_curve.rates[t - 1]))
            bel_int = bel_open * curr_rate
            fin_result = bel_int + csm_int

            # BEL close = PV of remaining (t+1..n-1)
            if t < n:
                dfs_curr_t1 = _dfs(curr_curve.rates, t + 1)
                bel_close = (
                    _pv([c + e for c, e in zip(claims[t + 1:], expenses[t + 1:])], dfs_curr_t1)
                    - _pv(premiums[t + 1:], dfs_curr_t1)
                    + _pv(ra_vec[t + 1:], dfs_curr_t1)
                )
            else:
                bel_close = Decimal("0.0")

            # Persist lines for period t (rollforward balances)
            put(t, Component.CSM_OPEN, csm_open)
            put(t, Component.CSM_INT, csm_int)
            put(t, Component.CSM_REL, csm_rel)
            put(t, Component.CSM_CLOSE, csm_close)

            put(t, Component.RA_OPEN, ra_open)
            put(t, Component.RA_REL, ra_rel)
            put(t, Component.RA_CLOSE, ra_close)

            put(t, Component.BEL_OPEN, bel_open)
            put(t, Component.BEL_CLOSE, bel_close)

            # Persist service detail
            put(t, Component.PREM_CASH, exp_prem, MovementType.SERVICE)
            put(t, Component.CLAIMS, exp_claims, MovementType.SERVICE)
            put(t, Component.EXPENSES, exp_exp, MovementType.SERVICE)
            put(t, Component.ACQ_AMORT, acq_amort, MovementType.SERVICE)
            put(t, Component.REV_SERVICE, revenue, MovementType.SERVICE)
            put(t, Component.EXP_SERVICE, service_exp, MovementType.SERVICE)
            put(t, Component.SRV_RESULT, service_result, MovementType.SERVICE)


            # Persist finance detail
            put(t, Component.FIN_INT_CSM, csm_int, MovementType.FINANCE)
            put(t, Component.FIN_INT_BEL, bel_int, MovementType.FINANCE)
            put(t, Component.FIN_RESULT, fin_result, MovementType.FINANCE)


            # roll state
            csm_open = csm_close
            ra_open = ra_close

        self.stdout.write(self.style.SUCCESS(f"Projection run created: {rs}"))
