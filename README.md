# Kamran (Cameron) Aliyev — Developer Portfolio

A content-managed personal portfolio built with Django 5.2 LTS. The profile, skills,
project case studies, resume content and resume PDF are stored in the database and
edited through the Django admin, so the site can be updated without touching code.
Visitors can send messages through a validated, spam-protected, rate-limited contact
form; messages are stored privately and can optionally be forwarded by email.

> **Screenshots**
>
> | Home | Project case study | Mobile |
> |---|---|---|
> | `docs/screenshots/home.png` *(add)* | `docs/screenshots/project.png` *(add)* | `docs/screenshots/mobile.png` *(add)* |

---

## Technology stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ (developed on 3.13) |
| Framework | Django 5.2 LTS |
| Database | SQLite (local) · PostgreSQL (production, via `DATABASE_URL`) |
| Templates | Django templates, HTML5, hand-written CSS, vanilla JavaScript |
| Images | Pillow (image validation for uploads) |
| Static files | WhiteNoise (compressed, hashed filenames) |
| App server | Gunicorn |
| Config | Environment variables (`python-dotenv` loads `.env` locally) |

No frontend framework is used. JavaScript only adds the mobile menu, active-section
highlighting and the resume print button; every page works without it.

## Architecture

```
portfolio/
├── config/                  Project configuration
│   ├── settings.py          Environment-based settings (dev + production)
│   ├── urls.py              Root URL routing, sitemap, robots.txt, media
│   ├── wsgi.py / asgi.py
├── core/                    Profile, skills, home + resume pages
│   ├── models.py            DeveloperProfile, Skill
│   ├── views.py             home, resume, resume_download, robots_txt
│   ├── validators.py        Upload validation (extension, size, PDF signature)
│   ├── context_processors.py  Makes `profile` available to every template
│   ├── sitemaps.py
│   ├── templatetags/portfolio_tags.py   `paragraphs` filter
│   └── management/commands/seed_portfolio.py
├── projects/                Project case studies
│   ├── models.py            Project, ProjectScreenshot
│   └── views.py             project_list, project_detail
├── contact/                 Contact form
│   ├── models.py            ContactMessage
│   ├── forms.py             ContactForm (ModelForm + honeypot + signed timestamp)
│   └── views.py             contact (validation, rate limit, PRG, email)
├── templates/               base.html, partials/, per-app templates, 404.html, 500.html
├── static/                  css/main.css, css/print.css, js/main.js, images/
├── media/                   Uploaded files (git-ignored)
├── build.sh                 Render build script
├── gunicorn.conf.py
├── render.yaml              Render Blueprint (review before use)
├── Procfile                 For Heroku-style platforms
├── requirements.txt
└── .env.example
```

A deeper explanation (request lifecycle, ORM, forms, security) is in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Data model

```
DeveloperProfile (single row)
Skill ──────────────┐
                    │ many-to-many  (Project.technologies ↔ Skill.projects)
Project ────────────┘
  └── ProjectScreenshot   (foreign key, many screenshots per project, CASCADE)
ContactMessage            (stand-alone, never shown publicly)
```

| Model | Key fields | Integrity rules |
|---|---|---|
| `DeveloperProfile` | name, title, location, intro, about, focus areas, resume text, photo, email, phone, GitHub, LinkedIn, resume PDF, availability | Admin allows only one row; uploads validated |
| `Skill` | name, category (choices), display order, icon, active | Case-insensitive unique name (`UniqueConstraint(Lower("name"))`) |
| `Project` | title, unique slug, descriptions, architecture, database design, features, challenges, setup, cover image, GitHub/demo URLs, technologies, featured, published, order, timestamps | Unique slug; `clean()` forbids featuring an unpublished project; index on `(is_published, display_order)` |
| `ProjectScreenshot` | project FK, image, alt text, caption, order | Deleted with its project |
| `ContactMessage` | name, email, subject, message, read, IP, created | Index on `(is_read, created_at)` |

## Local installation

Requirements: Python 3.12 or newer, Git.

```bash
git clone <your-repo-url> portfolio
```

```bash
cd portfolio
```

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

(Windows: `.venv\Scripts\activate`)

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

The example file sets `DJANGO_DEBUG=true`, which is all local development needs.

### Migrations

```bash
python manage.py migrate
```

After changing a model: `python manage.py makemigrations` then `python manage.py migrate`.

### Initial data

```bash
python manage.py seed_portfolio
```

Creates the profile, skills and the three projects **only if they do not exist**.
Running it again never overwrites content you edited in the admin.

### Create an administrator

```bash
python manage.py createsuperuser
```

No administrator account is created automatically and no credentials are stored in
the repository.

### Run

```bash
python manage.py runserver
```

- Website: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## Personalising content (admin)

