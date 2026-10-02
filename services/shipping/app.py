import os
import random
import time

from flask import Flask, jsonify, request
from opentelemetry import trace, metrics

app = Flask(__name__)

MIN_MS = int(os.getenv("SHIPPING_MIN_MS", "40"))
MAX_MS = int(os.getenv("SHIPPING_MAX_MS", "140"))

tracer = trace.get_tracer("obsstore.shipping")
meter = metrics.get_meter("obsstore.shipping")
shipping_quotes = meter.create_counter("obsstore.shipping.quotes", description="Shipping quote requests")
shipping_duration = meter.create_histogram("obsstore.shipping.duration", unit="ms", description="Shipping quote processing time")


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

    shipping_quotes.add(1, {"customer.state": state})
    processing_ms = random.randint(MIN_MS, MAX_MS)
    with tracer.start_as_current_span("shipping.calculate") as span:
        span.set_attribute("customer.state", state)
        span.set_attribute("cart.subtotal", subtotal)
        span.set_attribute("shipping.processing_ms", processing_ms)
        time.sleep(processing_ms / 1000)
        shipping_duration.record(processing_ms, {"customer.state": state})

    if subtotal >= 299:
        shipping = 0.0
    elif state in {"SP", "RJ", "MG", "ES"}:
        shipping = 19.90
    else:
        shipping = 29.90

    eta_days = random.randint(2, 8)
    trace.get_current_span().set_attribute("shipping.amount", shipping)
    trace.get_current_span().set_attribute("shipping.eta_days", eta_days)
    app.logger.info("shipping_quote state=%s shipping=%s eta_days=%s", state, shipping, eta_days)

    return jsonify({"status": "ok", "state": state, "shipping": shipping, "eta_days": eta_days})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
