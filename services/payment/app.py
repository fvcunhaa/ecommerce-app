import os
import random
import time
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

GATEWAY_MIN_MS = int(os.getenv("PAYMENT_GATEWAY_MIN_MS", "80"))
GATEWAY_MAX_MS = int(os.getenv("PAYMENT_GATEWAY_MAX_MS", "260"))
FAILURE_RATE = float(os.getenv("PAYMENT_FAILURE_RATE", "0.03"))


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "payment-service"})


@app.post("/authorize")
def authorize():
    payload = request.get_json(silent=True) or {}
    amount = float(payload.get("amount", 0))
    method = payload.get("method", "pix")
    order_id = payload.get("order_id")

    if amount <= 0:
        return jsonify({"status": "rejected", "reason": "invalid_amount"}), 400

    processing_ms = random.randint(GATEWAY_MIN_MS, GATEWAY_MAX_MS)
    time.sleep(processing_ms / 1000)

    if random.random() < FAILURE_RATE:
        app.logger.warning(
            "payment authorization rejected",
            extra={"order_id": order_id, "payment_method": method, "amount": amount},
        )
        return jsonify({
            "status": "rejected",
            "reason": "gateway_declined",
            "processing_ms": processing_ms,
        }), 402

    transaction_id = f"PAY-{uuid.uuid4().hex[:16].upper()}"
    app.logger.info(
        "payment authorized",
        extra={
            "order_id": order_id,
            "payment_method": method,
            "amount": amount,
            "transaction_id": transaction_id,
        },
    )
    return jsonify({
        "status": "approved",
        "transaction_id": transaction_id,
        "processing_ms": processing_ms,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
