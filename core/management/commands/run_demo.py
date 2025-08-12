from __future__ import annotations

from decimal import Decimal, getcontext
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from contracts.models import ContractGroup
from assumptions.models import DiscountCurve, CurveType, RiskAdjustmentParams, RAMethod
from results.models import ResultSet, RollforwardLine, Component

# numeric precision for Decimal outputs
getcontext().prec = 28


def _dfs(rates: list[float], start_index: int = 0) -> list[Decimal]:
    """
    Build end-of-period discount factors from a list of per-period spot rates.
    DF[t] = 1 / Π_{i=start..start+t} (1 + r[i])
    """
    dfs: list[Decimal] = []
    acc = Decimal("1.0")
    for r in rates[start_index:]:
        acc *= (Decimal("1.0") + Decimal(str(r)))
        dfs.append(Decimal("1.0") / acc)
    return dfs


def _pv(
    cashflows: list[Decimal],
    dfs: list[Decimal],
    include_t0: bool = False,
    t0_cash: Decimal = Decimal("0.0"),
) -> Decimal:
    """
    Present value of cashflows at end-of-period points using provided DFs.
    Optionally include a time-0 cash flow (undiscounted).
    """
    total = Decimal("0.0")
    if include_t0 and t0_cash:
        total += t0_cash
    for t, cf in enumerate(cashflows):
        total += cf * dfs[t]
    return total


