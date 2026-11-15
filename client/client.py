"""
Command line client for Bazar.com.

Runs on the host and sends search, info and purchase requests to the
Frontend Service, then prints the results in a readable format.

Usage:
    python client/client.py search "distributed systems"
    python client/client.py info 2
    python client/client.py purchase 2
"""

import argparse
import os
import sys
from urllib.parse import quote

import requests

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5000")

# Purchases can take a few catalog calls, so give the frontend
# enough time to answer.
TIMEOUT = 20

LINE = "-" * 60


def send_request(method, endpoint):
    """
    Send a request to the frontend and log it.

    Args:
        method: HTTP method, "GET" or "POST".
        endpoint: Frontend path, e.g. "/info/2".

    Returns:
        tuple: (status code, JSON body), or (None, None) if the frontend
        cannot be reached or does not reply with JSON.
    """
    url = f"{FRONTEND_URL}{endpoint}"
    print(f"[CLIENT] {method} {url}", flush=True)

    try:
        response = requests.request(method, url, timeout=TIMEOUT)
        body = response.json()

    except requests.Timeout:
        print("[CLIENT] Request timed out", flush=True)
        return None, None

    except (requests.RequestException, ValueError) as error:
        print(f"[CLIENT] Frontend unavailable: {error}", flush=True)
        return None, None

    print(f"[CLIENT] Response status: {response.status_code}", flush=True)
    return response.status_code, body


def print_error(status, body):
    """
    Print an error reply from the frontend.

    Args:
        status: HTTP status code.
        body: JSON body of the reply.
    """
    message = body.get("error", body) if isinstance(body, dict) else body
    print(f"Error ({status}): {message}")


def search(topic):
    """
    Search for books by topic and print the matches.

    Args:
        topic: Topic name, e.g. "distributed systems".

    Returns:
        int: 0 on success, 1 on error.
    """
    status, body = send_request("GET", f"/search/{quote(topic, safe='')}")

    if status is None:
        return 1

    print(LINE)
    print(f"Search results for '{topic}'")
    print(LINE)

    if status != 200:
        print_error(status, body)
        print(LINE)
        return 1

    if not body:
        print("No books found.")
    else:
        print(f"{'ID':<5}Title")
        for book in body:
            print(f"{book['id']:<5}{book['title']}")

    print(LINE)
    return 0


def info(item_id):
    """
    Get the details of one book and print them.

    Args:
        item_id: ID of the book.

    Returns:
        int: 0 on success, 1 on error.
    """
    status, body = send_request("GET", f"/info/{item_id}")

    if status is None:
        return 1

    print(LINE)
    print(f"Book {item_id}")
    print(LINE)

    if status != 200:
        print_error(status, body)
        print(LINE)
        return 1

    print(f"Title    : {body['title']}")
    print(f"Price    : ${body['price']:.2f}")
    print(f"In stock : {body['quantity']}")
    print(LINE)
    return 0


def purchase(item_id):
    """
    Buy one copy of a book and print the result.

    Args:
        item_id: ID of the book.

    Returns:
        int: 0 on success, 1 on error.
    """
    status, body = send_request("POST", f"/purchase/{item_id}")

    if status is None:
        return 1

    print(LINE)
    print(f"Purchase book {item_id}")
    print(LINE)

    if status != 200:
        print_error(status, body)
        print(LINE)
        return 1

    print(body["message"])
    print(LINE)
    return 0


def main():
    """
    Read the command line and run the chosen command.

    Returns:
        int: Exit code, 0 on success and 1 on error.
    """
    parser = argparse.ArgumentParser(description="Bazar.com client")
    commands = parser.add_subparsers(dest="command", required=True)

    search_parser = commands.add_parser("search", help="search by topic")
    search_parser.add_argument("topic")

    info_parser = commands.add_parser("info", help="show book details")
    info_parser.add_argument("item_id", type=int)

    purchase_parser = commands.add_parser("purchase", help="buy a book")
    purchase_parser.add_argument("item_id", type=int)

    args = parser.parse_args()

    if args.command == "search":
        return search(args.topic)
    if args.command == "info":
        return info(args.item_id)
    return purchase(args.item_id)


if __name__ == "__main__":
    sys.exit(main())
