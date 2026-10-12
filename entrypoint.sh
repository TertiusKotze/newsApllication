#!/bin/sh
# Wait for MariaDB, apply migrations, then start the Django server.
set -eu

echo "Waiting for the database..."
python - << 'PY'
import os
import sys
import time

import MySQLdb

host = os.environ.get("DB_HOST", "127.0.0.1")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER", "news_user")
password = os.environ.get("DB_PASSWORD", "")
name = os.environ.get("DB_NAME", "news_db")

for attempt in range(1, 31):
    try:
        connection = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=password,
            db=name,
        )
        connection.close()
        print("Database is ready.")
        sys.exit(0)
    except MySQLdb.Error as exc:
        print(f"Database not ready (attempt {attempt}/30): {exc}")
        time.sleep(2)

print("Could not connect to the database.", file=sys.stderr)
sys.exit(1)
PY

python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
