#!/bin/sh
set -e

echo "========================================="
echo "Database Full Cleanup Process"
echo "========================================="
echo "WARNING: This will delete ALL test data from the database!"
echo "This includes:"
echo "  1. Carts"
echo "  2. Favorites"
echo "  3. Ratings (likes/dislikes)"
echo "  4. Inventories"
echo "  5. Currencies"
echo "  6. Catalog (products, categories, etc.)"
echo "  7. Users"
echo ""

read -p "Are you sure you want to continue? Type 'yes' to confirm: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

START_TIME=$(date +%s)

echo "Step 1/7: Cleaning carts..."
echo "-----------------------------------------"
python manage.py clean_carts --yes
echo ""

echo "Step 2/7: Cleaning favorites..."
echo "-----------------------------------------"
python manage.py clean_favorites --yes
echo ""

echo "Step 3/7: Cleaning ratings..."
echo "-----------------------------------------"
python manage.py clean_ratings --yes
echo ""

echo "Step 4/7: Cleaning inventories..."
echo "-----------------------------------------"
python manage.py clear_inventories --confirm
echo ""

echo "Step 5/7: Cleaning currencies..."
echo "-----------------------------------------"
python manage.py clear_currencies --confirm
echo ""

echo "Step 6/7: Cleaning catalog..."
echo "-----------------------------------------"
python manage.py clean_catalog --yes
echo ""

echo "Step 7/7: Cleaning users..."
echo "-----------------------------------------"
python manage.py clean_users --yes
echo ""

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo "========================================="
echo "Database Cleanup Completed!"
echo "========================================="
echo "Total execution time: ${MINUTES}m ${SECONDS}s"
echo ""

echo "Generating final database statistics..."
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
echo "All Done! Database is now empty."
echo "========================================="
