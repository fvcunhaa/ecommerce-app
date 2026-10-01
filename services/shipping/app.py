import os
import random
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

MIN_MS = int(os.getenv("SHIPPING_MIN_MS", "40"))
MAX_MS = int(os.getenv("SHIPPING_MAX_MS", "140"))


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "shipping-service"})


@app.post("/quote")
def quote():
    payload = request.get_json(silent=True) or {}
    subtotal = float(payload.get("subtotal", 0))
    state = (payload.get("state") or "SP").upper()

    if subtotal < 0:
        return jsonify({"status": "error", "reason": "invalid_subtotal"}), 400

    time.sleep(random.randint(MIN_MS, MAX_MS) / 1000)

    if subtotal >= 299:
        shipping = 0.0
    elif state in {"SP", "RJ", "MG", "ES"}:
        shipping = 19.90
    else:
        shipping = 29.90

    return jsonify({
        "status": "ok",
        "state": state,
        "shipping": shipping,
        "eta_days": random.randint(2, 8),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
