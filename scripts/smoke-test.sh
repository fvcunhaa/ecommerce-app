#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"

echo "== ObsStore smoke test =="

echo "[1/4] Health"
curl -fsS "${BASE_URL}/status" >/dev/null

echo "[2/4] Products"
curl -fsS "${BASE_URL}/api/store/products" | grep -q '"products"'

echo "[3/4] Summary"
curl -fsS "${BASE_URL}/api/store/summary" | grep -q '"revenue_today"'

echo "[4/4] Checkout"
EMAIL="smoke-$(date +%s)@obsstore.lab"
curl -fsS -X POST "${BASE_URL}/api/store/checkout"   -H 'Content-Type: application/json'   -d "{
    \"customer\": {\"name\": \"Smoke Test\", \"email\": \"${EMAIL}\", \"state\": \"ES\"},
    \"payment_method\": \"pix\",
    \"source\": \"smoke-test\",
    \"items\": [{\"product_id\": \"mouse-precision\", \"quantity\": 1}]
  }" | grep -q '"status":1'

echo "ObsStore OK."
