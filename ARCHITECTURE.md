# Architecture

This document explains how the portfolio works, from an HTTP request to the HTML that
comes back. Each section ends with the points worth being able to explain in an
interview.

---

## 1. Django request/response lifecycle

```
Browser ──HTTP──▶ Gunicorn ──WSGI──▶ Django
                                      │
                    1. Middleware (request phase, top → bottom)
                       SecurityMiddleware → WhiteNoise → Sessions → Common
                       → CSRF → Authentication → Messages → Clickjacking
                    2. URL resolver  (config/urls.py → app urls.py)
                    3. View function (e.g. projects.views.project_detail)
                         ├─ ORM queries → database
                         └─ render(template, context)
                              └─ context processors add `profile`, `site_url`
                    4. Middleware (response phase, bottom → top)
                                      │
Browser ◀──HTTP── Gunicorn ◀──────────┘
```

1. **Gunicorn** accepts the connection and calls Django's WSGI application
   (`config/wsgi.py`). It runs several worker processes so one slow request does not
   block others.
2. **Middleware** wraps every request. Order matters: `SecurityMiddleware` adds HTTPS
   redirects and security headers first; `WhiteNoiseMiddleware` answers `/static/…`
   requests immediately, before any database work; `CsrfViewMiddleware` rejects POSTs
   without a valid token; `AuthenticationMiddleware` attaches `request.user`.
3. The **URL resolver** matches the path to a view.
4. The **view** builds a response, usually by querying models and rendering a template.
5. Middleware runs again in reverse order on the response (for example adding
   `X-Frame-Options: DENY`).

**Interview points:** middleware is an onion around the view; static files never reach
a view in production; what happens if the CSRF token is missing (403 before the view
runs).

## 2. URL routing

`config/urls.py` is the root URLconf. Each app owns its own `urls.py` and is mounted
with `include()` under a prefix, and each app sets `app_name` to create a namespace:

| Path | View | Name |
|---|---|---|
| `/` | `core.views.home` | `core:home` |
| `/resume/` | `core.views.resume` | `core:resume` |
| `/resume/download/` | `core.views.resume_download` | `core:resume_download` |
| `/projects/` | `projects.views.project_list` | `projects:list` |
| `/projects/<slug>/` | `projects.views.project_detail` | `projects:detail` |
| `/contact/` | `contact.views.contact` (GET + POST) | `contact:contact` |
| `/sitemap.xml`, `/robots.txt` | sitemap framework, `core.views.robots_txt` | |
| `/admin/` | Django admin | |

Templates and code never hard-code paths: they use `{% url 'projects:detail' slug=… %}`
or `reverse()`, and `Project.get_absolute_url()`. Changing a URL means changing one line.
`<slug:slug>` is a path converter that only matches letters, numbers, hyphens and
underscores.

**Interview points:** why namespaces (two apps can both have a view named `list`); why
`reverse()` instead of string paths; how a slug makes URLs readable and stable.

## 3. Views

The project uses **function-based views** because each one is short and the logic is
easier to read top to bottom. Every view is restricted to the HTTP methods it supports
(`@require_GET`, `@require_http_methods(["GET", "POST"])`), so other methods get a 405.

- `home` loads published projects with their technologies, groups active skills by
  category, and renders an unbound contact form.
- `project_detail` uses `get_object_or_404(Project.objects.published()…, slug=slug)`.
  Filtering on `published()` **inside** the lookup is what makes unpublished projects
  return 404 instead of leaking.
- `resume_download` returns a `FileResponse` with `as_attachment=True`, which streams
  the file instead of loading it into memory, and returns 404 when no PDF is uploaded.
- `contact` handles GET (empty form) and POST (validation, persistence, redirect).

**Interview points:** function-based vs class-based views (CBVs like `DetailView` would
also fit; FBVs were chosen for explicitness); what `get_object_or_404` does.

## 4. Models and the ORM

### Relationships

- **Many-to-many — `Project.technologies` ↔ `Skill`.** A project uses many skills and a
  skill appears in many projects. Django creates a join table
  (`projects_project_technologies`) with two foreign keys. The reverse accessor is
  `skill.projects` because of `related_name="projects"`.
