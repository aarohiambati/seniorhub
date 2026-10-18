import csv
from datetime import date

from django.core.management.base import BaseCommand

from hub.importing import university_rows
from hub.models import Deadline, University


class Command(BaseCommand):
    help = ("Import deadlines. Accepts either the wide university CSV (columns like 'Province/Territory', 'University', "
            "'Regular Application Deadline', ...) or the simple format university,kind,title,due,verified,source_url,notes.")

    def add_arguments(self, parser):
        parser.add_argument("csv_path")

    def handle(self, csv_path, **opts):
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            header = next(csv.reader(f), [])
        if "Province/Territory" in header:
            self.import_wide(csv_path)
        else:
            self.import_simple(csv_path)

    def import_wide(self, path):
        unis = dls = 0
        for r in university_rows(path):
            uni, _ = University.objects.get_or_create(
                name=r["name"], defaults={"province": r["province"] or "", "uses_ouac": r["province"] == "ON"})
            uni.province = r["province"] or uni.province
            uni.city, uni.website = r["city"][:80], r["url"][:300]
            uni.deadline_status, uni.deadline_notes = r["status"][:120], r["notes"][:300]
            uni.save()
            unis += 1
            for d in r["deadlines"]:
                Deadline.objects.update_or_create(
                    university=uni, title=d["title"][:160],
                    defaults={"kind": d["kind"], "due": d["due"], "verified": r["verified"],
                              "source_url": r["url"][:200], "notes": r["notes"][:240]})
                dls += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {unis} universities and {dls} dated deadlines."))

    def import_simple(self, path):
        n = 0
        with open(path, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                uni = University.objects.get_or_create(name=r["university"].strip())[0] if r["university"].strip() else None
                Deadline.objects.update_or_create(
                    university=uni, title=r["title"].strip(),
                    defaults={"kind": r["kind"].strip(), "due": date.fromisoformat(r["due"].strip()),
                              "verified": r["verified"].strip() in ("1", "true", "True", "yes"),
                              "source_url": r.get("source_url", "").strip(), "notes": r.get("notes", "").strip()})
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {n} deadlines."))
