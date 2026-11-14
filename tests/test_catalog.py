
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

# Allow importing the Catalog Service from the project root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "catalog"))

import app as catalog_app
import db as catalog_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a fresh temporary database for every test.
    test_db = tmp_path / "catalog_test.db"

    monkeypatch.setattr(catalog_db, "DB_PATH", test_db)
    monkeypatch.setattr(catalog_app, "DB_PATH", test_db)

    catalog_db.init_db()

    catalog_app.app.config["TESTING"] = True

    with catalog_app.app.test_client() as test_client:
        yield test_client


def test_search_books(client):
    response = client.get("/search/distributed%20systems")

    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_search_no_results(client):
    response = client.get("/search/mathematics")

    assert response.status_code == 200
    assert response.get_json() == []


def test_info_existing_book(client):
    response = client.get("/info/2")

    assert response.status_code == 200
    assert response.get_json()["title"] == "RPCs for Noobs"
    assert response.get_json()["quantity"] == 5


def test_info_missing_book(client):
    response = client.get("/info/99")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"


def test_update_quantity(client):
    response = client.put(
        "/update/2",
        json={"quantity_delta": 3}
    )

    assert response.status_code == 200
    assert response.get_json()["quantity"] == 8


def test_update_price(client):
    response = client.put(
        "/update/2",
        json={"price": 60}
    )

    assert response.status_code == 200
    assert response.get_json()["price"] == 60


def test_prevent_negative_stock(client):
    response = client.put(
        "/update/2",
        json={"quantity_delta": -100}
    )

    assert response.status_code == 409
    assert client.get("/info/2").get_json()["quantity"] == 5


def test_decrement_stock(client):
    response = client.post("/decrement/2")

    assert response.status_code == 200
    assert response.get_json()["quantity"] == 4


def test_decrement_missing_book(client):
    response = client.post("/decrement/99")

    assert response.status_code == 404


def test_decrement_out_of_stock(client):
    client.put("/update/2", json={"quantity_delta": -5})

    response = client.post("/decrement/2")

    assert response.status_code == 409
    assert client.get("/info/2").get_json()["quantity"] == 0


def test_concurrent_decrement(client):
    # Set book 2 stock to exactly one copy.
    response = client.put(
        "/update/2",
        json={"quantity_delta": -4}
    )
    assert response.status_code == 200

    # Send 10 concurrent decrement requests.
    def buy_one(_):
        with catalog_app.app.test_client() as thread_client:
            response = thread_client.post("/decrement/2")
            return response.status_code

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(buy_one, range(10)))

    # Only one request must succeed.
    assert results.count(200) == 1
    assert results.count(409) == 9

    # Quantity must never become negative.
    assert client.get("/info/2").get_json()["quantity"] == 0
