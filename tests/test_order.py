"""
Tests for the Order Service purchase endpoint.

The order service talks to a real catalog app with its own temporary
database. Instead of real HTTP, catalog calls are sent to the catalog's
Flask test client, so the tests do not need any server running.
"""

import importlib.util
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]

# Both services read their DB path when imported, so point them to a
# temp folder first. Otherwise importing them creates files in the repo.
IMPORT_DIR = tempfile.mkdtemp()


def load_service(name, env_var):
    """
    Load a service's db.py and app.py under unique module names.

    catalog/ and order/ both have modules called "app" and "db", so a
    normal import would mix them up with the ones test_catalog.py loads.

    Args:
        name: Service folder name, "catalog" or "order".
        env_var: Environment variable that holds the service's DB path.

    Returns:
        tuple: (app module, db module).
    """
    folder = ROOT / name
    old_env = os.environ.get(env_var)
    old_db = sys.modules.get("db")

    os.environ[env_var] = str(Path(IMPORT_DIR) / f"{name}.db")

    try:
        db_spec = importlib.util.spec_from_file_location(
            f"{name}_db_test", folder / "db.py"
        )
        db_module = importlib.util.module_from_spec(db_spec)
        db_spec.loader.exec_module(db_module)

        # app.py does "from db import ...", so it must find this service's db.
        sys.modules["db"] = db_module

        app_spec = importlib.util.spec_from_file_location(
            f"{name}_app_test", folder / "app.py"
        )
        app_module = importlib.util.module_from_spec(app_spec)
        app_spec.loader.exec_module(app_module)

    finally:
        if old_db is None:
            sys.modules.pop("db", None)
        else:
            sys.modules["db"] = old_db

        if old_env is None:
            os.environ.pop(env_var, None)
        else:
            os.environ[env_var] = old_env

    return app_module, db_module


catalog_app, catalog_db = load_service("catalog", "CATALOG_DB_PATH")
order_app, order_db = load_service("order", "ORDER_DB_PATH")


@pytest.fixture
def catalog_client(tmp_path, monkeypatch):
    """
    Catalog test client with a fresh database (5 copies of each book).

    Args:
        tmp_path: pytest temp folder.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        FlaskClient for the catalog app.
    """
    test_db = tmp_path / "catalog_test.db"

    monkeypatch.setattr(catalog_db, "DB_PATH", test_db)
    monkeypatch.setattr(catalog_app, "DB_PATH", test_db)
    catalog_db.init_db()

    catalog_app.app.config["TESTING"] = True

    # No "with" block here: the catalog request runs inside the order
    # request, and two open "with" clients break Flask's context stack.
    return catalog_app.app.test_client()


@pytest.fixture
def order_db_path(tmp_path, monkeypatch):
    """
    Give the order service a fresh, empty orders database.

    Args:
        tmp_path: pytest temp folder.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Path to the orders database.
    """
    test_db = tmp_path / "orders_test.db"

    monkeypatch.setattr(order_db, "DB_PATH", test_db)
    monkeypatch.setattr(order_app, "DB_PATH", test_db)
    order_db.init_db()

    return test_db


@pytest.fixture
def client(catalog_client, order_db_path, monkeypatch):
    """
    Order test client whose catalog calls go to the catalog test client.

    Args:
        catalog_client: Catalog test client.
        order_db_path: Path to the orders database.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        FlaskClient for the order app.
    """
    def fake_request(method, url, json=None, timeout=None):
        endpoint = url[len(order_app.CATALOG_URL):]
        reply = catalog_client.open(endpoint, method=method, json=json)

        response = Mock()
        response.status_code = reply.status_code
        response.json.return_value = reply.get_json()
        return response

    monkeypatch.setattr(order_app.requests, "request", fake_request)

    order_app.app.config["TESTING"] = True

    return order_app.app.test_client()


def count_orders(db_path):
    """
    Count the rows in the orders table.

    Args:
        db_path: Path to the orders database.

    Returns:
        int: Number of saved orders.
    """
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]


def test_purchase_success(client, catalog_client, order_db_path):
    """A purchase returns the contract JSON, takes one copy and saves the order."""

    response = client.post("/purchase/2")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "bought book RPCs for Noobs",
        "book_id": 2,
        "title": "RPCs for Noobs",
        "status": "success"
    }

    assert catalog_client.get("/info/2").get_json()["quantity"] == 4
    assert count_orders(order_db_path) == 1


def test_purchase_unknown_book(client, order_db_path):
    """Buying a book that does not exist returns 404."""

    response = client.post("/purchase/99")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"
    assert count_orders(order_db_path) == 0


def test_purchase_out_of_stock(client, catalog_client, order_db_path):
    """Buying a book with no copies left returns 409."""

    catalog_client.put("/update/2", json={"quantity_delta": -5})

    response = client.post("/purchase/2")

    assert response.status_code == 409
    assert response.get_json()["error"] == "Out of stock"
    assert catalog_client.get("/info/2").get_json()["quantity"] == 0
    assert count_orders(order_db_path) == 0


def test_purchase_catalog_down(client, order_db_path, monkeypatch):
    """If the catalog cannot be reached, the purchase returns 503."""

    fake_request = Mock(side_effect=requests.ConnectionError("refused"))
    monkeypatch.setattr(order_app.requests, "request", fake_request)

    response = client.post("/purchase/2")

    assert response.status_code == 503
    assert response.get_json()["error"] == "Catalog service unavailable"
    assert count_orders(order_db_path) == 0


def test_purchase_catalog_timeout(client, order_db_path, monkeypatch):
    """If the catalog times out, the purchase returns 503."""

    fake_request = Mock(side_effect=requests.Timeout("too slow"))
    monkeypatch.setattr(order_app.requests, "request", fake_request)

    response = client.post("/purchase/2")

    assert response.status_code == 503
    assert response.get_json()["error"] == "Catalog service timeout"
    assert count_orders(order_db_path) == 0


def test_stock_restored_when_order_not_saved(
    client, catalog_client, order_db_path, monkeypatch
):
    """If the order cannot be saved, the copy goes back to the catalog."""

    def broken_record_order(item_id, title):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(order_app, "record_order", broken_record_order)

    response = client.post("/purchase/2")

    assert response.status_code == 500
    # The copy was decremented and then given back.
    assert catalog_client.get("/info/2").get_json()["quantity"] == 5
    assert count_orders(order_db_path) == 0
