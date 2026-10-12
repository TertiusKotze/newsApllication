# News Application

A Django news platform for **readers**, **journalists**, **editors** and
**publishers**. Publishers register their publication and add/remove
their own editors and journalists. Journalists write articles
(independently or for a publisher). Publisher articles are approved by
that publisher's editors; independent articles are approved by their
author once finished. Readers subscribe to publishers or journalists.
When an article is approved, subscribers are emailed
and the article is logged to the project's own REST endpoint
(`/api/approved/`).

The project uses **MariaDB** as its database.

---

## Contents

1. [Requirements](#1-requirements)
2. [Installation](#2-installation)
3. [Create the MariaDB database](#3-create-the-mariadb-database)
4. [Configure the .env file](#4-configure-the-env-file)
5. [Migrate and run](#5-migrate-and-run)
6. [Using the application](#6-using-the-application)
7. [REST API](#7-rest-api)
8. [Running the tests](#8-running-the-tests)
9. [Project structure and design](#9-project-structure-and-design)
10. [Troubleshooting](#10-troubleshooting)
11. [Run with Docker](#11-run-with-docker)
12. [Sphinx documentation](#12-sphinx-documentation)

---

## 1. Requirements

Install these before you start:

| Software | Version | Download |
| --- | --- | --- |
| Python | 3.11 or newer | https://www.python.org/downloads/ |
| MariaDB Server | 10.5 or newer | https://mariadb.org/download/ |
| Git | any recent version | https://git-scm.com/downloads |

When the MariaDB installer asks for a **root password**, choose one and
write it down. You need it in step 3.

> **Windows:** when installing Python, tick **"Add python.exe to PATH"**.

---

## 2. Installation

Open a terminal (PowerShell on Windows, Terminal on macOS/Linux) and run
the commands below **one at a time**.

### 2.1 Clone the repository

```bash
git clone https://github.com/TertiusKotze/newsApllication.git
```

### 2.2 Enter the project folder

All later commands must be run from **inside** this folder. Otherwise
files such as `requirements.txt` and `manage.py` will not be found.

```bash
cd newsApllication
```

### 2.3 Create a virtual environment

This creates a `venv` folder inside the project folder.

```bash
python -m venv venv
```

### 2.4 Activate the virtual environment

| System | Command |
| --- | --- |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
| Windows (Command Prompt) | `venv\Scripts\activate.bat` |
| macOS / Linux | `source venv/bin/activate` |

Your prompt now starts with `(venv)`.

> **Windows PowerShell error "running scripts is disabled"?** Run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`,
> then activate again.

### 2.5 Install the dependencies

Make sure you are still in the `newsApllication` folder:

```bash
pip install -r requirements.txt
```

This installs Django, Django REST Framework, Simple JWT, `mysqlclient`
(the MariaDB driver), `python-dotenv`, and `requests`.

> **macOS/Linux:** `mysqlclient` needs the MariaDB/MySQL client headers.
> On macOS run `brew install mariadb pkg-config`. On Ubuntu/Debian run
> `sudo apt install libmariadb-dev pkg-config build-essential`. Then run
> `pip install -r requirements.txt` again.

---

## 3. Create the MariaDB database

### 3.1 Open the MariaDB client as root

| System | Command |
| --- | --- |
| Windows | `& "C:\Program Files\MariaDB 11.4\bin\mariadb.exe" -u root -p` (change `11.4` to your installed version) |
| macOS / Linux | `sudo mariadb -u root -p` |

Enter the root password you chose when installing MariaDB. The prompt
changes to `MariaDB [(none)]>`.

### 3.2 Create the database and a dedicated user

Copy and paste the SQL below into the MariaDB prompt. **Replace
`choose-a-strong-password`** with a password of your own and remember it
for step 4.

```sql
CREATE DATABASE news_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'news_user'@'localhost' IDENTIFIED BY 'choose-a-strong-password';

-- Access to the application database
GRANT ALL PRIVILEGES ON news_db.* TO 'news_user'@'localhost';

-- Access to the temporary database Django creates when running tests
GRANT ALL PRIVILEGES ON test_news_db.* TO 'news_user'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

---

## 4. Configure the .env file

The project reads its database credentials and other settings from a
`.env` file in the project folder. A template called `.env.example` is
included.

### 4.1 Copy the template

| System | Command |
| --- | --- |
| Windows | `copy .env.example .env` |
| macOS / Linux | `cp .env.example .env` |

### 4.2 Edit the values

Open `.env` in any text editor and update at least these lines:

```ini
DJANGO_SECRET_KEY=any-long-random-string-you-like
DB_NAME=news_db
DB_USER=news_user
DB_PASSWORD=the-password-you-chose-in-step-3.2
DB_HOST=127.0.0.1
DB_PORT=3306
```

| Variable | Meaning |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django's secret key. Any long random string. |
| `DJANGO_DEBUG` | `1` for development, `0` for production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names allowed to serve the site. |
| `DB_NAME` | MariaDB database name from step 3.2. |
| `DB_USER` / `DB_PASSWORD` | MariaDB user and password from step 3.2. |
| `DB_HOST` / `DB_PORT` | Where MariaDB runs (defaults: `127.0.0.1`, `3306`). |
| `DEFAULT_FROM_EMAIL` | Sender address for approval emails. |
| `INTERNAL_API_BASE_URL` | Base URL used to POST to `/api/approved/`. |
| `INTERNAL_API_KEY` | Shared key protecting `/api/approved/`. |

> `.env` holds your passwords and is excluded by `.gitignore`. Never
> commit it to GitHub.

---

## 5. Migrate and run

Still inside `newsApllication` with the virtual environment active:

```bash
python manage.py migrate
```

This creates all tables in MariaDB and the **Reader**, **Editor**,
**Journalist** and **Publisher** groups with their permissions.

Optionally load demo data (see 6.2):

```bash
python manage.py seed_demo
```

Optionally, create an administrator for the Django admin site:

```bash
python manage.py createsuperuser
```

Start the development server:

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser. Press `Ctrl+C` in the
terminal to stop the server.

---

## 6. Using the application

### 6.1 Register an account

Go to **http://127.0.0.1:8000/accounts/register/** and choose an
**Account type**:

| Account type | Group | What the user can do |
| --- | --- | --- |
| Reader | Reader | View approved articles and newsletters, and manage subscriptions to publishers and journalists. |
| Journalist | Journalist | Create, view, update, and delete their own articles and newsletters. |
| Editor | Editor | View, update, delete articles/newsletters, and **approve articles of the publishers they belong to**. |
| Publisher | Publisher | Owns a publication (name entered at registration) and **adds/removes its own editors and journalists** at *Manage publication*. |

The user is added to the matching group automatically and logged in.
Email addresses must be unique (case-insensitive) so password resets and
subscription emails always reach the right account.

**Who approves what?**

| Article type | Approved by |
| --- | --- |
| Publisher article | An editor of that publisher |
| Independent article (no publisher) | The journalist who wrote it, via *Pending review*, when the draft is finished |

### 6.2 Demo data (optional)

`python manage.py seed_demo` creates:

| Username | Password | Role |
| --- | --- | --- |
| `tkpublishing` | `Publish@99` | Publisher of **TKPublishing** |
| `tertius` | `Journalist@99` | Journalist (member of TKPublishing) |
| `editor1` | `Editor@99` | Editor (member of TKPublishing) |
| `reader1` | `Reader@99` | Reader (subscribed to TKPublishing and tertius) |

plus approved articles, humorous pending articles and a newsletter.

### 6.3 Try the full workflow

1. Register a **Publisher** (enter a publication name).
2. Register a **Journalist** and an **Editor**.
3. Log in as the publisher, open *Manage publication* and tick the
   journalist and editor to add them (untick to remove).
4. Log in as the journalist and write an article for the publisher, or
   leave it *Independent* and approve it yourself under *Pending review*.
5. Register a **Reader** and follow the publisher/journalist under
   *Subscriptions*.
6. Log in as the editor, open *Pending review* and click **Approve**.
7. The approval:
   - emails the reader (printed in the `runserver` terminal, because the
     console email backend is used in development), and
   - POSTs the article to `/api/approved/`, where it is stored in
     `ApprovedArticleLog` (visible in `/admin/`).
8. The article now appears on the home page for everyone.

The admin site is only for maintenance; every feature is available in
the front end.

### 6.4 Pages

| URL | Who can use it |
| --- | --- |
| `/accounts/register/` | Anyone (choose Reader, Journalist, Editor, or Publisher) |
| `/publisher/manage/` | Publishers (add/remove editors and journalists) |
| `/accounts/login/` | All users |
| `/` | Approved articles (everyone) |
| `/articles/<id>/` | Article detail |
| `/articles/create/` | Journalists |
| `/articles/mine/` | Journalists (their own articles) |
| `/articles/pending/` | Editors (their publishers' articles) and journalists (own independent drafts) |
| `/newsletters/` | All logged-in users |
| `/subscriptions/` | Readers |

---

## 7. REST API

### 7.1 Authentication (JWT)

Get a token:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
     -H "Content-Type: application/json" \
     -d "{\"username\": \"myuser\", \"password\": \"mypassword\"}"
```

Send the `access` token on every request:

```
Authorization: Bearer <access-token>
```

Refresh an expired token with `POST /api/token/refresh/`, sending
`{"refresh": "<refresh-token>"}`.

### 7.2 Endpoints

| Method | Endpoint | Who |
| --- | --- | --- |
| GET | `/api/articles/` | Any logged-in user: all approved articles |
| GET | `/api/articles/subscribed/` | Readers: articles from their subscriptions |
| GET | `/api/articles/<id>/` | Any logged-in user (readers: approved only) |
| POST | `/api/articles/` | Journalists only |
| PUT/PATCH | `/api/articles/<id>/` | Editors, or the journalist who wrote it (`approved=true`: publisher's editors for publisher articles, the author for independent ones) |
| DELETE | `/api/articles/<id>/` | Editors, or the journalist who wrote it |
| GET/POST | `/api/newsletters/` | Read: everyone. Create: journalists and editors |
| GET/PUT/DELETE | `/api/newsletters/<id>/` | Read: everyone. Change: editors or the owning journalist |
| POST | `/api/approved/` | Internal. Requires the `X-Internal-Key` header |

Serializers are provided for `User`, `Publisher`, `Article`, and
`Newsletter`.

---

## 8. Running the tests

The tests run against MariaDB. Django creates a temporary
`test_news_db` database (that is why step 3.2 grants access to it) and
deletes it afterwards.

```bash
python manage.py test news
```

The tests cover:

- registration for every role and rejection of invalid input
- authenticated access for each role, with successful and failed requests
- readers only receiving content from their subscriptions
- journalists creating articles, and non-journalists being refused
- editors approving only their publisher's articles, and deleting
- independent journalists approving their own articles
- unique email addresses on registration
- publisher registration and adding/removing staff
- newsletter permissions and ownership
- the approval signal, with email and the `/api/approved/` POST mocked

---

## 9. Project structure and design

```
newsApllication/
├── manage.py
├── requirements.txt
├── Dockerfile              # app image used by Docker Compose
├── docker-compose.yml      # Django app plus MariaDB
├── entrypoint.sh           # waits for MariaDB, migrates, starts the server
├── .env.example            # template for your .env settings
├── docs/                   # Sphinx source and generated HTML
├── news_project/           # project settings and root URLs
├── news/                   # the news application
│   ├── models.py           # User, Publisher, Article, Newsletter, ApprovedArticleLog
│   ├── views.py            # HTML views
│   ├── api_views.py        # REST API views
│   ├── serializers.py      # DRF serializers
│   ├── permissions.py      # role-based API permissions
│   ├── mixins.py           # role-based HTML view access
│   ├── forms.py            # registration, article, newsletter, subscription forms
│   ├── signals.py          # group setup and approval side effects
│   ├── tests.py            # automated tests
│   ├── migrations/
│   └── templates/news/     # templates belonging to the news app
└── templates/              # project-wide templates
    ├── base.html           # shared layout used by every app
    └── registration/       # login, logout, register, password pages
```

The `news` app keeps its own templates in `news/templates/news/`.
Project-wide templates (`base.html` and the authentication pages) live in
the top-level `templates/` folder because they are not tied to one app.

### Data model (normalised)

- **User** (custom): unique `email`, one `role` (`reader`,
  `journalist`, `editor`, `publisher`).
  - Reader fields: `subscribed_publishers` (M2M to Publisher) and
    `subscribed_journalists` (M2M to journalist users).
  - Journalist data: `articles` and `newsletters` (reverse relations).
  - Reader-only helpers return `None` for journalists, and vice versa.
    Subscription fields are cleared for non-readers.
- **Publisher**: `name`, `description`, `owner` (publisher user), M2M
  `editors`, M2M `journalists`.
- **Article**: `title`, `content`, `author` (journalist), `created_at`,
  `approved`, optional `publisher`. Independent articles have no
  publisher.
- **Newsletter**: `title`, `description`, `created_at`, `author`, M2M
  `articles`.
- **ApprovedArticleLog**: payloads received by `/api/approved/`.

### Approval workflow (Option 1: Django signals)

A `pre_save` signal records whether the article was already approved. A
`post_save` signal detects the change from *unapproved* to *approved* and
then:

1. emails every reader subscribed to the author or the publisher, and
2. POSTs the article to `/api/approved/` with the `requests` library.

Failures in either step are caught so they never block the approval.

---

## 10. Troubleshooting

| Problem | Fix |
| --- | --- |
| `No module named 'dotenv'` / `'rest_framework'` | Activate the virtual environment (step 2.4) and run `pip install -r requirements.txt`. |
| `Could not open requirements file` | You are not in the project folder. Run `cd newsApllication`. |
| `Access denied for user 'news_user'@'localhost'` | `DB_USER` or `DB_PASSWORD` in `.env` does not match step 3.2. |
| `Unknown database 'news_db'` | Run the SQL in step 3.2. |
| `Can't connect to MySQL server on '127.0.0.1'` | MariaDB is not running. Start the MariaDB service. |
| Tests fail with `Got an error creating the test database` | Run the `GRANT ... ON test_news_db.*` line from step 3.2. |
| `mysqlclient` fails to install on macOS/Linux | Install the client headers listed in step 2.5. |
| Docker web container exits waiting for the database | Check that `DB_PASSWORD` in `.env` matches the password MariaDB was first created with. If you changed it, run `docker compose down -v` and start again. |

---

## 11. Run with Docker

Docker is an alternative to the virtualenv steps in sections 2 to 5. You
need [Docker Desktop](https://www.docker.com/products/docker-desktop/) or
Docker Engine with the Compose plugin. You do **not** need a local Python
or MariaDB install for this path.

### 11.1 Choose your own secrets

Copy the template if you want your own passwords (recommended):

| System | Command |
| --- | --- |
| Windows | `copy .env.example .env` |
| macOS / Linux | `cp .env.example .env` |

Edit `.env` and set `DJANGO_SECRET_KEY`, `DB_PASSWORD`, and
`INTERNAL_API_KEY` yourself. Do not commit `.env`. Docker Compose reads
those names from `.env` when the file exists.

If you skip this step, Compose uses the local placeholders in
`docker-compose.yml` (`change-me` and similar). Those placeholders are
only for a private machine. Replace them before sharing the computer or
deploying the stack.

`DB_HOST` inside the web container is always the Compose service name
`db`, even if your `.env` file says `127.0.0.1` for the virtualenv
workflow.

### 11.2 Build and run

From the project folder:

```bash
docker compose up --build
```

The first run builds the image, starts MariaDB, waits until it accepts
connections, applies migrations, and serves the site on
**http://127.0.0.1:8000/**.

In another terminal, optional demo data:

```bash
docker compose exec web python manage.py seed_demo
```

Demo usernames and passwords are listed in section 6.2. Stop the stack
with `Ctrl+C`, then:

```bash
docker compose down
```

Add `-v` only when you want to delete the database volume as well.

### 11.3 Run the image without Compose

If you already have MariaDB on another host, build and run the app image
yourself. Replace the password and secret with values you choose:

```bash
docker build -t news-app .
docker run --rm -p 8000:8000 \
  -e DJANGO_SECRET_KEY=your-own-long-random-string \
  -e DJANGO_DEBUG=1 \
  -e DJANGO_ALLOWED_HOSTS=* \
  -e DB_NAME=news_db \
  -e DB_USER=news_user \
  -e DB_PASSWORD=your-own-database-password \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=3306 \
  -e INTERNAL_API_KEY=your-own-internal-key \
  news-app
```

The database and user must already exist and must be reachable from the
container.

---

## 12. Sphinx documentation

User-facing HTML documentation is generated with Sphinx and stored in
`docs/_build/html`. Open `docs/_build/html/index.html` in a browser. It
is committed so you can read it without installing Sphinx.

To rebuild it after docstring changes, with the virtual environment
active and the project dependencies installed:

```bash
pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```

`docs/conf.py` adds the project root to `sys.path`, sets
`DJANGO_SETTINGS_MODULE` to `news_project.settings`, and calls
`django.setup()` so autodoc can import the Django apps. Rebuilding the
docs needs the same packages as the app, including `mysqlclient`, because
Django loads the MariaDB backend while it sets up.

