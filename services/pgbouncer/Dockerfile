# PgBouncer image as a base
FROM edoburu/pgbouncer:v1.24.1-p0

# Use root user
USER root

# Install necessary tools using Alpine's package manager
RUN apk update && \
    apk add --no-cache \
        dos2unix \
        bash && \
    rm -rf /var/cache/apk/*

# Create commands directory
RUN mkdir -p /commands

# Copy our setup script
COPY ./commands/setup_pgbouncer_auth.sh /commands/setup_pgbouncer_auth.sh

# Ensure Unix-style line endings for scripts
RUN dos2unix /commands/*.sh

# Add execute bit to commands files
RUN chmod +x /commands/*.sh

# Create wrapper script to handle user switching
RUN echo '#!/bin/sh' > /commands/entrypoint_wrapper.sh && \
    echo '/commands/setup_pgbouncer_auth.sh' >> /commands/entrypoint_wrapper.sh && \
    echo 'exec su postgres -c "pgbouncer /etc/pgbouncer/pgbouncer.ini"' >> /commands/entrypoint_wrapper.sh && \
    chmod +x /commands/entrypoint_wrapper.sh

# Set the entry point to our wrapper script
ENTRYPOINT ["/commands/entrypoint_wrapper.sh"]
