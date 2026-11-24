"""
Populate the portfolio with initial content.

Idempotent: records are created only when missing (matched by name / slug),
so content edited in the admin is never overwritten by re-running this command.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import DeveloperProfile, Skill
from projects.models import Project

PROFILE = {
    "full_name": "Kamran Aliyev",
    "preferred_name": "Cameron",
    "title": "Python Backend Developer",
    "location": "New York City, NY",
    "summary": (
        "I build reliable backend applications, RESTful APIs, and database-driven systems "
        "with Django, FastAPI, and Flask."
    ),
    "about_text": (
        "I am a Python Backend Developer based in New York City, focused on building reliable "
        "backend applications, RESTful APIs, and database-driven systems. I work with Django, "
        "FastAPI, Flask, and relational databases. I enjoy solving technical problems, designing "
        "backend architecture, and writing clean, maintainable code.\n\n"
        "Most of my work happens below the interface: modeling data so relationships and "
        "constraints protect it, putting business rules where they can be tested, wrapping "
        "multi-step writes in transactions, and validating every request before it reaches the "
        "database. I care about code that the next developer can read, change, and trust.\n\n"
        "My projects are independent work that I designed and built to learn backend engineering "
        "properly, from schema design to automated tests. My goal is to join an engineering team "
        "where I can contribute to real-world software projects and keep developing my technical "
        "expertise."
    ),
    "focus_areas": "\n".join(
        [
            "Python backend development: Django, FastAPI and Flask applications with clear structure and tested behavior.",
            "REST API development: Predictable endpoints, validated requests and responses, and accurate HTTP status codes.",
            "Database architecture: Relational models, foreign keys and constraints that keep data consistent.",
            "Business logic: Rules placed where they can be tested and applied to every code path.",
            "Clean, maintainable code: Readable names, small functions, and code the next developer can change safely.",
            "Continuous learning and problem-solving: Reading documentation, tracing problems to their cause, and improving each project.",
        ]
    ),
    "resume_summary": (
        "Python Backend Developer with hands-on experience building web applications, RESTful "
        "APIs, and database-driven backend systems using Django, FastAPI, and Flask. Experienced "
        "in database modeling, ORM, CRUD operations, data validation, authentication, and "
        "business logic implementation.\n\n"
        "Passionate about writing clean, maintainable code, solving technical problems, and "
        "developing reliable backend applications. Seeking a Junior Python Backend Developer "
        "position to contribute to real-world software projects and grow within an engineering team."
    ),
    "professional_development": "\n".join(
        [
            "Python programming and object-oriented programming",
            "Django, FastAPI, and Flask development",
            "Relational databases and SQL",
            "REST API architecture",
            "Data structures and algorithms",
            "Git version control and software development practices",
        ]
    ),
    "education": "",
    "languages": "English, Russian, Turkish",
    "is_available": True,
    "availability_text": "Open to junior backend roles",
}

SKILLS = {
    Skill.Category.PROGRAMMING: ["Python", "SQL"],
    Skill.Category.FRAMEWORKS: ["Django", "FastAPI", "Flask"],
    Skill.Category.DATABASES: ["SQLite", "Django ORM", "SQLAlchemy"],
    Skill.Category.API: ["REST APIs", "HTTP", "JSON", "Pydantic", "Swagger/OpenAPI"],
    Skill.Category.TOOLS: ["Git", "GitHub", "VS Code"],
    Skill.Category.FRONTEND: ["HTML", "CSS"],
    Skill.Category.CONCEPTS: [
        "Object-oriented programming",
        "CRUD operations",
        "Authentication",
        "Authorization",
        "Database relationships",
        "Transactions",
        "Data validation",
        "Exception handling",
    ],
}

# Used to tag the portfolio project but not listed in the Skills section,
# because it is not on the resume. Activate it in the admin if you want it shown.
HIDDEN_SKILLS = {Skill.Category.FRONTEND: ["JavaScript"]}

PROJECTS = [
    {
        "slug": "stockflow",
        "title": "StockFlow — Inventory & Order Management System",
        "display_order": 1,
        "technologies": ["Python", "Django", "Django ORM", "SQLite"],
        "short_description": (
            "A database-driven inventory and order management application for products, "
            "categories, stock movements, and customer orders."
        ),
        "full_description": (
            "StockFlow is a database-driven inventory and order management application designed "
            "to manage products, categories, stock movements, and customer orders. It is built "
            "with Django and the Django ORM, with SQLite as the development database.\n\n"
            "The focus of the project is correctness of stock data: every change to a product's "
            "quantity is recorded as a stock movement, validated against business rules, and "
            "written inside a database transaction."
        ),
        "problem_statement": (
            "Small businesses that track inventory in spreadsheets lose accuracy quickly: stock "
            "counts drift from reality, orders are accepted for items that are not on the shelf, "
            "and there is no history of why a number changed.\n\n"
            "StockFlow models inventory as a relational system so stock levels, orders, and the "
            "movements that connect them stay consistent with each other."
        ),
        "architecture": (
            "StockFlow is a server-rendered Django application. URL patterns route requests to "
            "views, business rules are applied before data is saved, and Django templates render "
            "the result. The Django admin is "
            "configured as the back-office interface for managing records.\n\n"
            "Inventory adjustments run inside transaction.atomic(), so a stock movement and the "
            "matching quantity change are committed together or not at all. If any step raises an "
            "exception, for example because an order would take stock below zero, the whole "
            "transaction is rolled back and the database is left unchanged.\n\n"
            "Inside that transaction the product row is read with select_for_update(). On "
            "PostgreSQL this issues SELECT ... FOR UPDATE, which locks the row until the "
            "transaction ends so two concurrent orders cannot both read the same quantity and "
            "oversell. SQLite does not support row-level locking: Django omits the FOR UPDATE "
            "clause on SQLite, and SQLite instead serializes writers with a database-wide write "
            "lock. The code is written for the PostgreSQL behavior, and the guarantee under real "
            "concurrency should be verified on PostgreSQL rather than SQLite."
        ),
        "database_design": (
            "The schema is built around five related models: Category, Product, Order, OrderItem, "
            "and StockMovement.\n\n"
            "Product has a foreign key to Category. Order has many OrderItems, and each OrderItem "
            "references both its Order and a Product, so an order line always points to a real "
            "product. StockMovement references a Product and records each change to its stock, "
            "which gives every quantity an audit trail.\n\n"
            "Database constraints and ORM relationships enforce integrity at the database level, "
            "not only in forms, so invalid data is rejected no matter which code path writes it."
        ),
        "key_features": "\n".join(
            [
                "Product and category management",
                "Product search and filtering",
                "Stock movement tracking",
                "Transactional inventory adjustments with transaction.atomic()",
                "Stock quantity validation before changes are saved",
                "Order and order item management",
                "Order status management with business rules",
                "Relational database models with foreign keys",
                "Database constraints for data integrity",
                "Configured Django administration",
                "Automated tests",
            ]
        ),
        "challenges": (
            "Keeping stock consistent. A quantity change and its stock movement record must never "
            "get out of sync. Wrapping both writes in one atomic transaction means a failure "
            "halfway through leaves no partial update behind.\n\n"
            "Preventing overselling. Validation has to happen against the current quantity inside "
            "the transaction, not against a value read earlier. Locking the product row with "
            "select_for_update() addresses this on PostgreSQL; on SQLite the database-level write "
            "lock serializes writers instead, which is one reason PostgreSQL is the target for "
            "production.\n\n"
            "Enforcing rules in more than one place. Validation in forms gives users clear errors, "
            "while database constraints are the last line of defense for any code path that "
            "writes data, including the admin and tests."
        ),
        "resume_highlights": "\n".join(
            [
                "Developed a database-driven inventory and order management application.",
                "Designed relational database models for products, categories, orders, order items, and stock movements.",
                "Implemented transactional inventory adjustments and stock validation.",
                "Created product search, filtering, and management functionality.",
                "Implemented order status management and business rules.",
                "Used database constraints and ORM relationships to maintain data integrity.",
                "Configured Django administration and implemented automated tests.",
            ]
        ),
    },
    {
        "slug": "spendwise",
        "title": "SpendWise — Personal Finance REST API",
        "display_order": 2,
        "technologies": ["Python", "FastAPI", "SQLAlchemy", "Pydantic", "SQLite"],
        "short_description": (
            "A RESTful backend for managing personal financial transactions and expense "
            "categories, with validated requests and interactive API docs."
        ),
        "full_description": (
            "SpendWise is a RESTful backend application designed to manage personal financial "
            "transactions and expense categories. It is built with FastAPI, uses SQLAlchemy for "
            "database access and Pydantic for validation, and stores data in SQLite.\n\n"
            "The API exposes CRUD endpoints for transactions and category management, and "
            "documents itself through the Swagger/OpenAPI interface that FastAPI generates."
        ),
        "problem_statement": (
            "Tracking spending needs a reliable backend before it needs a polished interface: data "
            "must be validated on the way in, related correctly (a transaction belongs to a "
            "category), and available through a predictable API that any client can use.\n\n"
            "SpendWise provides that backend as a documented REST API."
        ),
        "architecture": (
            "A request moves through SpendWise in a fixed sequence. FastAPI matches the HTTP "
            "method and path to a route function. Before the function runs, Pydantic parses the "
            "JSON body into a typed schema and rejects invalid input with a 422 response that "
            "lists each error.\n\n"
            "The route declares its database session as a dependency. FastAPI's dependency "
            "injection calls a get_db generator that opens a SQLAlchemy session, yields it to the "
            "route, and closes it in a finally block after the response is produced, so every "
            "request gets its own session and no connection is leaked.\n\n"
            "The route uses the session to query or write SQLAlchemy models and commits changes. "
            "The returned object is serialized through a Pydantic response model, which controls "
            "exactly which fields leave the API. FastAPI builds the OpenAPI schema from these "
            "type declarations, which powers the Swagger UI at /docs."
        ),
        "database_design": (
            "The relational model contains users, transactions, categories, and budgets.\n\n"
            "Transactions reference a category through a foreign key, which lets the API group "
            "and filter spending by category. A Budget model is part of the schema. "
            "SQLAlchemy relationships map these foreign keys to Python attributes, and the "
            "database itself stores the links."
        ),
        "key_features": "\n".join(
            [
                "Transaction CRUD endpoints",
                "Category management",
                "Relational database models",
                "Pydantic request and response validation",
                "SQLAlchemy database sessions",
                "Dependency injection for database sessions",
                "Budget database model",
                "Swagger/OpenAPI documentation",
            ]
        ),
        "challenges": (
            "Separating schemas from models. SQLAlchemy models describe tables while Pydantic "
            "schemas describe API input and output. Keeping them separate means the API contract "
            "can change without changing the table, and internal columns are never exposed by "
            "accident.\n\n"
            "Session lifecycle. Opening one session per request through a dependency, and always "
            "closing it, avoids shared state between requests and connection leaks."
        ),
        "resume_highlights": "\n".join(
            [
                "Developed REST API endpoints for managing financial transactions and categories.",
                "Implemented CRUD operations and request/response validation using Pydantic.",
                "Designed relational database models for users, transactions, categories, and budgets.",
                "Used SQLAlchemy for database operations and session management.",
                "Implemented dependency injection for database sessions.",
                "Utilized Swagger/OpenAPI documentation for API exploration and testing.",
            ]
        ),
    },
    {
        "slug": "developer-portfolio",
        "title": "Developer Portfolio — Full-Stack Django Application",
        "display_order": 3,
        "technologies": ["Python", "Django", "HTML", "CSS", "JavaScript"],
        "short_description": (
            "This website: a Django application with admin-managed projects, skills and resume, "
            "and a validated, rate-limited contact form."
        ),
        "full_description": (
            "This portfolio is a full-stack Django application. Every piece of content, from the "
            "profile and skills to project case studies and the resume PDF, is stored in the "
            "database and edited through the Django admin, so updating the site never requires "
            "changing code.\n\n"
            "The frontend is server-rendered Django templates with hand-written CSS and a small "
            "amount of vanilla JavaScript for the mobile menu and active-section navigation."
        ),
        "problem_statement": (
            "A static portfolio goes stale because every change needs a code edit and a redeploy. "
            "This project treats the portfolio as a small content-managed application, and uses "
            "it to demonstrate backend practices: relational models, validated forms, security "
            "settings, automated tests, and production configuration."
        ),
        "architecture": (
            "The project is split into three Django apps. core holds the developer profile, "
            "skills, home and resume pages, sitemap and robots.txt. projects holds the Project and "
            "ProjectScreenshot models and their list and detail pages. contact holds the "
            "ContactMessage model, the ModelForm, and the submission view.\n\n"
            "Configuration comes from environment variables: SQLite locally, PostgreSQL in "
            "production through DATABASE_URL, static files served by WhiteNoise, and the "
            "application run by Gunicorn. Production mode enables HTTPS redirects, HSTS, and "
            "secure cookies."
        ),
        "database_design": (
            "Project has a many-to-many relationship with Skill through its technologies field, "
            "so one skill can tag many projects and one project can use many skills. "
            "ProjectScreenshot has a foreign key to Project, giving each project an ordered "
            "gallery. Skill names are unique regardless of letter case through a database "
            "constraint, and project slugs are unique.\n\n"
            "Views load technologies with prefetch_related, so a page of projects costs a fixed "
            "number of queries instead of one extra query per project."
        ),
        "key_features": "\n".join(
            [
                "Database-driven profile, skills, projects, and resume content",
                "Django admin with search, filters, inline screenshots, and publish/unpublish actions",
                "Project case-study pages with unpublished projects hidden from visitors",
                "Contact form built on a ModelForm with server-side validation and CSRF protection",
                "Post/Redirect/Get after a successful submission",
                "Spam prevention with a honeypot field and a signed form timestamp",
                "Per-IP submission rate limiting",
                "Optional email notification that never blocks saving the message",
                "Resume PDF upload with extension, size, and file-signature validation",
                "Print-friendly resume page",
                "Sitemap, robots.txt, Open Graph tags, and custom 404 and 500 pages",
                "Idempotent seed_portfolio management command",
                "Automated test suite",
            ]
        ),
        "challenges": (
            "Spam without CAPTCHAs. A hidden honeypot field and a signed timestamp that rejects "
            "submissions sent within seconds of the page loading stop most automated spam "
            "without adding friction for real visitors.\n\n"
            "Email that cannot lose messages. The message is saved to the database first; the "
            "optional notification email runs afterwards and its failures are logged, not shown "
            "to the visitor.\n\n"
            "Re-runnable seed data. The seed command only creates records that are missing, so "
            "running it again after editing content in the admin never overwrites those edits."
        ),
        "setup_instructions": "\n".join(
            [
                "python -m venv .venv",
                "source .venv/bin/activate",
                "pip install -r requirements.txt",
                "cp .env.example .env",
                "python manage.py migrate",
                "python manage.py seed_portfolio",
                "python manage.py createsuperuser",
                "python manage.py runserver",
            ]
        ),
        "resume_highlights": "\n".join(
            [
                "Built a content-managed portfolio with Django, server-rendered templates, and the Django admin.",
                "Implemented a contact form with ModelForm validation, CSRF protection, spam prevention, and rate limiting.",
                "Configured environment-based settings for PostgreSQL, WhiteNoise, Gunicorn, and HTTPS in production.",
                "Wrote automated tests for pages, project visibility, models, and the contact workflow.",
            ]
        ),
    },
]


class Command(BaseCommand):
    help = "Create initial portfolio content. Existing records are never overwritten."

    @transaction.atomic
    def handle(self, *args, **options):
        created = {"profile": 0, "skills": 0, "projects": 0}

        if not DeveloperProfile.objects.exists():
            DeveloperProfile.objects.create(**PROFILE)
            created["profile"] = 1

        for active, groups in ((True, SKILLS), (False, HIDDEN_SKILLS)):
            for category, names in groups.items():
                for order, name in enumerate(names, start=1):
                    if Skill.objects.filter(name__iexact=name).exists():
                        continue
                    Skill.objects.create(
                        name=name, category=category, display_order=order, is_active=active
                    )
                    created["skills"] += 1

        for data in PROJECTS:
            data = dict(data)
            tech_names = data.pop("technologies")
            if Project.objects.filter(slug=data["slug"]).exists():
                continue
            project = Project.objects.create(is_published=True, is_featured=True, **data)
            project.technologies.set(Skill.objects.filter(name__in=tech_names))
            created["projects"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: created {profile} profile, {skills} skills, {projects} projects. "
                "Existing records were left unchanged.".format(**created)
            )
        )
