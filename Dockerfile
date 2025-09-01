FROM python:3.12.9

# Define application root directory
ARG APP_ROOT=/usr/src/clothing-store
ENV APP_ROOT=${APP_ROOT}
# Define uv root directory for dependency operations
ARG DEPS_WORK_DIR=/usr/src/uv

# Python configuration
# Don't write .pyc files
# Output logs immediately
# Allow pip to cache packages
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off

# Installing dependencies
RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    dos2unix \
    && apt clean

# Install uv
RUN python -m pip install --upgrade pip && \
    pip install uv

# Copy dependency descriptors
COPY pyproject.toml uv.lock ${DEPS_WORK_DIR}/

# Set working directory for dependency install
WORKDIR ${DEPS_WORK_DIR}

# Create a virtual environment and install only main (non-dev) deps from lockfile
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV
RUN uv venv "${VIRTUAL_ENV}" && \
    uv sync --frozen --no-dev && \
    ln -sf /opt/venv/bin/python3 /usr/bin/python3 && \
    ln -sf /opt/venv/bin/python3 /usr/bin/python

# Set working directory for the app itself
WORKDIR ${APP_ROOT}

# Copy source code into the container
COPY src/ .

# Copy commands into the container
COPY commands /commands

# Ensure Unix-style line endings for scripts
RUN dos2unix /commands/*.sh

# Add execute permissions for scripts
RUN chmod +x /commands/*.sh

# Create symlinks for all executable files in /commands directory
RUN for file in /commands/*; do \
        if [ -f "$file" ] && [ -x "$file" ]; then \
            ln -sf "$file" "/usr/local/bin/$(basename "$file")"; \
        fi; \
    done
