"""
Frontend routes for purchases.

Forwards POST /purchase/<id> to the Order Service and returns its
JSON reply and HTTP status to the client.
"""

import os
import requests

from flask import Blueprint, jsonify

order_blueprint = Blueprint("order", __name__)

ORDER_URL = os.getenv(
    "ORDER_URL",
    "http://localhost:5002"
)

# The order service calls the catalog up to three times with a 5 second
# timeout each, so we wait longer than that before giving up on it.
ORDER_TIMEOUT = 15


def forward_order_request(endpoint):
    """
    Forward a POST request to the Order Service.

    Args:
        endpoint: Order path, e.g. "/purchase/2".

    Returns:
        tuple: (JSON response, HTTP status). The status is the one sent
        by the order service, or 504 on timeout, or 503 if the order
        service cannot be reached or does not reply with JSON.
    """
    try:
        response = requests.post(
            f"{ORDER_URL}{endpoint}",
            timeout=ORDER_TIMEOUT
        )

        print(
            f"[FRONTEND] Order service replied {response.status_code}",
            flush=True
        )

        return jsonify(response.json()), response.status_code

    except requests.Timeout:
        print("[FRONTEND] Order request timed out", flush=True)
        return jsonify({
            "error": "Order service timeout"
        }), 504

    except (requests.RequestException, ValueError):
        print("[FRONTEND] Order service unavailable", flush=True)
        return jsonify({
            "error": "Order service unavailable"
        }), 503


@order_blueprint.route("/purchase/<int:item_id>", methods=["POST"])
def purchase_book(item_id):
    """
    Buy one copy of a book through the Order Service.

    Args:
        item_id: ID of the book.

    Returns:
        200: {"message", "book_id", "title", "status"} on success.
        404: book not found.
        409: book out of stock.
        500: order could not be saved.
        503: order or catalog service unavailable.
        504: order service timed out.
    """
    print(f"[FRONTEND] Purchase request for book {item_id}", flush=True)

    return forward_order_request(f"/purchase/{item_id}")
