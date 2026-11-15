
import os
from flask import Flask, jsonify

from catalog_routes import catalog_blueprint
from order_routes import order_blueprint

app = Flask(__name__)

# Register Catalog-related frontend routes.
app.register_blueprint(catalog_blueprint)
app.register_blueprint(order_blueprint)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "frontend",
        "status": "running"
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
