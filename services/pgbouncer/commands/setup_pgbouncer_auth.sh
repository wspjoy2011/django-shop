#!/bin/bash

set -e

# Check if PGBOUNCER_USER and PGBOUNCER_PASSWORD are set
if [ -z "$PGBOUNCER_USER" ] || [ -z "$PGBOUNCER_PASSWORD" ]; then
    echo "ERROR: PGBOUNCER_USER and PGBOUNCER_PASSWORD must be set."
    exit 1
fi

# Create userlist.txt file
echo "Creating userlist.txt file."
USERLIST_FILE="/etc/pgbouncer/userlist.txt"

# Function to generate MD5 hash for PostgreSQL
# Format: "md5" + md5(password + username)
generate_md5() {
    local username="$1"
    local password="$2"
    echo -n "md5$(echo -n "${password}${username}" | md5sum | cut -d ' ' -f 1)"
}

# Create or update the userlist file
echo "\"$PGBOUNCER_USER\" \"$(generate_md5 "$PGBOUNCER_USER" "$PGBOUNCER_PASSWORD")\"" > $USERLIST_FILE
echo "Auth setup complete for user: $PGBOUNCER_USER"

# Create or update pgbouncer.ini with proper auth settings
cat > /etc/pgbouncer/pgbouncer.ini << EOL
[databases]
* = host=${POSTGRES_HOST} port=${POSTGRES_DB_PORT:-5432} dbname=${POSTGRES_DB} user=${POSTGRES_USER} password=${POSTGRES_PASSWORD}

[pgbouncer]
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
listen_addr = *
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
admin_users = ${PGBOUNCER_USER}
stats_users = ${PGBOUNCER_USER}
pool_mode = transaction
server_reset_query = DISCARD ALL
max_client_conn = ${MAX_CLIENT_CONN:-200}
default_pool_size = ${DEFAULT_POOL_SIZE:-20}
ignore_startup_parameters = extra_float_digits
EOL

echo "PgBouncer configuration complete."

# Create log directory if it doesn't exist
mkdir -p /var/log/pgbouncer
chown -R postgres:postgres /var/log/pgbouncer

# Create run directory if it doesn't exist
mkdir -p /var/run/pgbouncer
chown -R postgres:postgres /var/run/pgbouncer

# Launch the main process
exec "$@"
