
import os
from flask import Flask, jsonify
from db import init_db

app = Flask(__name__)

init_db()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({ "service": "order", "status": "running" }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5002"))
    app.run(host="0.0.0.0", port=port, threaded=True)
