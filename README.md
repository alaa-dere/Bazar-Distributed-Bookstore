# Bazar.com – Distributed Bookstore

A multi-tier online bookstore developed for the Distributed and Operating Systems course.

## Project Overview

Bazar.com is a small online bookstore that contains four books.

The system uses a two-tier architecture with three independent microservices:

- **Frontend Service:** Receives client requests and forwards them to the appropriate backend service.
- **Catalog Service:** Manages book information, including titles, topics, prices, and available quantities.
- **Order Service:** Processes book purchases and maintains an order history.

The microservices communicate using HTTP REST APIs and exchange data in JSON format.

## Technology Stack

- Python 3.11
- Flask 3.1.3
- SQLite
- Docker and Docker Compose
- Requests 2.34.2
- pytest 9.2.0
- Git and GitHub

## Project Structure

```text
Bazar-Distributed-Bookstore/
├── frontend/
│   ├── app.py
│   └── Dockerfile
├── catalog/
│   ├── app.py
│   ├── db.py
│   └── Dockerfile
├── order/
│   ├── app.py
│   ├── db.py
│   └── Dockerfile
├── tests/
├── docs/
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── .gitignore
└── README.md
```

## Prerequisites

The following software is required:

- Git
- Docker Desktop with Linux containers and Docker Compose

Python does not need to be installed locally when running the project through Docker.

## Getting Started

### 1. Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd Bazar-Distributed-Bookstore
```

Replace `<REPOSITORY_URL>` with the actual GitHub repository URL.

### 2. Build and Start the Services

Make sure Docker Desktop is running.

Run:

```bash
docker compose up --build -d
```

### 3. Check Service Status

```bash
docker compose ps
```

All three services should eventually report a healthy status.

### 4. Test the Services

The following health endpoints are currently available:

| Service | URL |
|---|---|
| Frontend | http://localhost:5000/health |
| Catalog | http://localhost:5001/health |
| Order | http://localhost:5002/health |

Each endpoint returns a JSON response containing the service name and its running status.

## Database Setup

The system uses two separate SQLite databases:

- `catalog.db`: Stores book information.
- `orders.db`: Stores order records.

Both databases are initialized automatically when their corresponding services start.

Docker named volumes provide persistent storage:

- `catalog_data`
- `order_data`

The database files are not committed to GitHub.

## Docker Commands

Build and run the services:

```bash
docker compose up --build -d
```

View logs:

```bash
docker compose logs -f
```

Check container status:

```bash
docker compose ps
```

Stop and remove the containers while preserving the database volumes:

```bash
docker compose down
```

**Warning:** Running `docker compose down -v` also removes the database volumes and deletes the stored data.

## Current Development Status

The initial infrastructure setup includes:

- Three Flask microservice skeletons
- Dockerfiles for all three services
- Docker Compose configuration
- SQLite database initialization
- Persistent Docker volumes
- Health-check endpoints

The search, information, purchase, and catalog update APIs are not implemented yet.

## Development Workflow

Contributors should create separate feature branches for their work.

Suggested branches:

- `feature/catalog`
- `feature/order`
- `feature/frontend`

Changes should be committed with descriptive messages and merged into the main branch through pull requests.

## Future Development

The next stages will include:

- Catalog search and information APIs
- Catalog stock and price updates
- Order processing
- Frontend request forwarding
- Integration and concurrency testing
- Final documentation and test outputs
