#!/bin/sh
set -e

echo "Creating migrations..."
python manage.py makemigrations

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Migrations and view synchronization completed successfully!"
