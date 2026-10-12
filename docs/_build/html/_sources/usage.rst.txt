Using the application
=====================

Virtual environment
-------------------

From the project root:

1. Create a virtual environment with ``python -m venv venv``.
2. Activate it (``source venv/bin/activate`` on macOS/Linux, or
   ``venv\\Scripts\\activate`` on Windows).
3. Install packages with ``pip install -r requirements.txt``.
4. Copy ``.env.example`` to ``.env`` and set your own MariaDB password
   and ``DJANGO_SECRET_KEY``. Never commit ``.env``.
5. Create the MariaDB database and user described in ``README.md``.
6. Run ``python manage.py migrate`` and ``python manage.py runserver``.

Docker
------

Docker Compose starts MariaDB and the Django app together. From the
project root:

.. code-block:: bash

   docker compose up --build

Then open http://127.0.0.1:8000/ . The Compose file reads passwords from
your ``.env`` file when that file exists. If it does not, it uses the
local development placeholders shown in ``docker-compose.yml``. Replace
those placeholders before using the stack anywhere other than your own
machine.

Stop the stack with ``docker compose down``.

Rebuild the documentation
-------------------------

The HTML in ``docs/_build/html`` is already generated. To rebuild it
after you change docstrings, install Sphinx and run:

.. code-block:: bash

   pip install -r docs/requirements.txt
   sphinx-build -b html docs docs/_build/html
