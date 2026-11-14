
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from flask import Flask

# Load frontend routes without importing catalog/app.py.
ROOT = Path(__file__).resolve().parents[1]
ROUTES_FILE = ROOT / "frontend" / "catalog_routes.py"

spec = importlib.util.spec_from_file_location(
    "frontend_catalog_routes_test", ROUTES_FILE
)
catalog_routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_routes)


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(catalog_routes.catalog_blueprint)

    with app.test_client() as test_client:
        yield test_client


def mock_response(data, status=200):
    response = Mock()
    response.json.return_value = data
    response.status_code = status
    return response


def test_frontend_search(client, monkeypatch):
    books = [
        {"id": 1, "title": "Book One"},
        {"id": 2, "title": "Book Two"}
    ]

    fake_get = Mock(return_value=mock_response(books))
    monkeypatch.setattr(catalog_routes.requests, "get", fake_get)

    response = client.get("/search/distributed%20systems")

    assert response.status_code == 200
    assert response.get_json() == books
    assert fake_get.call_args.kwargs["timeout"] == 5
    assert fake_get.call_args.args[0].endswith(
        "/search/distributed%20systems"
    )


def test_frontend_search_empty(client, monkeypatch):
    monkeypatch.setattr(
        catalog_routes.requests,
        "get",
        Mock(return_value=mock_response([]))
    )

    response = client.get("/search/mathematics")

    assert response.status_code == 200
    assert response.get_json() == []


def test_frontend_info(client, monkeypatch):
    book = {
        "title": "RPCs for Noobs",
        "quantity": 5,
        "price": 50.0
    }

    monkeypatch.setattr(
        catalog_routes.requests,
        "get",
        Mock(return_value=mock_response(book))
    )

    response = client.get("/info/2")

    assert response.status_code == 200
    assert response.get_json() == book


def test_frontend_book_not_found(client, monkeypatch):
    monkeypatch.setattr(
        catalog_routes.requests,
        "get",
        Mock(return_value=mock_response(
            {"error": "Book not found"}, 404
        ))
    )

    response = client.get("/info/99")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"


def test_catalog_timeout(client, monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(catalog_routes.requests, "get", fake_get)

    response = client.get("/info/2")

    assert response.status_code == 504
    assert response.get_json()["error"] == "Catalog service timeout"


def test_catalog_unavailable(client, monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(catalog_routes.requests, "get", fake_get)

    response = client.get("/info/2")

    assert response.status_code == 503
    assert response.get_json()["error"] == "Catalog service unavailable"
