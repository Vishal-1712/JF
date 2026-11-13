# Job Application Tracker

A Django and SQLite application for tracking job applications, interview schedules, and job-search progress. Each account has a private dashboard and can only view or change its own applications and interviews.

## Requirements

- Python 3.12 or newer
- pip

Bootstrap 5 and Chart.js are loaded from jsDelivr, so an internet connection is needed for their styles, icons, and dashboard charts.

## Run locally on Windows

Open the project folder in VS Code, then open a PowerShell terminal in that folder.

1. Create and activate a virtual environment:

   ```powershell
   py -3.12 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use the venv interpreter directly in the commands below, or adjust the execution policy for your user account.

2. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Create the SQLite database and apply migrations:

   ```powershell
   python manage.py migrate
   ```

4. Start the development server:

   ```powershell
   python manage.py runserver
   ```

5. Open <http://127.0.0.1:8000/> and register an account.

Optional: create an administrator account for `/admin/`:

```powershell
python manage.py createsuperuser
```

## Tests and checks

Run the application test suite and Django system checks:

```powershell
python manage.py test
python manage.py check
```

## Project layout

```text
config/                 Django project settings and root URLs
templates/              Project-level error pages
tracker/
  migrations/           Database schema migrations
  static/tracker/       CSS, JavaScript, and favicon
  templates/tracker/    Authentication and application pages
  forms.py              Registration, profile, application, and interview forms
  models.py             JobApplication and Interview models
  urls.py               Tracker routes
  views.py              Authentication, CRUD, filters, and dashboard analytics
manage.py
requirements.txt
```

## Configuration

The default settings are intended for local development (`DEBUG=True`, SQLite, and localhost hosts). Set `DJANGO_SECRET_KEY` to a unique, private value before using the app outside local development. Do not deploy with `DEBUG=True` or the development fallback secret.
