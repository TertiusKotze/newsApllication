# News Application

A Django news platform for **readers**, **journalists**, and **editors**.
Journalists write articles (independently or for a publisher), editors
review and approve them, and readers subscribe to publishers or
journalists. When an editor approves an article, subscribers are emailed
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
git clone https://github.com/<your-github-username>/News_application.git
```

### 2.2 Enter the project folder

All later commands must be run from **inside** this folder. Otherwise
files such as `requirements.txt` and `manage.py` will not be found.

```bash
cd News_application
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

Make sure you are still in the `News_application` folder:

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

Still inside `News_application` with the virtual environment active:

```bash
python manage.py migrate
```

This creates all tables in MariaDB and the **Reader**, **Editor**, and
**Journalist** groups with their permissions.

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
| Editor | Editor | View, update, delete, and **approve** articles, and manage newsletters. |

The user is added to the matching group automatically and logged in.

### 6.2 Try the full workflow

1. Register a **Journalist** and create an article at *Write article*.
   New articles are not approved yet.
2. Log out and register a **Reader**. Under *Subscriptions*, follow the
   journalist.
3. Log out and register an **Editor**. Open *Pending articles* and
   click **Approve**.
4. The approval:
   - emails the reader (printed in the `runserver` terminal, because the
     console email backend is used in development), and
   - POSTs the article to `/api/approved/`, where it is stored in
     `ApprovedArticleLog` (visible in `/admin/`).
5. The article now appears on the home page for everyone.

Publishers are created in the admin site (`/admin/`), where editors and
journalists can be assigned to them.

### 6.3 Pages

| URL | Who can use it |
| --- | --- |
| `/accounts/register/` | Anyone (choose Reader, Journalist, or Editor) |
| `/accounts/login/` | All users |
| `/` | Approved articles (everyone) |
| `/articles/<id>/` | Article detail |
| `/articles/create/` | Journalists |
| `/articles/mine/` | Journalists (their own articles) |
| `/articles/pending/` | Editors (review and approve) |
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
| PUT/PATCH | `/api/articles/<id>/` | Editors, or the journalist who wrote it (only editors may set `approved`) |
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
- editors approving and deleting articles
- newsletter permissions and ownership
- the approval signal, with email and the `/api/approved/` POST mocked

---

## 9. Project structure and design

```
News_application/
├── manage.py
├── requirements.txt
├── .env.example            # template for your .env settings
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

- **User** (custom): one `role` (`reader`, `journalist`, `editor`).
  - Reader fields: `subscribed_publishers` (M2M to Publisher) and
    `subscribed_journalists` (M2M to journalist users).
  - Journalist data: `articles` and `newsletters` (reverse relations).
  - Reader-only helpers return `None` for journalists, and vice versa.
    Subscription fields are cleared for non-readers.
- **Publisher**: `name`, `description`, M2M `editors`, M2M `journalists`.
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
| `Could not open requirements file` | You are not in the project folder. Run `cd News_application`. |
| `Access denied for user 'news_user'@'localhost'` | `DB_USER` or `DB_PASSWORD` in `.env` does not match step 3.2. |
| `Unknown database 'news_db'` | Run the SQL in step 3.2. |
| `Can't connect to MySQL server on '127.0.0.1'` | MariaDB is not running. Start the MariaDB service. |
| Tests fail with `Got an error creating the test database` | Run the `GRANT ... ON test_news_db.*` line from step 3.2. |
| `mysqlclient` fails to install on macOS/Linux | Install the client headers listed in step 2.5. |

