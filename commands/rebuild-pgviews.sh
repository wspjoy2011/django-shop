#!/bin/sh
set -e

echo "========================================="
echo "Rebuilding and Refreshing Postgres Views"
echo "========================================="
echo "This will forcibly drop and recreate all defined pgviews."
echo ""

echo "Step 1/2: Forcibly synchronizing view schemas..."
echo "-----------------------------------------"
python manage.py sync_pgviews --force
echo ""

echo "Step 2/2: Refreshing materialized views with data..."
echo "-----------------------------------------"
python manage.py refresh_db_views
echo ""

echo "========================================="
echo "Postgres Views Rebuild Completed!"
echo "========================================="
