# Django Final Project: E-commerce Shop <img src="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/1f6cd.svg" alt="Project Banner" width="32" height="32">

A comprehensive e-commerce platform built with Django, featuring a robust set of functionalities from product catalog management to a complete checkout process. This project is fully containerized using Docker for easy setup and deployment.

## Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
  - [Installation & Launch](#installation--launch)
- [Available Commands](#-available-commands)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## ✨ Features

- **Product Catalog:** Advanced product management with categories, variations, and rich details.
- **Shopping Cart:** Persistent cart functionality for authenticated users.
- **User Accounts:** Full user authentication and profile management.
- **Shipping Address Management:** Google Places API integration for verified and streamlined address entry.
- **Ratings & Favorites:** Users can rate products and create favorite lists.
- **Inventory Management:** Tracks product stock levels.
- **Dockerized Environment:** Fully containerized for development and production consistency.
- **Optimized Database:** Utilizes PgBouncer for connection pooling and includes materialized views for performance.

---

## 🛠️ Tech Stack

- **Backend:** Django, Django REST Framework
- **Database:** PostgreSQL
- **Containerization:** Docker, Docker Compose
- **Frontend:** HTML5, CSS3, JavaScript (ES6 Modules)
- **Build/Task Runner:** GNU Make

---

## 🚀 Getting Started

Follow these instructions to get the project up and running on your local machine.

### Prerequisites

- [Docker](https://www.docker.com/get-started/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- `make` (usually pre-installed on Linux/macOS, available on Windows via WSL or Chocolatey)

### Configuration

Before launching the application, you need to set up your environment configuration files.

1.  **Main Configuration:** Create a `.env` file in the project root by copying the sample file.
    ```bash
    cp .env.sample .env
    ```
2.  **PgBouncer Configuration:** Do the same for the PgBouncer service.
    ```bash
    cp services/pgbouncer/.env.sample services/pgbouncer/.env
    ```
3.  **Edit Variables:** Open both `.env` files and fill in the required values. Pay special attention to:
    - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
    - `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`
    - `GOOGLE_PLACES_API_KEY` (required for the shipping address feature)

### Installation & Launch

The project uses a `Makefile` to streamline the setup process. The recommended sequence for the first-time setup is as follows:

1.  **Build Docker Images:**
    This command builds all the necessary Docker images for the services defined in `docker-compose.yml`.
    ```bash
    make build
    ```

2.  **Apply Database Migrations:**
    This will start the database container and run Django's `migrate` command.
    ```bash
    make migrate
    ```
    
3.  **Seed the Database:**
    Populate the database with initial data for categories, products, users, etc. This is essential for a functional demo.
    ```bash
    make seed-all
    ```
    
4.  **Rebuild Materialized Views:**
    The project uses PostgreSQL materialized views for performance. This command creates and refreshes them.
    ```bash
    make rebuild-pgviews
    ```
    
5.  **Create an Admin Superuser:**
    This creates a Django admin user based on the credentials you provided in the `.env` file.
    ```bash
    make create-admin
    ```

6.  **Start the Application:**
    Finally, launch all project services.
    ```bash
    make up
    ```

Once the services are running, the Django application will be available at `http://localhost:8000`.

---

## 📋 Available Commands

The `Makefile` provides several useful commands to manage the project. Run `make help` to see all available commands.

| Command               | Description                                                                     |
| --------------------- | ------------------------------------------------------------------------------- |
| `make build`          | Builds the Docker containers for the project.                                   |
| `make up`             | Starts all services in the background.                                          |
| `make down`           | Stops all running services.                                                     |
| `make logs`           | Tails the logs from all running containers.                                     |
| `make restart`        | Restarts the services (equivalent to `down`, `build`, `up`).                      |
| `make migrate`        | Runs Django database migrations.                                                |
| `make seed-all`       | Populates the database with a full set of test data.                            |
| `make clean-all`      | Removes all test data from the database.                                        |
| `make create-admin`   | Creates a Django superuser from `.env` variables.                               |
| `make rebuild-pgviews`| Rebuilds and refreshes all Postgres materialized views.                           |
| `make clean`          | **DANGER!** Stops and removes all project containers, volumes, and images.      |

---

## 📂 Project Structure

A brief overview of the key directories:

```
.
├── commands/         # Scripts for custom management commands (seeding, cleaning, etc.)
├── configs/          # Configuration files for various tools (e.g., PostgreSQL)
├── datasets/         # Source data files (CSV, JSON) for database seeding
├── services/         # Docker configurations for supporting services (e.g., PgBouncer)
├── src/              # Main Django project source code
│   ├── apps/         # Individual Django applications (catalog, cart, shipping)
│   ├── core/         # Core project settings, main URL configuration, and WSGI entrypoint
│   ├── static/       # Project-wide static assets (CSS, JS, images)
│   └── templates/    # Base HTML templates and layouts
├── .env.sample       # Sample environment file for the main application
├── Makefile          # Automation scripts for common development tasks
├── docker-compose.yml# Docker Compose configuration defining all application services
└── Dockerfile        # Dockerfile for the main Django web application
```

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
