
import os
import requests

from flask import Blueprint, jsonify

# Routes related to book search and information.
catalog_blueprint = Blueprint("catalog", __name__)

# Docker service URL (configurable for local testing).
CATALOG_URL = os.getenv(
    "CATALOG_URL",
    "http://localhost:5001"
)


def forward_catalog_request(endpoint):
    """Forward a GET request to the Catalog Service."""
    try:
        response = requests.get(
            f"{CATALOG_URL}{endpoint}",
            timeout=5
        )

        # Forward the JSON response and HTTP status.
        return jsonify(response.json()), response.status_code

    except requests.Timeout:
        print("[FRONTEND] Catalog request timed out", flush=True)
        return jsonify({
            "error": "Catalog service timeout"
        }), 504

    except (requests.RequestException, ValueError):
        print("[FRONTEND] Catalog service unavailable", flush=True)
        return jsonify({
            "error": "Catalog service unavailable"
        }), 503


@catalog_blueprint.route("/search/<topic>", methods=["GET"])
def search_books(topic):
    print(f"[FRONTEND] Searching for topic: {topic}", flush=True)

    # Requests handles URL encoding for the topic.
    from urllib.parse import quote
    return forward_catalog_request(
        f"/search/{quote(topic, safe='')}"
    )


@catalog_blueprint.route("/info/<int:item_id>", methods=["GET"])
def book_info(item_id):
    print(f"[FRONTEND] Requesting book info: {item_id}", flush=True)

    return forward_catalog_request(f"/info/{item_id}")
