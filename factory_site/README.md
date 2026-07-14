# Meihua Musical Instruments Website

Public OEM/ODM factory website with inquiry collection and a lightweight lead follow-up backend.

## Run Locally

From the project root:

```bash
.venv/bin/python factory_site/app.py
```

Open:

```text
http://127.0.0.1:5080
```

If port 5080 is occupied:

```bash
FACTORY_SITE_PORT=5081 .venv/bin/python factory_site/app.py
```

For LAN preview from a phone or another computer:

```bash
FACTORY_SITE_HOST=0.0.0.0 FACTORY_SITE_PORT=5080 .venv/bin/python factory_site/app.py
```

Admin lead follow-up backend:

```text
http://127.0.0.1:5080/admin?password=your-admin-password
```

Submitted inquiries are saved to:

- `factory_site/data/inquiries.jsonl`
- `factory_site/data/inquiries.csv`

The backend supports:

- Lead status: New, Contacted, Quoted, Sample Sent, Order Won, No Fit
- Follow-up notes and next follow-up date
- Email and WhatsApp quick links
- Excel and CSV export

## Replace Before Launch

- Company name
- Logo
- Factory address
- Sales email
- WhatsApp / phone / WeChat
- Real factory photos
- Real product photos
- MOQ, sample lead time and production lead time
- Certificates and export markets

## Production Notes

Set a stronger admin password before deployment. The app supports either a plain environment variable:

```bash
export FACTORY_ADMIN_PASSWORD="your-strong-password"
```

Or a hashed password:

```bash
export FACTORY_ADMIN_PASSWORD_HASH="pbkdf2:sha256:..."
```

For live email alerts, the site is preconfigured for Gmail alerts to `besttone188@gmail.com`.
Create a Gmail app password, then add it to Render as `FACTORY_SMTP_PASSWORD`.

Optional SMTP email alert environment variables:

```bash
export FACTORY_ALERT_EMAIL="besttone188@gmail.com"
export FACTORY_SMTP_HOST="smtp.gmail.com"
export FACTORY_SMTP_PORT="587"
export FACTORY_SMTP_USER="besttone188@gmail.com"
export FACTORY_SMTP_PASSWORD="gmail-app-password"
```

## Simple Online Deployment

Recommended low-cost first step: GitHub + Render free web service.

1. Create a new private GitHub repository and upload this project.
2. Open Render and create a new Web Service from that GitHub repository.
3. Use these settings:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn factory_site.app:app --bind 0.0.0.0:$PORT`
   - Plan: Free
4. Add environment variables in Render:
   - `FACTORY_ADMIN_PASSWORD`: choose a strong admin password
   - `FACTORY_SITE_SECRET`: choose any long random text
5. After Render deploys successfully, open the Render URL first and test:
   - Home page
   - Inquiry form
   - Admin page: `/admin?password=your-password`
6. Add your custom domain in Render, then go to the domain provider and add the DNS record Render gives you.

For the first stage, this setup is enough for customers to view the website. Render free service may sleep after inactivity, so the first visit can load slowly. The simple inquiry backend stores data inside the web service filesystem, which is fine for early testing but should be upgraded later to a database or persistent storage before serious promotion.
