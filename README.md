# SeniorHub

Django app: school calendars for multiple schools + a university application tracker for Canadian high school seniors.

## Run it
    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py makemigrations hub
    python manage.py migrate
    python manage.py seed
    python manage.py createsuperuser
    python manage.py runserver

Open http://127.0.0.1:8000/ (app) and /admin/ (staff).

## Updating an existing copy
Extract the new zip over your old folder (keep your venv, db.sqlite3 and hub/migrations), then:

    python manage.py makemigrations hub
    python manage.py migrate
    python manage.py seed
    python manage.py import_deadlines data/deadlines_2027.csv

## Bulk data (CSV files from your own research)
    python manage.py import_schools canada_schools_odef.csv
    python manage.py import_deadlines canada_university_deadlines_fall_2027.csv
Both are safe to re-run. import_deadlines also accepts the simpler format in data/deadlines_2027.csv.

- Deadlines: add rows to data/deadlines_2027.csv (university,kind,title,due,verified,source_url,notes) and re-run import_deadlines. Re-running updates existing rows.
- Schools: build a CSV like data/schools_template.csv (name,city,province,board) from each province's open school list, then run `python manage.py import_schools yourfile.csv`.
- Teachers: new teacher accounts are inactive until approved in Admin -> Profiles (action: "Approve selected teachers").

## Where to change things
- Deadlines (early/regular/supplementary/OUAC payment/etc.): Admin -> Deadlines. Leave "university" blank for ones everyone sees (OUAC). Tick "verified" once checked against the official site.
- School calendar: Admin -> Events (pick the school). Add each school in Admin -> Schools.
- Default checklist for every student: Admin -> Checklist templates (new items appear for existing users automatically).
- Universities: Admin -> Universities.
- Layout/colours: hub/static/hub/style.css (CSS grid/flex, responsive). Pages: hub/templates/.

## Before real use
Set SECRET_KEY, DEBUG=0 and ALLOWED_HOSTS environment variables, and run `collectstatic` behind a real web server.
