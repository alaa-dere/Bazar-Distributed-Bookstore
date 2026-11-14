import os
import math
import sqlite3

from flask import Flask, jsonify, request
from db import init_db, DB_PATH

app = Flask(__name__)

# Initialize database when the service starts.
init_db()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "catalog",
        "status": "running"
    }), 200


@app.route("/search/<topic>", methods=["GET"])
def search_books(topic):
    # Find all books that match the requested topic.
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, title FROM books WHERE LOWER(topic) = LOWER(?)",
            (topic,)
        ).fetchall()

    books = [
        {"id": row[0], "title": row[1]}
        for row in rows
    ]

    print(f"[CATALOG] Search topic: {topic} | Results: {len(books)}", flush=True)

    return jsonify(books), 200


@app.route("/info/<int:item_id>", methods=["GET"])
def book_info(item_id):
    # Retrieve book details from the catalog database.
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT title, quantity, price FROM books WHERE id = ?",
            (item_id,)
        ).fetchone()

    # Return 404 if the requested book does not exist.
    if row is None:
        print(f"[CATALOG] Book {item_id} not found", flush=True)
        return jsonify({"error": "Book not found"}), 404

    book = {
        "title": row[0],
        "quantity": row[1],
        "price": row[2]
    }

    print(f"[CATALOG] Info requested for book {item_id}", flush=True)

    return jsonify(book), 200


@app.route("/update/<int:item_id>", methods=["PUT"])
def update_book(item_id):
    data = request.get_json(silent=True)

    # Check that the request contains valid JSON fields.
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    allowed_fields = {"price", "quantity_delta"}

    if set(data) - allowed_fields:
        return jsonify({"error": "Unsupported update field"}), 400

    # Validate the new price.
    if "price" in data:
        price = data["price"]

        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price < 0
        ):
            return jsonify({"error": "Invalid price"}), 400

    # Validate the quantity change.
    if "quantity_delta" in data:
        delta = data["quantity_delta"]

        if isinstance(delta, bool) or not isinstance(delta, int):
            return jsonify({"error": "Invalid quantity_delta"}), 400

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        try:
            # Lock the database for a safe read-modify-write.
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                "SELECT price, quantity FROM books WHERE id = ?",
                (item_id,)
            ).fetchone()

            if row is None:
                conn.rollback()
                return jsonify({"error": "Book not found"}), 404

            current_price, current_quantity = row

            new_price = data.get("price", current_price)
            new_quantity = (
                current_quantity + data.get("quantity_delta", 0)
            )

            if new_quantity < 0:
                conn.rollback()
                return jsonify({"error": "Insufficient stock"}), 409

            conn.execute(
                """
                UPDATE books
                SET price = ?, quantity = ?
                WHERE id = ?
                """,
                (new_price, new_quantity, item_id)
            )

            conn.commit()

        except sqlite3.Error:
            conn.rollback()
            app.logger.exception("Catalog database update failed")
            return jsonify({"error": "Database operation failed"}), 500

    print(
        f"[CATALOG] Updated book {item_id} | "
        f"Price: {new_price} | Quantity: {new_quantity}",
        flush=True
    )

    return jsonify({
        "id": item_id,
        "price": new_price,
        "quantity": new_quantity
    }), 200



@app.route("/decrement/<int:item_id>", methods=["POST"])
def decrement_stock(item_id):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # Lock before checking and updating stock.
            conn.execute("BEGIN IMMEDIATE")

            # Decrement only if at least one copy is available.
            cursor = conn.execute(
                """
                UPDATE books
                SET quantity = quantity - 1
                WHERE id = ? AND quantity > 0
                """,
                (item_id,)
            )

            if cursor.rowcount == 0:
                # Distinguish missing books from out-of-stock books.
                exists = conn.execute(
                    "SELECT 1 FROM books WHERE id = ?",
                    (item_id,)
                ).fetchone()

                conn.rollback()

                if exists is None:
                    print(
                        f"[CATALOG] Book {item_id} not found",
                        flush=True
                    )
                    return jsonify({"error": "Book not found"}), 404

                print(
                    f"[CATALOG] Book {item_id} out of stock",
                    flush=True
                )
                return jsonify({"error": "Insufficient stock"}), 409

            # Read the remaining quantity.
            row = conn.execute(
                "SELECT quantity FROM books WHERE id = ?",
                (item_id,)
            ).fetchone()

            remaining_quantity = row[0]
            conn.commit()

    except sqlite3.Error:
        app.logger.exception("Stock decrement failed")
        return jsonify({"error": "Database operation failed"}), 500

    print(
        f"[CATALOG] Stock decremented for book {item_id} | "
        f"Remaining: {remaining_quantity}",
        flush=True
    )

    return jsonify({
        "id": item_id,
        "quantity": remaining_quantity
    }), 200




if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, threaded=True)