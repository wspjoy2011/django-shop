#!/bin/sh
set -e

echo "Creating Django admin user..."

python manage.py create_admin

echo "Admin user creation completed successfully!"
