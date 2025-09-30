from __future__ import annotations

from decimal import Decimal
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from results.models import ResultSet, RollforwardLine, Component
from contracts.models import ContractGroup


class DemoRunTests(TestCase):
    fixtures = [
        "contracts/fixtures/contracts_minimal.json",
        "assumptions/fixtures/assumptions_minimal.json",
    ]

    def setUp(self):
        # Make sure fixtures loaded a group
        self.group = ContractGroup.objects.first()
        self.assertIsNotNone(self.group, "Expected a ContractGroup from fixtures")

    def test_run_demo_creates_expected_rows_and_is_idempotent(self):
        # 1st run
        call_command("run_demo")

        today = timezone.now().date()
        rs_qs = ResultSet.objects.filter(
            group=self.group, scenario_name="BASE", measurement_date=today
        )
        self.assertEqual(rs_qs.count(), 1, "Expected one ResultSet after first run")
        rs = rs_qs.first()

        # Has period 0 & 1 lines
        periods = set(
            RollforwardLine.objects.filter(result=rs).values_list("period_index", flat=True)
        )
        self.assertIn(0, periods, "Missing initial recognition (t=0) lines")
        self.assertIn(1, periods, "Missing first subsequent period (t=1) lines")

        # Must have key components
        comps = set(
            RollforwardLine.objects.filter(result=rs, period_index=0).values_list("component", flat=True)
        )
        self.assertIn(Component.INIT_CSM, comps, "Missing INIT_CSM at t=0")
        self.assertIn(Component.INIT_PV_IN, comps, "Missing INIT_PV_IN at t=0")
        self.assertIn(Component.INIT_PV_OUT, comps, "Missing INIT_PV_OUT at t=0")

        comps1 = set(
            RollforwardLine.objects.filter(result=rs, period_index=1).values_list("component", flat=True)
        )
        self.assertIn(Component.CSM_REL, comps1, "Missing CSM_REL at t=1")
        self.assertIn(Component.RA_REL, comps1, "Missing RA_REL at t=1")
        self.assertIn(Component.FIN_RESULT, comps1, "Missing FIN_RESULT at t=1")

        # Profitability sanity (with toy assumptions, expect profitable → CSM >= 0, no loss component)
        init_csm = RollforwardLine.objects.get(result=rs, period_index=0, component=Component.INIT_CSM).amount
        init_loss = RollforwardLine.objects.get(result=rs, period_index=0, component=Component.INIT_LOSS_COMP).amount
        self.assertGreaterEqual(Decimal(init_csm), Decimal("0"))
        self.assertEqual(Decimal(init_loss), Decimal("0"))

        # 2nd run: should update the same ResultSet (idempotent), not create a second
        call_command("run_demo")
        rs_qs_after = ResultSet.objects.filter(
            group=self.group, scenario_name="BASE", measurement_date=today
        )
        self.assertEqual(rs_qs_after.count(), 1, "run_demo should be idempotent for same day")