class Command(BaseCommand):
    help = "Run a tiny end-to-end demo: initial recognition + first roll-forward, and save results."

    def handle(self, *args, **options):
        # --- 1) Load inputs ---------------------------------------------------
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
            raise CommandError("Missing DiscountCurve(s). Load assumptions fixtures first.")

        ra_params = RiskAdjustmentParams.objects.first()
        if not ra_params:
            raise CommandError("Missing RiskAdjustmentParams. Load assumptions fixtures first.")
        if ra_params.method != RAMethod.TOY_FACTOR:
            raise CommandError("This demo expects RAMethod=TOY_FACTOR in Phase 1.")

        # --- 2) Guardrails on projection length ------------------------------
        coverage_n = group.coverage_term_years
        li_len = len(li_curve.rates or [])
        curr_len = len(curr_curve.rates or [])

        if li_len < coverage_n or curr_len < coverage_n:
            raise CommandError(
                f"Discount curve length too short for coverage term: "
                f"coverage_term_years={coverage_n}, locked_in_len={li_len}, current_len={curr_len}. "
                f"Extend your fixtures (add more rates) or shorten the term."
            )

        n = coverage_n  # require full term availability for the demo

        # --- 3) Build toy projections (Phase 1 simplifications) ---------------
        # Premiums: spread written_premium level over premium_term_years (end of period)
        prem_per = Decimal(group.written_premium) / Decimal(group.premium_term_years or 1)
        premiums = [prem_per if t < group.premium_term_years else Decimal("0.0") for t in range(n)]

        # Claims & expenses: simple proportions of premium
        claims = [prem_per * Decimal("0.60") for _ in range(n)]
        expenses = [prem_per * Decimal("0.05") for _ in range(n)]

        # Acquisition cash flow: 10% of written premium at time 0 (outflow)
        acq_t0 = Decimal(group.written_premium) * Decimal("0.10")

        # RA per period (toy): factor × expected claims
        ra_factor = Decimal(ra_params.factor)
        ra_vec = [Decimal(c) * ra_factor for c in claims]

        # DFs
        dfs_curr_0 = _dfs(curr_curve.rates, 0)
        dfs_curr_1 = _dfs(curr_curve.rates, 1) if n > 1 else []
        dfs_li = _dfs(li_curve.rates, 0)

        # --- 4) Initial recognition (t = 0) ----------------------------------
        pv_in = _pv([Decimal(x) for x in premiums], dfs_curr_0)
        pv_out = _pv(
            [Decimal(c) + Decimal(e) for c, e in zip(claims, expenses)],
            dfs_curr_0,
            include_t0=True,
            t0_cash=acq_t0,
        )
        pv_ra = _pv([Decimal(x) for x in ra_vec], dfs_curr_0)
        fcf0 = pv_out - pv_in + pv_ra

        csm0 = Decimal("0.0")
        loss_comp0 = Decimal("0.0")
        if fcf0 <= 0:
            csm0 = -fcf0  # profitable → CSM
        else:
            loss_comp0 = fcf0  # onerous (not used further in Phase 1)

        # --- 5) ResultSet header ---------------------------------------------
        meas_date = timezone.now().date()
        rs, _created = ResultSet.objects.update_or_create(
            group=group,
            scenario_name="BASE",
            measurement_date=meas_date,
            defaults={
                "code": f"DEMO_{group.code}_{meas_date.isoformat()}",
                "name": f"Demo run for {group.name}",
                "currency": group.currency,
                "notes": "Phase 1 demo: toy PVs; 60% claims, 5% expenses, 10% t0 acquisition; RA = factor × claims.",
            },
        )

        rs.lines.all().delete()
        # Helper to add a line
        def add_line(period: int, component: str, amount: Decimal):
            RollforwardLine.objects.update_or_create(
                result=rs,
                period_index=period,
                component=component,
                defaults={"amount": amount.quantize(Decimal("0.000001"))},
            )

        # t=0 lines
        add_line(0, Component.INIT_PV_IN, pv_in)
        add_line(0, Component.INIT_PV_OUT, pv_out)
        add_line(0, Component.INIT_RA, pv_ra)
        add_line(0, Component.INIT_FCF, fcf0)
        add_line(0, Component.INIT_CSM, csm0)
        add_line(0, Component.INIT_LOSS_COMP, loss_comp0)

        # --- 6) First subsequent period (t = 1) ------------------------------
        # Coverage-units proxy: equal units → release 1/n of CSM after interest
        csm_open = csm0
        li_rate_0 = Decimal(str(li_curve.rates[0]))
        csm_int = csm_open * li_rate_0
        csm_after_int = csm_open + csm_int
        csm_rel = csm_after_int * (Decimal("1.0") / Decimal(n))
        csm_close = csm_after_int - csm_rel

        # RA release proportional to claims run-off (equal share here)
        ra_open = pv_ra
        ra_rel = ra_open * (Decimal("1.0") / Decimal(n))
        ra_close = ra_open - ra_rel

        # Expected service amounts in period 1
        exp_claims_1 = Decimal(claims[0])
        exp_exp_1 = Decimal(expenses[0])
        acq_amort_1 = acq_t0 * (Decimal("1.0") / Decimal(n))  # spread t0 acquisition over coverage units

        # Insurance revenue/expenses (toy mapping)
        revenue_1 = csm_rel + ra_rel + exp_claims_1 + exp_exp_1 + acq_amort_1
        service_exp_1 = exp_claims_1 + exp_exp_1 + acq_amort_1
        service_result_1 = revenue_1 - service_exp_1  # equals CSM_rel + RA_rel

        # BEL opening (remaining PV excl. CSM) at start of year 1 (i.e., periods 1..N)
        pv_in_rem_0 = _pv([Decimal(x) for x in premiums[1:]], dfs_curr_1)
        pv_out_rem_0 = _pv(
            [Decimal(c) + Decimal(e) for c, e in zip(claims[1:], expenses[1:])],
            dfs_curr_1,
        )
        pv_ra_rem_0 = _pv([Decimal(x) for x in ra_vec[1:]], dfs_curr_1)
        bel_open_1 = pv_out_rem_0 - pv_in_rem_0 + pv_ra_rem_0

        # Finance result: approximate = unwind on BEL_open (current r0) + CSM interest
        curr_rate_0 = Decimal(str(curr_curve.rates[0]))
        finance_result_1 = bel_open_1 * curr_rate_0 + csm_int

        # For completeness, BEL close after one period (using periods 2..N)
        dfs_curr_2 = _dfs(curr_curve.rates, 2) if n > 2 else []
        if n > 2:
            pv_in_rem_1 = _pv([Decimal(x) for x in premiums[2:]], dfs_curr_2)
            pv_out_rem_1 = _pv(
                [Decimal(c) + Decimal(e) for c, e in zip(claims[2:], expenses[2:])],
                dfs_curr_2,
            )
            pv_ra_rem_1 = _pv([Decimal(x) for x in ra_vec[2:]], dfs_curr_2)
            bel_close_1 = pv_out_rem_1 - pv_in_rem_1 + pv_ra_rem_1
        else:
            bel_close_1 = Decimal("0.0")

        # Persist t=1 lines
        add_line(1, Component.CSM_OPEN, csm_open)
        add_line(1, Component.CSM_INT, csm_int)
        add_line(1, Component.CSM_REL, csm_rel)
        add_line(1, Component.CSM_CLOSE, csm_close)

        add_line(1, Component.RA_OPEN, ra_open)
        add_line(1, Component.RA_REL, ra_rel)
        add_line(1, Component.RA_CLOSE, ra_close)

        add_line(1, Component.BEL_OPEN, bel_open_1)
        add_line(1, Component.BEL_CLOSE, bel_close_1)

        add_line(1, Component.REV_SERVICE, revenue_1)
        add_line(1, Component.EXP_SERVICE, service_exp_1)
        add_line(1, Component.SRV_RESULT, service_result_1)

        add_line(1, Component.FIN_RESULT, finance_result_1)

        self.stdout.write(self.style.SUCCESS(f"Demo run created: {rs}"))