| What | Where in admin |
|---|---|
| Photo, email, phone, GitHub, LinkedIn, availability badge | Core → Developer profile |
| Resume PDF (upload / replace), resume summary, education | Core → Developer profile → Resume |
| Skills, ordering, hide/show | Core → Skills (order and active are editable in the list) |
| Project repository / demo URLs, cover image, screenshots | Projects → Projects |
| Publish / unpublish / feature projects | Projects list (checkboxes or bulk actions) |
| Incoming messages, read/unread | Contact → Contact messages |

Links and buttons for GitHub, LinkedIn, email, phone, repositories, demos and the
resume download are only rendered when a value exists, so nothing broken is shown.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `false` | `true` only for local development |
| `DJANGO_SECRET_KEY` | — | **Required** when debug is off; the app refuses to start without it |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins with scheme |
| `SITE_URL` | request host | Base URL for canonical and Open Graph tags |
| `DATABASE_URL` | SQLite file | e.g. `postgres://user:pass@host:5432/db` |
| `MEDIA_ROOT` | `./media` | Where uploads are stored; use a persistent disk in production |
| `SERVE_MEDIA` | `true` | Serve uploads through Django (see Media storage) |
| `CONTACT_RATE_LIMIT` | `5` | Max submissions per IP per window |
| `CONTACT_RATE_WINDOW_SECONDS` | `3600` | Rate-limit window |
| `CONTACT_TRUST_PROXY` | `true` on Render | Use `X-Forwarded-For` for client IP |
| `CONTACT_NOTIFY_EMAIL` | empty | Address that receives new-message notifications |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | — | SMTP settings; without `EMAIL_HOST` emails go to the console and messages are still saved |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` | HTTPS redirect in production |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` | HSTS max-age |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `true` | |
| `DJANGO_SECURE_HSTS_PRELOAD` | `false` | Enable only after reading hstspreload.org |
| `RENDER_EXTERNAL_HOSTNAME` | set by Render | Added to allowed hosts and CSRF origins automatically |

## Running tests

```bash
python manage.py check
```

```bash
python manage.py test
```

The suite (61 tests) covers pages, routing, project visibility and models, the contact
form (validation, persistence, PRG redirect, spam handling, rate limit, CSRF, email
on/off/failure), resume upload validation and download, seed idempotency, sitemap,
robots.txt, the 404/500 pages, and a query-count check for the home page.

## Production deployment (Render)

Nothing is deployed automatically. These steps create billable resources only when you
choose a paid plan; review Render's pricing first.

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repository. `render.yaml`
   defines a PostgreSQL database, a web service running `./build.sh` and
   `gunicorn config.wsgi:application`, and a 1 GB disk mounted at `/var/data`.
   Alternatively create a **Web Service** manually with the same build and start
   commands and add the environment variables from the table above.
3. In the service's environment settings set `SITE_URL`, and once you have a domain,
   `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
4. After the first deploy, open the Render **Shell** and run
   `python manage.py createsuperuser`.
5. Log in to `/admin/`, upload your photo and resume PDF, and add your links.

`build.sh` installs dependencies, runs `collectstatic`, applies migrations and runs
`seed_portfolio` (safe to repeat).

### Media storage

Render's (and most PaaS) filesystems are **ephemeral**: anything written outside a
persistent disk is lost on every deploy or restart. Uploaded files (photo, screenshots,
resume PDF) therefore need one of:

- **Persistent disk (configured):** `MEDIA_ROOT=/var/data/media` on a Render disk.
  Disks require a paid instance and pin the service to one instance. Django serves the
  files (`SERVE_MEDIA=true`), which is fine for a low-traffic portfolio.
- **Object storage (for scaling):** add `django-storages` with S3, Cloudflare R2 or
  similar, set `STORAGES["default"]` to the S3 backend, and set `SERVE_MEDIA=false`.

Static files (CSS, JS, images in `static/`) are built into the deploy by
`collectstatic` and served by WhiteNoise, so they need no extra storage.

### Custom domain

1. In Render: service → **Settings → Custom Domains → Add**, e.g. `yourdomain.com`
   and `www.yourdomain.com`.
2. At your DNS provider, create the records Render shows (a `CNAME` for `www`, and an
   `ALIAS`/`ANAME` or `A` record for the apex domain).
3. Wait for Render to verify the domain and issue the TLS certificate.
4. Update environment variables:
   `DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`,
   `SITE_URL=https://yourdomain.com`.

### Other hosts

Any platform that runs a Python web process works: install `requirements.txt`, run
`collectstatic` and `migrate`, start `gunicorn config.wsgi:application`
(the `Procfile` covers Heroku-style platforms), and provide PostgreSQL through
`DATABASE_URL` plus persistent media storage.

## Known limitations

- The rate limiter uses Django's in-memory cache, which is per process. With several
  Gunicorn workers the effective limit is multiplied by the worker count. A shared
  cache (Redis or the database cache backend) makes it exact.
- `SERVE_MEDIA` uses `django.views.static.serve`, adequate for a portfolio but not for
  high traffic; use object storage or a CDN for that.
- The StockFlow and SpendWise case studies were written from the project descriptions
  on the resume. Review them against the actual repositories before sharing.
