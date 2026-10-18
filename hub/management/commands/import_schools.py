from django.core.management.base import BaseCommand

from hub.importing import school_rows
from hub.models import School


class Command(BaseCommand):
    help = "Import schools from CSV (School Name, City, Province, School Board). Safe to re-run; duplicates are skipped."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")

    def handle(self, csv_path, **opts):
        before, seen, bad = School.objects.count(), set(), 0
        batch = []
        for name, city, prov, board in school_rows(csv_path):
            if not name or not prov:
                bad += 1
                continue
            key = (name[:160], city[:80], prov)
            if key in seen:
                continue
            seen.add(key)
            batch.append(School(name=key[0], city=key[1], province=prov, board=board[:160]))
        School.objects.bulk_create(batch, batch_size=1000, ignore_conflicts=True)
        added = School.objects.count() - before
        self.stdout.write(self.style.SUCCESS(f"Added {added} schools ({len(seen)} unique in file, {bad} rows skipped)."))