- **One-to-many — `ProjectScreenshot.project` → `Project`.** A foreign key with
  `on_delete=CASCADE`: deleting a project deletes its screenshots. Accessed as
  `project.screenshots.all()`.

### Constraints and validation layers

| Layer | Example | Enforced when |
|---|---|---|
| Field type | `EmailField`, `URLField`, `PositiveSmallIntegerField` | Forms and `full_clean()` |
| Field validators | Upload extension, size and PDF signature (`core/validators.py`) | Forms / admin |
| Model `clean()` | A featured project must be published | Forms / admin (`full_clean`) |
| Database constraint | `unique=True` on `Project.slug`; `UniqueConstraint(Lower("name"))` on `Skill` | **Every write**, including scripts and raw SQL |

The database constraint is the last line of defence: `Model.save()` does **not** call
`full_clean()`, so only database constraints protect against code that bypasses forms.

### Custom QuerySets

`Project.objects.published()` and `.with_technologies()` live on a custom
`QuerySet` so every view filters the same way. `Skill.objects.in_category_order()`
uses `Case`/`When` to sort by the site's category order in SQL.

### Avoiding N+1 queries

Rendering three project cards that each list technologies would naively run one
query for the projects plus one per project for its skills. `prefetch_related` loads
all related skills in a single second query and joins them in Python. The home page
runs **4 queries regardless of how many projects exist**, and a test
(`test_homepage_query_count_is_bounded`) asserts that.

- `select_related` → SQL `JOIN`, for foreign keys / one-to-one (single object on the
  other side).
- `prefetch_related` → separate query + Python join, for many-to-many and reverse
  foreign keys (many objects on the other side).

**Interview points:** what N+1 is and how to detect it (`assertNumQueries`, Django
Debug Toolbar); why constraints belong in the database; `CASCADE` vs `PROTECT`.

## 5. Templates

`templates/base.html` defines the page skeleton and `{% block %}`s for the title, meta
description, Open Graph tags and content. Pages `{% extends "base.html" %}` and
override blocks. Repeated pieces are `{% include %}` partials (project card, contact
form, icons).

The `core.context_processors.site_context` context processor adds `profile` to every
template, so the navigation and footer can show the name and social links on every
page without each view loading them.

**Autoescaping** is on: `{{ value }}` converts `<` to `&lt;` and so on, so content typed
into the admin cannot inject scripts (a test checks this). The custom `paragraphs`
filter splits text on blank lines and builds `<p>` tags with `format_html_join`, which
escapes each paragraph before marking the result safe. `mark_safe` is never applied to
user input.

## 6. Forms

`ContactForm` is a **ModelForm** for `ContactMessage`: field types, max lengths and the
email format come from the model, so the rules are defined once. On top of that:

- `clean_name`, `clean_subject`, `clean_message` add field rules (minimum lengths, no
  more than three links).
- `clean()` validates cross-field and anti-spam data: the honeypot field and a signed
  timestamp.
- `full_clean()` is extended to add `aria-invalid` and `aria-describedby` to inputs
  with errors, so screen readers announce the error text.

Form validation always runs **on the server**. The HTML `required` attributes are a
convenience; the form is rendered with `novalidate` so that server messages are
displayed consistently.

## 7. Contact form submission lifecycle

```
GET /contact/ (or the home page)
  └─ ContactForm() renders with a CSRF token and a signed timestamp (form_token)

POST /contact/
  1. CsrfViewMiddleware checks the token ─────────────── fail → 403
  2. Rate limit: cache counter for the client IP ───────── over limit → 429 + message
  3. form.is_valid()
       field validation → clean_<field>() → clean()
       ├─ invalid → re-render with errors, status 400, nothing saved
       └─ valid
  4. Spam check (honeypot filled, or submitted < 3 s after render)
       └─ spam → record attempt, save nothing, respond as if successful
  5. form.save(commit=False) → set ip_address → save()   ← message is now persisted
  6. notify_owner(): send_mail only if CONTACT_NOTIFY_EMAIL is set;
     any exception is logged and swallowed — the message is already saved
  7. messages.success(...) and redirect (302) to /contact/?sent=1
GET /contact/?sent=1
  └─ success message rendered from the session once, then cleared
```

