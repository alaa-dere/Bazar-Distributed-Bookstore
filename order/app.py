"""
Order Service for Bazar.com.

Handles book purchases. It checks the book with the Catalog Service,
asks the catalog to decrement the stock, and saves the order in its
own SQLite database.
"""

import os
import sqlite3

import requests
from flask import Flask, jsonify

from db import init_db, DB_PATH

app = Flask(__name__)

CATALOG_URL = os.getenv("CATALOG_URL", "http://localhost:5001")

# So a slow catalog cannot block a purchase request forever.
CATALOG_TIMEOUT = 5

init_db()


class CatalogUnavailable(Exception):
    """Raised when the Catalog Service cannot be reached."""


def call_catalog(method, endpoint, body=None):
    """
    Send a request to the Catalog Service.

    Args:
        method: HTTP method, e.g. "GET" or "POST".
        endpoint: Catalog path, e.g. "/info/2".
        body: Optional JSON body for the request.

    Returns:
        tuple: (status code, JSON body).

    Raises:
        CatalogUnavailable: on connection error, timeout, or non-JSON reply.
    """
    url = f"{CATALOG_URL}{endpoint}"

    try:
        response = requests.request(
            method, url, json=body, timeout=CATALOG_TIMEOUT
        )
        return response.status_code, response.json()

    except requests.Timeout as error:
        print(f"[ORDER] Catalog timeout: {method} {endpoint}", flush=True)
        raise CatalogUnavailable("Catalog service timeout") from error

    except (requests.RequestException, ValueError) as error:
        print(
            f"[ORDER] Catalog unavailable: {method} {endpoint} | {error}",
            flush=True
        )
        raise CatalogUnavailable("Catalog service unavailable") from error


def record_order(item_id, title):
    """
    Save a successful purchase in the orders table.

    Args:
        item_id: ID of the book.
        title: Title of the book.

    Returns:
        int: ID of the new order.

    Raises:
        sqlite3.Error: if the order cannot be saved.
    """
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        cursor = conn.execute(
            "INSERT INTO orders (book_id, book_title, status) VALUES (?, ?, ?)",
            (item_id, title, "success")
        )
        conn.commit()
        return cursor.lastrowid


def restore_stock(item_id):
    """
    Give one copy back to the catalog with PUT /update/<id>.

    Args:
        item_id: ID of the book.

    Returns:
        bool: True if the catalog accepted the update, False otherwise.
    """
    try:
        status, _ = call_catalog(
            "PUT", f"/update/{item_id}", {"quantity_delta": 1}
        )
    except CatalogUnavailable:
        status = None

    if status == 200:
        print(f"[ORDER] Restored one copy of book {item_id}", flush=True)
        return True

    # Here the stock stays one lower than it should be, so the log
    # message is the only way to find and fix it by hand.
    print(
        f"[ORDER] ERROR: could not restore stock for book {item_id} "
        f"(catalog status {status})",
        flush=True
    )
    return False


@app.route("/health", methods=["GET"])
def health():
    """
    Check that the service is running.

    Returns:
        200: {"service", "status"}.
    """
    return jsonify({
        "service": "order",
        "status": "running"
    }), 200


@app.route("/purchase/<int:item_id>", methods=["POST"])
def purchase(item_id):
    """
    Buy one copy of a book.

    Args:
        item_id: ID of the book.

    Returns:
        200: {"message", "book_id", "title", "status"} on success.
        404: book not found.
        409: book out of stock.
        500: order could not be saved (the copy is given back).
        503: catalog is down, timed out, or gave a bad reply.
    """
    print(f"[ORDER] Purchase request for book {item_id}", flush=True)

    try:
        status, info = call_catalog("GET", f"/info/{item_id}")

        if status == 404:
            print(f"[ORDER] Book {item_id} not found", flush=True)
            return jsonify({"error": "Book not found"}), 404

        if status != 200:
            print(
                f"[ORDER] Unexpected catalog status {status} on info",
                flush=True
            )
            return jsonify({"error": "Catalog service unavailable"}), 503

        title = info["title"]

        # Stop early if there are no copies. This check is not enough
        # when two requests come at the same time, so the decrement
        # below is the real check.
        if info["quantity"] <= 0:
            print(f"[ORDER] Book {item_id} out of stock", flush=True)
            return jsonify({"error": "Out of stock"}), 409

        # The catalog uses a conditional UPDATE, so if two requests try
        # to buy the last copy, only one succeeds and the other gets 409.
        status, _ = call_catalog("POST", f"/decrement/{item_id}")

        if status == 409:
            print(
                f"[ORDER] Book {item_id} sold out before decrement",
                flush=True
            )
            return jsonify({"error": "Out of stock"}), 409

        if status == 404:
            print(f"[ORDER] Book {item_id} not found", flush=True)
            return jsonify({"error": "Book not found"}), 404

        if status != 200:
            print(
                f"[ORDER] Unexpected catalog status {status} on decrement",
                flush=True
            )
            return jsonify({"error": "Catalog service unavailable"}), 503

    except CatalogUnavailable as error:
        return jsonify({"error": str(error)}), 503

    except (KeyError, TypeError):
        # The catalog replied 200 but without the expected fields.
        print(f"[ORDER] Malformed catalog reply for book {item_id}", flush=True)
        return jsonify({"error": "Catalog service unavailable"}), 503

    try:
        order_id = record_order(item_id, title)

    except sqlite3.Error:
        app.logger.exception("Order could not be recorded")
        print(f"[ORDER] Failed to record order for book {item_id}", flush=True)

        # The copy was already taken from the catalog, but there is no
        # order for it. We give the copy back so the stock and the order
        # log stay in sync.
        restore_stock(item_id)

        return jsonify({"error": "Order could not be recorded"}), 500

    print(f"[ORDER] bought book {title} (order {order_id})", flush=True)

    return jsonify({
        "message": f"bought book {title}",
        "book_id": item_id,
        "title": title,
        "status": "success"
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5002"))
    app.run(host="0.0.0.0", port=port, threaded=True)
