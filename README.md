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
│   ├── catalog_routes.py
│   ├── order_routes.py
│   └── Dockerfile
├── catalog/
│   ├── app.py
│   ├── db.py
│   └── Dockerfile
├── order/
│   ├── app.py
│   ├── db.py
│   └── Dockerfile
├── client/
│   └── client.py
├── tests/
│   ├── test_catalog.py
│   ├── test_frontend.py
│   └── test_order.py
├── shared/
│   └── API_CONTRACT.md
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

The services run inside Docker, so Python is not needed for them.
Python 3.11 is only needed on the host to run the client and the tests.

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/alaa-dere/Bazar-Distributed-Bookstore.git
cd Bazar-Distributed-Bookstore
```

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

### 4. Check the Health Endpoints

| Service | URL |
|---|---|
| Frontend | http://localhost:5000/health |
| Catalog | http://localhost:5001/health |
| Order | http://localhost:5002/health |

Each endpoint returns a JSON response containing the service name and its running status.

## REST API

The full API contract is in [shared/API_CONTRACT.md](shared/API_CONTRACT.md).

| Service | Method | Endpoint | Description |
|---|---|---|---|
| Frontend | GET | `/search/<topic>` | Forwards to the catalog search |
| Frontend | GET | `/info/<id>` | Forwards to the catalog info |
| Frontend | POST | `/purchase/<id>` | Forwards to the order service |
| Catalog | GET | `/search/<topic>` | Books with this topic |
| Catalog | GET | `/info/<id>` | Title, quantity and price of a book |
| Catalog | PUT | `/update/<id>` | Change the price or the stock |
| Catalog | POST | `/decrement/<id>` | Take one copy from the stock |
| Order | POST | `/purchase/<id>` | Buy one copy of a book |

### Purchase

```bash
curl -X POST http://localhost:5000/purchase/2
```

Success (HTTP 200):

```json
{
  "message": "bought book RPCs for Noobs",
  "book_id": 2,
  "title": "RPCs for Noobs",
  "status": "success"
}
```

How a purchase works:

1. The frontend forwards the request to the order service.
2. The order service calls `GET /info/<id>` on the catalog to check that
   the book exists and is in stock.
3. The order service calls `POST /decrement/<id>` on the catalog. The
   catalog uses a conditional `UPDATE`, so two buyers can never both get
   the last copy.
4. The order is saved in `orders.db` and the order service prints
   `bought book <title>`.
5. If the order cannot be saved, the order service gives the copy back
   with `PUT /update/<id>` and `{"quantity_delta": 1}`.

Error responses:

| Status | Meaning |
|---|---|
| 404 | Book not found |
| 409 | Book out of stock |
| 500 | Order could not be saved (the copy is given back) |
| 503 | Order or catalog service unavailable |
| 504 | Order service timed out |

## Running the Client

The client is a small command line program in `client/client.py`. It runs
on the host and sends requests to the frontend at `http://localhost:5000`.

Install the requirements once:

```bash
pip install -r requirements.txt
```

Start the services with `docker compose up --build -d`, then run:

```bash
python client/client.py search "distributed systems"
python client/client.py search "undergraduate school"
python client/client.py info 2
python client/client.py purchase 2
```

To use a different frontend address, set `FRONTEND_URL`:

```bash
FRONTEND_URL=http://192.168.1.10:5000 python client/client.py info 2
```

On Windows (cmd):

```bat
set FRONTEND_URL=http://192.168.1.10:5000
python client\client.py info 2
```

Sample output of the client is saved in `docs/sample_output.txt`.

## Running the Tests

The tests use Flask test clients and temporary SQLite databases, so
Docker does not need to be running.

```bash
pip install -r requirements.txt
python -m pytest -v tests
```

| File | What it tests |
|---|---|
| `tests/test_catalog.py` | Catalog search, info, update, decrement and concurrent decrements |
| `tests/test_frontend.py` | Frontend forwarding to the catalog |
| `tests/test_order.py` | Purchase success, 404, 409, catalog down or timeout, stock restore, and two buyers racing for the last copy |

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

## Development Workflow

Contributors should create separate feature branches for their work.

Branch naming:

- `feature/<name>` for new code, e.g. `feature/client`
- `docs/<name>` for documentation, e.g. `docs/readme`

Changes should be committed with descriptive messages and merged into the main branch through pull requests.
