#!/bin/sh
set -e

echo "========================================="
echo "Database Full Seeding Process"
echo "========================================="
echo "This script will populate the database with all test data:"
echo "  1. Users"
echo "  2. Catalog (products, categories, etc.)"
echo "  3. Currencies"
echo "  4. Inventories"
echo "  5. Ratings (likes/dislikes)"
echo "  6. Favorites"
echo "  7. Carts"
echo "  8. Database statistics"
echo ""

START_TIME=$(date +%s)

echo "Step 1/7: Seeding users..."
echo "-----------------------------------------"
python manage.py seed_users
echo ""

echo "Step 2/7: Seeding catalog data..."
echo "-----------------------------------------"
python manage.py seed_catalog
echo ""

echo "Step 3/7: Seeding currencies..."
echo "-----------------------------------------"
python manage.py seed_currencies
echo ""

echo "Step 4/7: Seeding inventories..."
echo "-----------------------------------------"
python manage.py seed_inventories
echo ""

echo "Step 5/7: Seeding ratings..."
echo "-----------------------------------------"
python manage.py seed_ratings
echo ""

echo "Step 6/7: Seeding favorites..."
echo "-----------------------------------------"
python manage.py seed_favorites
echo ""

echo "Step 7/7: Seeding carts..."
echo "-----------------------------------------"
python manage.py seed_carts
echo ""

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo "========================================="
echo "Database Seeding Completed!"
echo "========================================="
echo "Total execution time: ${MINUTES}m ${SECONDS}s"
echo ""

echo "Generating database statistics..."
echo "-----------------------------------------"
python manage.py database_stats

echo ""
echo "Updating PostgreSQL statistics after cleanup..."
echo "-----------------------------------------"
python manage.py update_stats

echo "Refreshing materialized views with price ranges..."
echo "-----------------------------------------"
python manage.py refresh_db_views
echo ""

echo ""
echo "========================================="
echo "All Done! Database is fully populated."
echo "========================================="
