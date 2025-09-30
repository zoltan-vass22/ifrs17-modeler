from __future__ import annotations

from django.conf import settings
from django.core.management import BaseCommand, call_command, CommandError

from contracts.models import ContractGroup
from assumptions.models import DiscountCurve, RiskAdjustmentParams
from results.models import ResultSet, RollforwardLine


class Command(BaseCommand):
    help = "Seed deterministic demo data and create a fresh demo result. Use --hard to flush DB and reload fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hard",
            action="store_true",
            help="DEV ONLY: flush the whole DB, reload fixtures, then run the demo.",
        )

    def handle(self, *args, **options):
        hard = options.get("hard", False)

        if hard:
            # Guard: don’t allow hard reset in non-debug by default
            if not settings.DEBUG:
                raise CommandError("Refusing to run --hard while DEBUG=False. Enable DEBUG or remove the guard if intentional.")
            self.stdout.write(self.style.WARNING("Flushing database (DEV ONLY)…"))
            call_command("flush", verbosity=0, interactive=False)

        # Ensure base data exists (load fixtures only if missing)
        if hard:
            self.stdout.write("Loading base fixtures (contracts, assumptions)…")
            call_command("loaddata", "contracts/fixtures/contracts_minimal.json", verbosity=0)
            call_command("loaddata", "assumptions/fixtures/assumptions_minimal.json", verbosity=0)
        else:
            if not ContractGroup.objects.exists():
                self.stdout.write("No ContractGroup found; loading contracts fixtures…")
                call_command("loaddata", "contracts/fixtures/contracts_minimal.json", verbosity=0)
            if not DiscountCurve.objects.exists() or not RiskAdjustmentParams.objects.exists():
                self.stdout.write("Missing assumptions; loading assumptions fixtures…")
                call_command("loaddata", "assumptions/fixtures/assumptions_minimal.json", verbosity=0)

        # Clear previous results only (idempotent)
        self.stdout.write("Clearing previous results…")
        RollforwardLine.objects.all().delete()
        ResultSet.objects.all().delete()

        # Create a fresh demo run
        self.stdout.write("Running demo…")
        call_command("run_demo")

        self.stdout.write(self.style.SUCCESS("Demo seed complete."))
