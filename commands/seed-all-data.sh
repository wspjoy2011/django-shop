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
echo "  7. Database statistics"
echo ""

START_TIME=$(date +%s)

echo "Step 1/6: Seeding users..."
echo "-----------------------------------------"
python manage.py seed_users
echo ""

echo "Step 2/6: Seeding catalog data..."
echo "-----------------------------------------"
python manage.py seed_catalog
echo ""

echo "Step 3/6: Seeding currencies..."
echo "-----------------------------------------"
python manage.py seed_currencies
echo ""

echo "Step 4/6: Seeding inventories..."
echo "-----------------------------------------"
python manage.py seed_inventories
echo ""

echo "Step 5/6: Seeding ratings..."
echo "-----------------------------------------"
python manage.py seed_ratings
echo ""

echo "Step 6/6: Seeding favorites..."
echo "-----------------------------------------"
python manage.py seed_favorites
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
echo "========================================="
echo "All Done! Database is fully populated."
echo "========================================="
