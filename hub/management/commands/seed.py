from datetime import date

from django.core.management.base import BaseCommand

from hub.models import ChecklistTemplate as C, Deadline, Event, School, University


CHECKLIST = [
    ("prepare", "Research programs and build a shortlist", "Check prerequisites, required grades and average cut-offs."),
    ("prepare", "Confirm deadlines for each university", "Early vs regular, supplementary and scholarship dates differ per school."),
    ("prepare", "Create your OUAC account", "Ontario high school students apply through OUAC using the 101 application. Keep your login safe."),
    ("prepare", "Meet your guidance counsellor", "Confirm courses, transcript sending, and any school-side deadlines."),
    ("prepare", "Line up references / write personal statements", "Only if a program asks for them."),
    ("submit", "Complete supplementary applications", "Essays, portfolios, video interviews or admission info forms where required."),
    ("submit", "Submit your OUAC application", "Add all program choices before the deadline."),
    ("submit", "Pay the OUAC fee", "Your application is not complete until payment goes through."),
    ("submit", "Submit direct applications and pay their fees", "For universities that do not use OUAC."),
    ("submit", "Apply for scholarships and bursaries", "Many have earlier deadlines than admission."),
    ("after", "Check email and university portals for missing documents", "Do this weekly."),
    ("after", "Apply for OSAP / student financial aid", "Check provincial and federal aid timelines."),
    ("after", "Apply for residence", "Often has its own deadline and deposit."),
    ("after", "Send updated grades when asked", "Confirm with your counsellor."),
    ("after", "Respond to offers and pay deposits on time", "Offer response dates are firm."),
]
SAMPLE_UNIS = [
    ("University of Toronto", "ON", True), ("Wilfrid Laurier University", "ON", True), ("University of Waterloo", "ON", True),
    ("Queen's University", "ON", True), ("McMaster University", "ON", True),
    ("Western University", "ON", True), ("University of Ottawa", "ON", True),
    ("York University", "ON", True), ("Toronto Metropolitan University", "ON", True),
    ("University of British Columbia", "BC", False), ("McGill University", "QC", False),
]


class Command(BaseCommand):
    help = "Load sample school, universities and default checklist. Then run import_deadlines."

    def handle(self, *args, **opts):
        school, _ = School.objects.get_or_create(name="Sample Secondary School", defaults={"city": "Ajax"})
        for i, (phase, title, hint) in enumerate(CHECKLIST):
            C.objects.update_or_create(title=title, defaults={"phase": phase, "help_text": hint, "order": i})
        for name, prov, ouac in SAMPLE_UNIS:
            University.objects.get_or_create(name=name, defaults={"province": prov, "uses_ouac": ouac})
        Deadline.objects.filter(title__startswith="OUAC 105 application deadline (placeholder").delete()
        Event.objects.get_or_create(school=school, title="University info night",
                                    defaults={"category": "guidance", "start": date(2026, 11, 5)})
        self.stdout.write(self.style.SUCCESS("Seeded. Now edit real dates in /admin/."))
