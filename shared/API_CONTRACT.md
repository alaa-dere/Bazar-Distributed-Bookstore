# Bazar.com — Shared API Contract

## Service URLs

| Service | Docker URL | Host URL |
|---|---|---|
| Frontend | http://frontend:5000 | http://localhost:5000 |
| Catalog | http://catalog:5001 | http://localhost:5001 |
| Order | http://order:5002 | http://localhost:5002 |

All APIs return JSON.

## 1. Catalog — Search Books

**GET `/search/<topic>`**

Example: `GET /search/distributed%20systems`

Success — HTTP 200:

```json
[
  {
    "id": 1,
    "title": "How to get a good grade in DOS in 40 minutes a day"
  },
  {
    "id": 2,
    "title": "RPCs for Noobs"
  }
]
```

No matches: HTTP 200 with `[]`.

## 2. Catalog — Book Information

**GET `/info/<id>`**

Example: `GET /info/2`

Success — HTTP 200:

```json
{
  "title": "RPCs for Noobs",
  "quantity": 5,
  "price": 50.0
}
```

Unknown book — HTTP 404:

```json
{
  "error": "Book not found"
}
```

## 3. Catalog — Update Book

**PUT `/update/<id>`**

Supported JSON fields:

- `price`: Set the book price (non-negative number).
- `quantity_delta`: Increase or decrease the stock (integer).

Example:

```json
{
  "quantity_delta": 5
}
```

Success — HTTP 200:

```json
{
  "id": 2,
  "price": 50.0,
  "quantity": 10
}
```

Invalid values: HTTP 400.

Unknown book: HTTP 404.

Insufficient stock: HTTP 409.

Quantity must never become negative.

## 4. Catalog — Atomic Stock Decrement

**POST `/decrement/<id>`**

Decreases quantity by exactly one using a conditional SQLite UPDATE.

Success — HTTP 200:

```json
{
  "id": 2,
  "quantity": 4
}
```

Out of stock: HTTP 409.

Unknown book: HTTP 404.

This operation is designed to be safe when concurrent purchase requests arrive.

## 5. Order — Purchase Book

**POST `/purchase/<id>`**

The Order Service must:

1. Query Catalog to verify the book exists and obtain book information.
2. Request an atomic one-unit stock decrement from Catalog.
3. Record the successful purchase in the Orders database.
4. Return the purchase result.

Success — HTTP 200:

```json
{
  "message": "bought book RPCs for Noobs",
  "book_id": 2,
  "title": "RPCs for Noobs",
  "status": "success"
}
```

Unknown book: HTTP 404.

Out of stock: HTTP 409.

Backend unavailable: HTTP 503.

Unexpected failures must be logged. The implementation must define how it handles failure after stock has been decremented but before an order is recorded.

## 6. Frontend APIs

The Frontend forwards requests to the appropriate backend service:

- GET `/search/<topic>` → Catalog
- GET `/info/<id>` → Catalog
- POST `/purchase/<id>` → Order

Responses should preserve the backend HTTP status and JSON response where appropriate.

## General Rules

- Book IDs are integers.
- Prices must be non-negative.
- Quantities must never be negative.
- Requests and responses use JSON.
- Each service owns its SQLite database.
- Services communicate through HTTP REST, not direct access to another service's database.
- Internal service addresses come from environment variables.
- Return meaningful errors and HTTP status codes.
- Log requests and important operations.
