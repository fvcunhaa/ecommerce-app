import os
import random
import time
from datetime import datetime

import requests

BASE_URL = os.getenv("OBSSTORE_URL", "http://web:5000").rstrip("/")
TARGET_REVENUE_DAILY = float(os.getenv("TARGET_REVENUE_DAILY", "100000"))
VISITS_PER_MINUTE = max(float(os.getenv("VISITS_PER_MINUTE", "8")), 0.2)
PAYMENT_FAILURE_RATE = float(os.getenv("PAYMENT_FAILURE_RATE", "0.03"))
CART_RATE = float(os.getenv("CART_RATE", "0.42"))
BASE_CONVERSION_RATE = float(os.getenv("BASE_CONVERSION_RATE", "0.012"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8"))

PRODUCT_WEIGHTS = {
    "mouse-precision": 0.24,
    "keyboard-mechanical": 0.17,
    "ssd-nvme-2tb": 0.16,
    "headset-pulse-pro": 0.15,
    "monitor-ultraview-32": 0.10,
    "smartphone-nova-x": 0.08,
    "smart-tv-vision-55": 0.06,
    "notebook-pro-x15": 0.04,
}

STATES = ["SP", "RJ", "MG", "PR", "RS", "SC", "BA", "GO", "PE", "CE", "ES"]
STATE_WEIGHTS = [28, 13, 12, 9, 8, 7, 7, 5, 5, 4, 2]
PAYMENTS = ["pix", "credito", "debito"]
PAYMENT_WEIGHTS = [35, 52, 13]

# Distribuição aproximada do faturamento ao longo do dia.
DAY_CURVE = [
    (0, 0.00), (6, 0.03), (9, 0.10), (12, 0.28), (14, 0.40),
    (18, 0.62), (22, 0.93), (24, 1.00)
]


def wait_for_app():
    while True:
        try:
            response = requests.get(f"{BASE_URL}/status", timeout=REQUEST_TIMEOUT)
            if response.ok:
                print("[simulator] ObsStore disponível.")
                return
        except requests.RequestException:
            pass
        print("[simulator] aguardando ObsStore...")
        time.sleep(3)


def expected_fraction_now():
    now = datetime.now()
    hour = now.hour + now.minute / 60 + now.second / 3600
    for idx in range(1, len(DAY_CURVE)):
        h0, f0 = DAY_CURVE[idx - 1]
        h1, f1 = DAY_CURVE[idx]
        if hour <= h1:
            ratio = (hour - h0) / max(h1 - h0, 0.001)
            return f0 + (f1 - f0) * max(0, min(ratio, 1))
    return 1.0


def get_summary():
    response = requests.get(f"{BASE_URL}/api/store/summary", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_products():
    response = requests.get(f"{BASE_URL}/api/store/products", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()["products"]


def choose_basket(products, deficit):
    available = {p["id"]: p for p in products if (p.get("quantity", 0) - p.get("reserved", 0)) > 0}
    ids = [pid for pid in PRODUCT_WEIGHTS if pid in available]
    if not ids:
        return []

    weights = [PRODUCT_WEIGHTS[pid] for pid in ids]
    first = random.choices(ids, weights=weights, k=1)[0]
    basket = [{"product_id": first, "quantity": 1}]

    # Carrinhos maiores aparecem mais quando o faturamento está abaixo da curva esperada.
    add_second = random.random() < (0.18 if deficit < 3000 else 0.38)
    if add_second and len(ids) > 1:
        second = random.choices(ids, weights=weights, k=1)[0]
        if second == first:
            basket[0]["quantity"] = 2
        else:
            basket.append({"product_id": second, "quantity": 1})
    return basket


def browse():
    requests.get(f"{BASE_URL}/", timeout=REQUEST_TIMEOUT)
    requests.get(f"{BASE_URL}/produtos", timeout=REQUEST_TIMEOUT)


def cart_journey():
    requests.get(f"{BASE_URL}/carrinho/criar", timeout=REQUEST_TIMEOUT)
    requests.get(f"{BASE_URL}/carrinho/adicionar", timeout=REQUEST_TIMEOUT)
    requests.get(f"{BASE_URL}/carrinho/resumo", timeout=REQUEST_TIMEOUT)


def complete_purchase(products, deficit):
    requests.get(f"{BASE_URL}/login", timeout=REQUEST_TIMEOUT)
    requests.get(f"{BASE_URL}/checkout", timeout=REQUEST_TIMEOUT)
    requests.get(f"{BASE_URL}/endereco", timeout=REQUEST_TIMEOUT)

    payment = random.choices(PAYMENTS, weights=PAYMENT_WEIGHTS, k=1)[0]

    # Falha de pagamento proposital: gera erro técnico e abandono.
    if random.random() < PAYMENT_FAILURE_RATE:
        try:
            requests.get(f"{BASE_URL}/pagamento/boleto", timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            pass
        print("[simulator] pagamento recusado/indisponível; jornada abandonada.")
        return False

    payment_endpoint = "pix" if payment == "pix" else "cartao"
    response = requests.get(f"{BASE_URL}/pagamento/{payment_endpoint}", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    basket = choose_basket(products, deficit)
    if not basket:
        return False

    suffix = f"{int(time.time() * 1000)}-{random.randint(1000,9999)}"
    payload = {
        "customer": {
            "name": f"Cliente Virtual {suffix[-4:]}",
            "email": f"virtual-{suffix}@obsstore.lab",
            "state": random.choices(STATES, weights=STATE_WEIGHTS, k=1)[0],
        },
        "payment_method": payment,
        "source": "simulator",
        "items": basket,
    }
    checkout = requests.post(
        f"{BASE_URL}/api/store/checkout",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    checkout.raise_for_status()
    order = checkout.json()["order"]
    print(
        f"[simulator] pedido #{order['order_id']} | "
        f"{order['payment_method']} | R$ {order['total']:.2f}"
    )
    return True


def run_visit():
    browse()

    if random.random() > CART_RATE:
        return

    cart_journey()
    summary = get_summary()
    expected = TARGET_REVENUE_DAILY * expected_fraction_now()
    current = float(summary["revenue_today"])
    deficit = max(0.0, expected - current)

    # Quando estamos abaixo da curva de R$100k/dia, a chance de conversão sobe
    # progressivamente até recuperar o ritmo.
    deficit_factor = min(deficit / max(TARGET_REVENUE_DAILY * 0.08, 1), 1.0)
    conversion = min(BASE_CONVERSION_RATE + (0.55 * deficit_factor), 0.60)

    if random.random() <= conversion:
        complete_purchase(get_products(), deficit)


def main():
    wait_for_app()
    interval = 60.0 / VISITS_PER_MINUTE
    print(
        f"[simulator] alvo diário=R$ {TARGET_REVENUE_DAILY:.2f} | "
        f"visitas/min={VISITS_PER_MINUTE:.1f}"
    )
    while True:
        started = time.time()
        try:
            run_visit()
        except requests.RequestException as exc:
            print(f"[simulator] erro HTTP: {exc}")
        except Exception as exc:
            print(f"[simulator] erro inesperado: {exc}")

        elapsed = time.time() - started
        jitter = random.uniform(0.75, 1.25)
        time.sleep(max(0.2, interval * jitter - elapsed))


if __name__ == "__main__":
    main()
