import os
import random
import time
import uuid

from flask import Flask, jsonify, request
from opentelemetry import trace, metrics

app = Flask(__name__)

GATEWAY_MIN_MS = int(os.getenv("PAYMENT_GATEWAY_MIN_MS", "80"))
GATEWAY_MAX_MS = int(os.getenv("PAYMENT_GATEWAY_MAX_MS", "260"))
FAILURE_RATE = float(os.getenv("PAYMENT_FAILURE_RATE", "0.03"))

tracer = trace.get_tracer("obsstore.payment")
meter = metrics.get_meter("obsstore.payment")
payment_attempts = meter.create_counter("obsstore.payment.attempts", description="Payment authorization attempts")
payment_duration = meter.create_histogram("obsstore.payment.duration", unit="ms", description="Payment authorization processing time")


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

    payment_attempts.add(1, {"payment.method": method})
    with tracer.start_as_current_span("payment.gateway") as span:
        span.set_attribute("payment.method", method)
        span.set_attribute("payment.amount", amount)
        processing_ms = random.randint(GATEWAY_MIN_MS, GATEWAY_MAX_MS)
        time.sleep(processing_ms / 1000)
        span.set_attribute("payment.processing_ms", processing_ms)
        payment_duration.record(processing_ms, {"payment.method": method})

    if random.random() < FAILURE_RATE:
        trace.get_current_span().set_attribute("payment.result", "rejected")
        app.logger.warning("payment_authorization_rejected order_id=%s method=%s amount=%s", order_id, method, amount)
        return jsonify({"status": "rejected", "reason": "gateway_declined", "processing_ms": processing_ms}), 402

    transaction_id = f"PAY-{uuid.uuid4().hex[:16].upper()}"
    trace.get_current_span().set_attribute("payment.result", "approved")
    trace.get_current_span().set_attribute("payment.transaction_id", transaction_id)
    app.logger.info("payment_authorized transaction_id=%s method=%s amount=%s", transaction_id, method, amount)
    return jsonify({"status": "approved", "transaction_id": transaction_id, "processing_ms": processing_ms})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