**Post/Redirect/Get:** after a successful POST the server redirects, so refreshing the
page repeats a harmless GET instead of resubmitting the form.

**Why spam gets a fake success:** telling a bot it was blocked helps it adapt.

**Signed timestamp:** `django.core.signing` signs the render time with `SECRET_KEY`.
A bot cannot forge a token that looks older, and tokens older than 24 hours are
rejected with a "reload the page" message.

**Privacy:** messages are only visible in the admin, which requires a staff login.
No public view lists them (tested), and the admin marks a message as read when opened.

## 8. Security decisions

| Concern | Implementation |
|---|---|
| Secrets | `SECRET_KEY` comes from `DJANGO_SECRET_KEY`; with debug off the app refuses to start without it. `.env` is git-ignored. |
| Debug | `DJANGO_DEBUG` defaults to **false**; debug must be enabled explicitly. |
| Hosts | `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` come from the environment. |
| CSRF | `CsrfViewMiddleware` + `{% csrf_token %}`; tested with `enforce_csrf_checks`. |
| XSS | Template autoescaping; no `mark_safe` on user data. |
| Clickjacking | `X_FRAME_OPTIONS = "DENY"`. |
| HTTPS | In production: `SECURE_SSL_REDIRECT`, HSTS for one year, `SECURE_PROXY_SSL_HEADER` (Render terminates TLS at its proxy), secure session and CSRF cookies. |
| Uploads | Allowed extensions only, size limits (5 MB images, 10 MB PDF), Pillow verifies images, PDF "magic bytes" (`%PDF-`) checked, files stored under `MEDIA_ROOT` with Django-generated safe names. |
| Spam / abuse | Honeypot, minimum time-to-submit, link limit, per-IP rate limit. |
| Admin | No default credentials; superuser created manually; `robots.txt` disallows `/admin/`. |
| Database | ORM parameterises all queries, preventing SQL injection. |

`python manage.py check --deploy` reports no issues apart from HSTS preload, which is
intentionally off until the domain is ready for the preload list.

## 9. Production configuration

- **Settings from the environment** (twelve-factor style): the same code runs locally and
  in production; only environment variables differ.
- **Database:** `dj-database-url` parses `DATABASE_URL`. Without it, SQLite is used.
  `conn_max_age=600` keeps connections open between requests and
  `conn_health_checks=True` discards broken ones.
- **Static files:** `collectstatic` copies everything into `staticfiles/`. WhiteNoise's
  `CompressedManifestStaticFilesStorage` adds content hashes to filenames
  (`main.4aa776dc42ff.css`) and pre-compresses them, so browsers can cache them forever
  and a new deploy automatically busts the cache.
- **Media files:** user uploads are not part of the code and must survive deploys, so
  they need a persistent disk or object storage (see README).
- **Gunicorn:** `gunicorn.conf.py` binds to `$PORT` and sets worker count from
  `WEB_CONCURRENCY`.
- **Build:** `build.sh` installs dependencies, collects static files, migrates and
  seeds (idempotent).

## 10. Notes on the featured projects

### StockFlow: `transaction.atomic` and `select_for_update`

`transaction.atomic()` groups several writes into one database transaction: either all
of them commit or, if an exception is raised inside the block, all are rolled back.

`select_for_update()` makes the query `SELECT … FOR UPDATE` on databases that support
it (PostgreSQL, MySQL, Oracle). The selected rows stay locked until the transaction
ends, so a second transaction that wants the same product waits instead of reading a
stale quantity. It must be used inside `atomic()`.

SQLite has no row-level locks. Django skips the `FOR UPDATE` clause there, and SQLite
instead allows only one writer for the whole database at a time. That prevents
corrupted writes but behaves differently under load, so concurrency behaviour should
be tested on PostgreSQL.

### SpendWise: FastAPI request lifecycle

Route match → Pydantic parses and validates the body (422 on failure) → `Depends(get_db)`
opens a SQLAlchemy session and yields it → the route queries or writes models and
commits → the response model serialises the result → the dependency's `finally` closes
the session.
