#!/bin/bash

set -e

echo "--- Running Index Rebuild Script ---"

python manage.py rebuild_indexes

echo "--- Index Rebuild Script Finished ---"
