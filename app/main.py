import os
import time
import psycopg2
import requests
import threading

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from random import randint, uniform, choices
from collections import defaultdict
from datetime import datetime, timedelta
from time import perf_counter
from functools import wraps
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "obsstore-lab-change-me")


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ecommerce:ecommerce123@postgres:5432/ecommerce"
)

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:5001").rstrip("/")
SHIPPING_SERVICE_URL = os.getenv("SHIPPING_SERVICE_URL", "http://shipping-service:5002").rstrip("/")
SERVICE_TIMEOUT_SECONDS = float(os.getenv("SERVICE_TIMEOUT_SECONDS", "5"))


# ============================================================
# CONFIGURAÇÕES DE NEGÓCIO
# ============================================================

ESTADOS = {
    "SP": 0.28,
    "RJ": 0.13,
    "MG": 0.12,
    "PR": 0.09,
    "RS": 0.08,
    "SC": 0.07,
    "BA": 0.07,
    "GO": 0.05,
    "PE": 0.05,
    "CE": 0.04,
    "ES": 0.02
}


PRODUTOS = {
    "Camiseta Premium": {
        "preco_min": 79.90,
        "preco_max": 129.90,
        "peso": 0.22
    },
    "Tênis Casual": {
        "preco_min": 179.90,
        "preco_max": 329.90,
        "peso": 0.16
    },
    "Mochila Executiva": {
        "preco_min": 139.90,
        "preco_max": 259.90,
        "peso": 0.13
    },
    "Relógio Digital": {
        "preco_min": 99.90,
        "preco_max": 219.90,
        "peso": 0.12
    },
    "Fone Bluetooth": {
        "preco_min": 89.90,
        "preco_max": 189.90,
        "peso": 0.11
    },
    "Calça Jeans": {
        "preco_min": 119.90,
        "preco_max": 239.90,
        "peso": 0.10
    },
    "Jaqueta Corta Vento": {
        "preco_min": 199.90,
        "preco_max": 399.90,
        "peso": 0.08
    },
    "Óculos de Sol": {
        "preco_min": 69.90,
        "preco_max": 169.90,
        "peso": 0.08
    }
}


STORE_PRODUCTS = [
    {
        "id": "notebook-pro-x15",
        "name": "Notebook Pro X15",
        "category": "Notebooks",
        "price": 6499.90,
        "old_price": 7199.90,
        "badge": "Mais vendido",
        "description": "Performance profissional, tela de alta definição e autonomia para o dia inteiro.",
        "visual": "notebook"
    },
    {
        "id": "monitor-ultraview-32",
        "name": "Monitor UltraView 32”",
        "category": "Monitores",
        "price": 2399.90,
        "old_price": 2799.90,
        "badge": "Oferta",
        "description": "Painel imersivo 4K para produtividade, criação e entretenimento.",
        "visual": "monitor"
    },
    {
        "id": "smartphone-nova-x",
        "name": "Smartphone Nova X",
        "category": "Smartphones",
        "price": 4299.90,
        "old_price": 4799.90,
        "badge": "Lançamento",
        "description": "Câmera avançada, alto desempenho e design premium em um só dispositivo.",
        "visual": "phone"
    },
    {
        "id": "headset-pulse-pro",
        "name": "Headset Pulse Pro",
        "category": "Áudio",
        "price": 899.90,
        "old_price": 1099.90,
        "badge": "Destaque",
        "description": "Áudio espacial, cancelamento de ruído e conforto para longas sessões.",
        "visual": "headset"
    },
    {
        "id": "mouse-precision",
        "name": "Mouse Precision",
        "category": "Acessórios",
        "price": 329.90,
        "old_price": 399.90,
        "badge": "20% OFF",
        "description": "Precisão, ergonomia e conectividade para sua rotina de trabalho.",
        "visual": "mouse"
    },
    {
        "id": "keyboard-mechanical",
        "name": "Keyboard Mechanical",
        "category": "Gaming",
        "price": 599.90,
        "old_price": 699.90,
        "badge": "Gaming",
        "description": "Switches mecânicos, iluminação ajustável e construção robusta.",
        "visual": "keyboard"
    },
    {
        "id": "ssd-nvme-2tb",
        "name": "SSD NVMe 2TB",
        "category": "Componentes",
        "price": 749.90,
        "old_price": 899.90,
        "badge": "Alta performance",
        "description": "Armazenamento ultrarrápido para aplicações, jogos e grandes projetos.",
        "visual": "ssd"
    },
    {
        "id": "smart-tv-vision-55",
        "name": "Smart TV Vision 55”",
        "category": "Casa",
        "price": 3499.90,
        "old_price": 3999.90,
        "badge": "Oferta",
        "description": "Imagem 4K, streaming integrado e experiência imersiva para sua casa.",
        "visual": "tv"
    }
]


FORMAS_PAGAMENTO = {
    "credito": 0.52,
    "pix": 0.35,
    "boleto": 0.00,
    "debito": 0.13
}


SIMULADOR = {
    "vendas": [],
    "carrinhos_criados": 0,
    "numero_coleta": 0,
    "ultima_atualizacao": None
}


SNAPSHOT = {
    "metricas": None,
    "endpoints": None,
    "ultima_coleta": None
}


ENDPOINTS_MONITORADOS = {
    "/status": {
        "nome": "status",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/login": {
        "nome": "login",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/produtos": {
        "nome": "lista_produtos",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/carrinho/criar": {
        "nome": "carrinho_criar",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/carrinho/adicionar": {
        "nome": "carrinho_adicionar",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/carrinho/resumo": {
        "nome": "carrinho_resumo",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/checkout": {
        "nome": "checkout",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/endereco": {
        "nome": "endereco",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/pagamento/pix": {
        "nome": "pagamento_pix",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/pagamento/boleto": {
        "nome": "pagamento_boleto",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/pagamento/cartao": {
        "nome": "pagamento_cartao",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    },
    "/sucesso": {
        "nome": "sucesso",
        "total_chamadas": 0,
        "sucessos": 0,
        "falhas": 0,
        "ultimo_status": None,
        "ultima_chamada": None,
        "tempo_total_ms": 0
    }
}


# ============================================================
# BANCO DE DADOS POSTGRESQL
# ============================================================

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def aguardar_banco(max_tentativas=30):
    for tentativa in range(1, max_tentativas + 1):
        try:
            conn = get_db_connection()
            conn.close()
            print("Banco PostgreSQL conectado com sucesso.")
            return
        except Exception as erro:
            print(f"Aguardando PostgreSQL... tentativa {tentativa}/{max_tentativas}: {erro}")
            time.sleep(2)

    raise Exception("Não foi possível conectar ao PostgreSQL.")


def inicializar_banco():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY,
                    estado VARCHAR(2) NOT NULL,
                    produto VARCHAR(100) NOT NULL,
                    forma_pagamento VARCHAR(30) NOT NULL,
                    quantidade INTEGER NOT NULL,
                    preco_unitario NUMERIC(10,2) NOT NULL,
                    subtotal NUMERIC(10,2) NOT NULL,
                    desconto_percentual NUMERIC(5,2) NOT NULL,
                    valor_desconto NUMERIC(10,2) NOT NULL,
                    frete NUMERIC(10,2) NOT NULL,
                    total NUMERIC(10,2) NOT NULL,
                    data TIMESTAMP NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS simulador_state (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    carrinhos_criados INTEGER NOT NULL DEFAULT 0,
                    numero_coleta INTEGER NOT NULL DEFAULT 0,
                    ultima_atualizacao TIMESTAMP NULL
                );
            """)

            cur.execute("""
                INSERT INTO simulador_state (
                    id,
                    carrinhos_criados,
                    numero_coleta,
                    ultima_atualizacao
                )
                VALUES (1, 0, 0, NULL)
                ON CONFLICT (id) DO NOTHING;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS store_products (
                    id VARCHAR(80) PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    category VARCHAR(80) NOT NULL,
                    price NUMERIC(12,2) NOT NULL,
                    old_price NUMERIC(12,2),
                    description TEXT,
                    badge VARCHAR(80),
                    visual VARCHAR(40),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    product_id VARCHAR(80) PRIMARY KEY REFERENCES store_products(id),
                    quantity INTEGER NOT NULL DEFAULT 0,
                    reserved INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    email VARCHAR(200) UNIQUE NOT NULL,
                    state VARCHAR(2) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id BIGSERIAL PRIMARY KEY,
                    customer_id BIGINT REFERENCES customers(id),
                    status VARCHAR(30) NOT NULL DEFAULT 'paid',
                    payment_method VARCHAR(30) NOT NULL,
                    subtotal NUMERIC(12,2) NOT NULL,
                    shipping NUMERIC(12,2) NOT NULL DEFAULT 0,
                    discount NUMERIC(12,2) NOT NULL DEFAULT 0,
                    total NUMERIC(12,2) NOT NULL,
                    source VARCHAR(30) NOT NULL DEFAULT 'store',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id BIGSERIAL PRIMARY KEY,
                    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_id VARCHAR(80) NOT NULL REFERENCES store_products(id),
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(12,2) NOT NULL,
                    total NUMERIC(12,2) NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id BIGSERIAL PRIMARY KEY,
                    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    method VARCHAR(30) NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    amount NUMERIC(12,2) NOT NULL,
                    transaction_id VARCHAR(80) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            for product in STORE_PRODUCTS:
                cur.execute("""
                    INSERT INTO store_products (
                        id, name, category, price, old_price, description, badge, visual
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        category = EXCLUDED.category,
                        price = EXCLUDED.price,
                        old_price = EXCLUDED.old_price,
                        description = EXCLUDED.description,
                        badge = EXCLUDED.badge,
                        visual = EXCLUDED.visual,
                        active = TRUE;
                """, (
                    product["id"], product["name"], product["category"], product["price"],
                    product["old_price"], product["description"], product["badge"], product["visual"]
                ))
                cur.execute("""
                    INSERT INTO inventory (product_id, quantity)
                    VALUES (%s, %s)
                    ON CONFLICT (product_id) DO NOTHING;
                """, (product["id"], 50))

            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key VARCHAR(120) PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    email VARCHAR(200) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    state VARCHAR(2) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                ALTER TABLE orders
                ADD COLUMN IF NOT EXISTS user_id BIGINT;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_addresses (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    label VARCHAR(80) NOT NULL DEFAULT 'Principal',
                    street VARCHAR(200),
                    city VARCHAR(120),
                    state VARCHAR(2) NOT NULL,
                    zip_code VARCHAR(20),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS carts (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                    session_key VARCHAR(120),
                    status VARCHAR(30) NOT NULL DEFAULT 'open',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS cart_items (
                    id BIGSERIAL PRIMARY KEY,
                    cart_id BIGINT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
                    product_id VARCHAR(80) NOT NULL REFERENCES store_products(id),
                    quantity INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(cart_id, product_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(160) UNIQUE NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id BIGSERIAL PRIMARY KEY,
                    supplier_id BIGINT NOT NULL REFERENCES suppliers(id),
                    product_id VARCHAR(80) NOT NULL REFERENCES store_products(id),
                    quantity INTEGER NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'ordered',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    in_transit_at TIMESTAMP,
                    received_at TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id BIGSERIAL PRIMARY KEY,
                    product_id VARCHAR(80) NOT NULL REFERENCES store_products(id),
                    movement_type VARCHAR(30) NOT NULL,
                    quantity INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    reference_type VARCHAR(40),
                    reference_id BIGINT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                INSERT INTO suppliers (name)
                VALUES ('Tech Distribution Brasil')
                ON CONFLICT (name) DO NOTHING;
            """)

            cur.execute("SELECT value FROM app_settings WHERE key='inventory_seed_50_v1';")
            if cur.fetchone() is None:
                cur.execute("UPDATE inventory SET quantity=50, reserved=0, updated_at=NOW();")
                cur.execute("""
                    INSERT INTO app_settings (key, value)
                    VALUES ('inventory_seed_50_v1','applied');
                """)

        conn.commit()


def salvar_venda_db(venda):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO vendas (
                    id,
                    estado,
                    produto,
                    forma_pagamento,
                    quantidade,
                    preco_unitario,
                    subtotal,
                    desconto_percentual,
                    valor_desconto,
                    frete,
                    total,
                    data
                )
                VALUES (
                    %(id)s,
                    %(estado)s,
                    %(produto)s,
                    %(forma_pagamento)s,
                    %(quantidade)s,
                    %(preco_unitario)s,
                    %(subtotal)s,
                    %(desconto_percentual)s,
                    %(valor_desconto)s,
                    %(frete)s,
                    %(total)s,
                    %(data)s
                )
                ON CONFLICT (id) DO NOTHING;
            """, venda)

        conn.commit()


def carregar_vendas_db():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    estado,
                    produto,
                    forma_pagamento,
                    quantidade,
                    preco_unitario,
                    subtotal,
                    desconto_percentual,
                    valor_desconto,
                    frete,
                    total,
                    data
                FROM vendas
                ORDER BY id;
            """)

            vendas = []

            for row in cur.fetchall():
                vendas.append({
                    "id": row["id"],
                    "estado": row["estado"],
                    "produto": row["produto"],
                    "forma_pagamento": row["forma_pagamento"],
                    "quantidade": row["quantidade"],
                    "preco_unitario": float(row["preco_unitario"]),
                    "subtotal": float(row["subtotal"]),
                    "desconto_percentual": float(row["desconto_percentual"]),
                    "valor_desconto": float(row["valor_desconto"]),
                    "frete": float(row["frete"]),
                    "total": float(row["total"]),
                    "data": row["data"].strftime("%Y-%m-%d %H:%M:%S")
                })

            return vendas


def salvar_estado_simulador():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE simulador_state
                SET
                    carrinhos_criados = %s,
                    numero_coleta = %s,
                    ultima_atualizacao = %s
                WHERE id = 1;
            """, (
                SIMULADOR["carrinhos_criados"],
                SIMULADOR["numero_coleta"],
                SIMULADOR["ultima_atualizacao"]
            ))

        conn.commit()


def carregar_estado_simulador():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    carrinhos_criados,
                    numero_coleta,
                    ultima_atualizacao
                FROM simulador_state
                WHERE id = 1;
            """)

            row = cur.fetchone()

            if not row:
                return

            SIMULADOR["carrinhos_criados"] = row["carrinhos_criados"]
            SIMULADOR["numero_coleta"] = row["numero_coleta"]

            if row["ultima_atualizacao"]:
                SIMULADOR["ultima_atualizacao"] = row["ultima_atualizacao"].strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================

def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sortear_com_peso(dicionario):
    chaves = list(dicionario.keys())

    if isinstance(list(dicionario.values())[0], dict):
        pesos = [item["peso"] for item in dicionario.values()]
    else:
        pesos = list(dicionario.values())

    return choices(chaves, weights=pesos, k=1)[0]


def invalidar_snapshot():
    SNAPSHOT["metricas"] = None
    SNAPSHOT["endpoints"] = None


def obter_store_products():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.id, p.name, p.category, p.price, p.old_price, p.description,
                       p.badge, p.visual, i.quantity, i.reserved
                FROM store_products p
                JOIN inventory i ON i.product_id = p.id
                WHERE p.active = TRUE
                ORDER BY p.name;
            """)
            rows = cur.fetchall()
    return [{
        **dict(row),
        "price": float(row["price"]),
        "old_price": float(row["old_price"]) if row["old_price"] is not None else None
    } for row in rows]


def registrar_pedido_store(customer, items, payment_method="pix", source="store", user_id=None):
    if not items:
        raise ValueError("Carrinho vazio")

    if user_id:
        with get_db_connection() as user_conn:
            with user_conn.cursor(cursor_factory=RealDictCursor) as user_cur:
                user_cur.execute("SELECT name,email,state FROM users WHERE id=%s;", (user_id,))
                logged_user = user_cur.fetchone()
        if logged_user:
            customer = {
                "name": logged_user["name"],
                "email": logged_user["email"],
                "state": logged_user["state"]
            }

    state = (customer.get("state") or "SP").upper()[:2]
    email = (customer.get("email") or f"guest-{int(time.time()*1000)}@obsstore.lab").lower()
    name = customer.get("name") or "Cliente ObsStore"

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO customers (name, email, state)
                VALUES (%s,%s,%s)
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, state = EXCLUDED.state
                RETURNING id;
            """, (name, email, state))
            customer_id = cur.fetchone()["id"]

            normalized = []
            subtotal = 0.0
            for item in items:
                product_id = item.get("product_id")
                quantity = max(1, min(int(item.get("quantity", 1)), 5))
                cur.execute("""
                    SELECT p.id, p.name, p.price, i.quantity, i.reserved
                    FROM store_products p
                    JOIN inventory i ON i.product_id = p.id
                    WHERE p.id = %s AND p.active = TRUE
                    FOR UPDATE;
                """, (product_id,))
                product = cur.fetchone()
                if not product:
                    raise ValueError(f"Produto inválido: {product_id}")
                available = product["quantity"] - product["reserved"]
                if available < quantity:
                    raise ValueError(f"Estoque insuficiente para {product['name']}")
                unit_price = float(product["price"])
                line_total = round(unit_price * quantity, 2)
                subtotal += line_total
                normalized.append((product, quantity, unit_price, line_total))

            try:
                shipping_response = requests.post(
                    f"{SHIPPING_SERVICE_URL}/quote",
                    json={"subtotal": round(subtotal, 2), "state": state},
                    timeout=SERVICE_TIMEOUT_SECONDS,
                )
                shipping_response.raise_for_status()
                shipping_data = shipping_response.json()
                shipping = float(shipping_data["shipping"])
            except (requests.RequestException, KeyError, ValueError) as error:
                app.logger.exception("shipping service unavailable")
                raise RuntimeError("Serviço de frete indisponível") from error

            discount = round(subtotal * 0.03, 2) if payment_method == "pix" else 0.0
            total = round(subtotal + shipping - discount, 2)

            try:
                payment_response = requests.post(
                    f"{PAYMENT_SERVICE_URL}/authorize",
                    json={
                        "amount": total,
                        "method": payment_method,
                        "customer_email": email,
                    },
                    timeout=SERVICE_TIMEOUT_SECONDS,
                )
                payment_data = payment_response.json()
            except (requests.RequestException, ValueError) as error:
                app.logger.exception("payment service unavailable")
                raise RuntimeError("Serviço de pagamento indisponível") from error

            if payment_response.status_code >= 400 or payment_data.get("status") != "approved":
                reason = payment_data.get("reason", "payment_rejected")
                raise ValueError(f"Pagamento não aprovado: {reason}")

            transaction_id = payment_data["transaction_id"]

            cur.execute("""
                INSERT INTO orders (
                    customer_id, user_id, status, payment_method, subtotal, shipping, discount, total, source
                )
                VALUES (%s,%s,'paid',%s,%s,%s,%s,%s,%s)
                RETURNING id, created_at;
            """, (customer_id, user_id, payment_method, subtotal, shipping, discount, total, source))
            order = cur.fetchone()

            for product, quantity, unit_price, line_total in normalized:
                cur.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, total)
                    VALUES (%s,%s,%s,%s,%s);
                """, (order["id"], product["id"], quantity, unit_price, line_total))
                cur.execute("""
                    UPDATE inventory
                    SET quantity = quantity - %s, updated_at = NOW()
                    WHERE product_id = %s
                    RETURNING quantity;
                """, (quantity, product["id"]))
                balance = cur.fetchone()["quantity"]
                cur.execute("""
                    INSERT INTO inventory_movements
                    (product_id,movement_type,quantity,balance_after,reference_type,reference_id)
                    VALUES(%s,'SALE',%s,%s,'order',%s);
                """,(product["id"],-quantity,balance,order["id"]))
                if balance == 0:
                    ensure_purchase_order(cur, product["id"])

            cur.execute("""
                INSERT INTO payments (order_id, method, status, amount, transaction_id)
                VALUES (%s,%s,'approved',%s,%s);
            """, (order["id"], payment_method, total, transaction_id))

        conn.commit()

    main_product = normalized[0][0]["name"]
    legacy = {
        "id": 1000000 + int(order["id"]),
        "estado": state,
        "produto": main_product,
        "forma_pagamento": payment_method,
        "quantidade": sum(line[1] for line in normalized),
        "preco_unitario": normalized[0][2],
        "subtotal": round(subtotal, 2),
        "desconto_percentual": round((discount / subtotal) if subtotal else 0, 4),
        "valor_desconto": discount,
        "frete": shipping,
        "total": total,
        "data": order["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    }
    salvar_venda_db(legacy)
    SIMULADOR["vendas"].append(legacy)
    SIMULADOR["carrinhos_criados"] += 1
    SIMULADOR["ultima_atualizacao"] = agora()
    salvar_estado_simulador()
    invalidar_snapshot()

    return {
        "order_id": int(order["id"]),
        "transaction_id": transaction_id,
        "status": "paid",
        "total": total,
        "subtotal": round(subtotal, 2),
        "shipping": shipping,
        "discount": discount,
        "payment_method": payment_method,
        "customer": {"name": name, "email": email, "state": state}
    }


def obter_resumo_store():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(total),0) AS revenue_today,
                    COUNT(*) AS orders_today,
                    COALESCE(AVG(total),0) AS average_ticket
                FROM orders
                WHERE created_at >= CURRENT_DATE;
            """)
            today = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS customers FROM customers;")
            customers = cur.fetchone()["customers"]
            cur.execute("SELECT COALESCE(SUM(quantity),0) AS stock FROM inventory;")
            stock = cur.fetchone()["stock"]
    return {
        "revenue_today": float(today["revenue_today"]),
        "orders_today": int(today["orders_today"]),
        "average_ticket": round(float(today["average_ticket"]), 2),
        "customers": int(customers),
        "stock_units": int(stock)
    }


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, email, state, created_at FROM users WHERE id=%s;", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_or_create_cart():
    if "cart_session" not in session:
        session["cart_session"] = f"cart-{int(time.time()*1000)}-{randint(1000,9999)}"
    user_id = session.get("user_id")
    session_key = session["cart_session"]
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                cur.execute("SELECT id FROM carts WHERE user_id=%s AND status='open' ORDER BY id DESC LIMIT 1;", (user_id,))
            else:
                cur.execute("SELECT id FROM carts WHERE session_key=%s AND status='open' ORDER BY id DESC LIMIT 1;", (session_key,))
            row = cur.fetchone()
            if row:
                return int(row["id"])
            cur.execute(
                "INSERT INTO carts (user_id, session_key) VALUES (%s,%s) RETURNING id;",
                (user_id, session_key)
            )
            cart_id = int(cur.fetchone()["id"])
        conn.commit()
    return cart_id


def cart_payload():
    cart_id = get_or_create_cart()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT ci.product_id, ci.quantity, p.name, p.price,
                       i.quantity AS stock
                FROM cart_items ci
                JOIN store_products p ON p.id=ci.product_id
                JOIN inventory i ON i.product_id=ci.product_id
                WHERE ci.cart_id=%s
                ORDER BY ci.id;
            """, (cart_id,))
            rows = cur.fetchall()
    items = []
    total = 0.0
    for row in rows:
        price = float(row["price"])
        line_total = round(price * row["quantity"], 2)
        total += line_total
        items.append({
            "product_id": row["product_id"],
            "name": row["name"],
            "price": price,
            "quantity": row["quantity"],
            "stock": row["stock"],
            "line_total": line_total
        })
    return {"cart_id": cart_id, "items": items, "subtotal": round(total, 2)}


def ensure_purchase_order(cur, product_id):
    cur.execute("""
        SELECT id FROM purchase_orders
        WHERE product_id=%s AND status IN ('ordered','in_transit')
        LIMIT 1;
    """, (product_id,))
    if cur.fetchone():
        return
    cur.execute("SELECT id FROM suppliers WHERE active=TRUE ORDER BY id LIMIT 1;")
    supplier = cur.fetchone()
    if not supplier:
        return
    cur.execute("""
        INSERT INTO purchase_orders (supplier_id, product_id, quantity, status)
        VALUES (%s,%s,50,'ordered');
    """, (supplier[0], product_id))


def process_restock_cycle():
    while True:
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        UPDATE purchase_orders
                        SET status='in_transit', in_transit_at=NOW()
                        WHERE status='ordered' AND created_at <= NOW() - INTERVAL '30 seconds'
                        RETURNING id;
                    """)
                    cur.execute("""
                        SELECT id, product_id, quantity
                        FROM purchase_orders
                        WHERE status='in_transit'
                          AND in_transit_at <= NOW() - INTERVAL '60 seconds'
                        FOR UPDATE;
                    """)
                    orders = cur.fetchall()
                    for po in orders:
                        cur.execute("""
                            UPDATE inventory
                            SET quantity=quantity+%s, updated_at=NOW()
                            WHERE product_id=%s
                            RETURNING quantity;
                        """, (po["quantity"], po["product_id"]))
                        balance = cur.fetchone()["quantity"]
                        cur.execute("""
                            INSERT INTO inventory_movements
                            (product_id, movement_type, quantity, balance_after, reference_type, reference_id)
                            VALUES (%s,'RESTOCK',%s,%s,'purchase_order',%s);
                        """, (po["product_id"], po["quantity"], balance, po["id"]))
                        cur.execute("""
                            UPDATE purchase_orders
                            SET status='received', received_at=NOW()
                            WHERE id=%s;
                        """, (po["id"],))
                conn.commit()
        except Exception:
            app.logger.exception("restock cycle failed")
        time.sleep(10)


def business_dashboard():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT COALESCE(SUM(total),0) revenue, COUNT(*) orders,
                       COALESCE(AVG(total),0) avg_ticket
                FROM orders WHERE created_at >= CURRENT_DATE;
            """)
            summary = cur.fetchone()
            cur.execute("""
                SELECT c.state, COALESCE(SUM(o.total),0) revenue, COUNT(*) orders
                FROM orders o JOIN customers c ON c.id=o.customer_id
                GROUP BY c.state ORDER BY revenue DESC;
            """)
            states = [dict(x) for x in cur.fetchall()]
            cur.execute("""
                SELECT p.id, p.name, COALESCE(SUM(oi.quantity),0) units,
                       COALESCE(SUM(oi.total),0) revenue
                FROM store_products p
                LEFT JOIN order_items oi ON oi.product_id=p.id
                GROUP BY p.id,p.name ORDER BY units DESC, p.name;
            """)
            products = [dict(x) for x in cur.fetchall()]
            cur.execute("""
                SELECT p.id,p.name,p.category,i.quantity,
                       CASE WHEN i.quantity=0 THEN 'out_of_stock'
                            WHEN i.quantity<=10 THEN 'critical' ELSE 'ok' END status
                FROM inventory i JOIN store_products p ON p.id=i.product_id
                ORDER BY i.quantity ASC,p.name;
            """)
            stock = [dict(x) for x in cur.fetchall()]
            cur.execute("""
                SELECT po.id,p.name product,po.quantity,po.status,
                       po.created_at,po.in_transit_at,po.received_at
                FROM purchase_orders po JOIN store_products p ON p.id=po.product_id
                ORDER BY po.id DESC LIMIT 20;
            """)
            replenishment = [dict(x) for x in cur.fetchall()]
            cur.execute("""
                SELECT source, COUNT(*) orders, COALESCE(SUM(total),0) revenue
                FROM orders GROUP BY source ORDER BY revenue DESC;
            """)
            sources = [dict(x) for x in cur.fetchall()]
    return {
        "summary": {
            "revenue": float(summary["revenue"]),
            "orders": summary["orders"],
            "average_ticket": round(float(summary["avg_ticket"]),2),
            "target": 100000
        },
        "states": [{"state":x["state"],"revenue":float(x["revenue"]),"orders":x["orders"]} for x in states],
        "products": [{"id":x["id"],"name":x["name"],"units":x["units"],"revenue":float(x["revenue"])} for x in products],
        "stock": stock,
        "replenishment": replenishment,
        "sources": [{"source":x["source"],"orders":x["orders"],"revenue":float(x["revenue"])} for x in sources]
    }


# ============================================================
# MONITORAMENTO DOS ENDPOINTS
# ============================================================

def registrar_endpoint(caminho, status_http, sucesso, inicio):
    if caminho not in ENDPOINTS_MONITORADOS:
        return

    duracao_ms = round((perf_counter() - inicio) * 1000, 2)

    endpoint = ENDPOINTS_MONITORADOS[caminho]

    endpoint["total_chamadas"] += 1
    endpoint["ultimo_status"] = status_http
    endpoint["ultima_chamada"] = agora()
    endpoint["tempo_total_ms"] += duracao_ms

    if sucesso:
        endpoint["sucessos"] += 1
    else:
        endpoint["falhas"] += 1


def monitorar_endpoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        caminho = request.path
        inicio = perf_counter()

        try:
            resposta = func(*args, **kwargs)

            status_http = 200

            if isinstance(resposta, tuple):
                status_http = resposta[1]

            sucesso = 1 if status_http < 400 else 0

            registrar_endpoint(
                caminho=caminho,
                status_http=status_http,
                sucesso=sucesso,
                inicio=inicio
            )

            return resposta

        except Exception:
            registrar_endpoint(
                caminho=caminho,
                status_http=500,
                sucesso=0,
                inicio=inicio
            )
            raise

    return wrapper


def montar_metricas_endpoint(caminho):
    if caminho not in ENDPOINTS_MONITORADOS:
        return None

    item = ENDPOINTS_MONITORADOS[caminho]

    total = item["total_chamadas"]
    sucessos = item["sucessos"]
    falhas = item["falhas"]

    taxa_sucesso = round(
        sucessos / total * 100,
        2
    ) if total else 0

    taxa_erro = round(
        falhas / total * 100,
        2
    ) if total else 0

    latencia_media_ms = round(
        item["tempo_total_ms"] / total,
        2
    ) if total else 0

    response_code = item["ultimo_status"]

    if response_code is None:
        status_operacional = None
    elif response_code < 400:
        status_operacional = 1
    else:
        status_operacional = 0

    return {
        "endpoint": caminho,
        "nome": item["nome"],
        "status": status_operacional,
        "response_code": response_code,
        "ultimo_status": response_code,
        "latencia_media_ms": latencia_media_ms,
        "total_chamadas": total,
        "sucessos": sucessos,
        "falhas": falhas,
        "taxa_sucesso": taxa_sucesso,
        "taxa_erro": taxa_erro,
        "ultima_chamada": item["ultima_chamada"]
    }


def calcular_metricas_endpoint():
    dados = []

    for caminho in ENDPOINTS_MONITORADOS.keys():
        dados.append(montar_metricas_endpoint(caminho))

    return dados


# ============================================================
# GERAÇÃO DE VENDAS
# ============================================================

def gerar_venda(id_venda):
    estado = sortear_com_peso(ESTADOS)
    produto = sortear_com_peso(PRODUTOS)
    forma_pagamento = sortear_com_peso(FORMAS_PAGAMENTO)

    preco_min = PRODUTOS[produto]["preco_min"]
    preco_max = PRODUTOS[produto]["preco_max"]

    preco_unitario = round(uniform(preco_min, preco_max), 2)

    quantidade = choices(
        [1, 2, 3],
        weights=[0.74, 0.21, 0.05],
        k=1
    )[0]

    subtotal = round(preco_unitario * quantidade, 2)

    desconto_percentual = choices(
        [0, 0.05, 0.10, 0.15],
        weights=[0.62, 0.22, 0.12, 0.04],
        k=1
    )[0]

    valor_desconto = round(subtotal * desconto_percentual, 2)
    frete = round(uniform(0, 29.90), 2)

    total = round(subtotal - valor_desconto + frete, 2)

    return {
        "id": id_venda,
        "estado": estado,
        "produto": produto,
        "forma_pagamento": forma_pagamento,
        "quantidade": quantidade,
        "preco_unitario": preco_unitario,
        "subtotal": subtotal,
        "desconto_percentual": desconto_percentual,
        "valor_desconto": valor_desconto,
        "frete": frete,
        "total": total,
        "data": agora()
    }


def iniciar_base(qtd_inicial=200):
    vendas_db = carregar_vendas_db()

    if vendas_db:
        SIMULADOR["vendas"] = vendas_db
        carregar_estado_simulador()
        return

    for i in range(qtd_inicial):
        venda = gerar_venda(i + 1)

        dias_atras = randint(1, 30)
        segundos_aleatorios = randint(0, 86400)

        data_historica = datetime.now() - timedelta(
            days=dias_atras,
            seconds=segundos_aleatorios
        )

        venda["data"] = data_historica.strftime("%Y-%m-%d %H:%M:%S")

        SIMULADOR["vendas"].append(venda)
        salvar_venda_db(venda)

    total_pedidos = len(SIMULADOR["vendas"])

    taxa_abandono_inicial = 0.35

    SIMULADOR["carrinhos_criados"] = round(
        total_pedidos / (1 - taxa_abandono_inicial)
    )

    SIMULADOR["ultima_atualizacao"] = agora()

    salvar_estado_simulador()


def adicionar_novas_vendas():
    SIMULADOR["numero_coleta"] += 1
    SIMULADOR["ultima_atualizacao"] = agora()

    total_atual = len(SIMULADOR["vendas"])

    novas_vendas = round(total_atual * uniform(0.01, 0.04))
    novas_vendas = max(1, novas_vendas)
    novas_vendas = min(novas_vendas, 10)

    proximo_id = total_atual + 1

    for i in range(novas_vendas):
        venda = gerar_venda(proximo_id + i)
        SIMULADOR["vendas"].append(venda)
        salvar_venda_db(venda)

    taxa_conversao = uniform(0.63, 0.67)
    novos_carrinhos = round(novas_vendas / taxa_conversao)

    SIMULADOR["carrinhos_criados"] += novos_carrinhos

    salvar_estado_simulador()

    return novas_vendas


# ============================================================
# CÁLCULO DAS MÉTRICAS DE NEGÓCIO
# ============================================================

def calcular_metricas():
    vendas = SIMULADOR["vendas"]

    total_pedidos = len(vendas)
    vendas_total_ecommerce = round(sum(venda["total"] for venda in vendas), 2)

    ticket_medio = round(
        vendas_total_ecommerce / total_pedidos,
        2
    ) if total_pedidos else 0

    vendas_por_estado = defaultdict(float)
    pedidos_por_estado = defaultdict(int)
    quantidade_produtos_por_estado = defaultdict(lambda: defaultdict(int))

    vendas_por_pagamento = defaultdict(float)
    pedidos_por_pagamento = defaultdict(int)

    total_frete = 0
    total_descontos = 0

    for venda in vendas:
        estado = venda["estado"]
        produto = venda["produto"]
        pagamento = venda["forma_pagamento"]

        vendas_por_estado[estado] += venda["total"]
        pedidos_por_estado[estado] += 1
        quantidade_produtos_por_estado[estado][produto] += venda["quantidade"]

        vendas_por_pagamento[pagamento] += venda["total"]
        pedidos_por_pagamento[pagamento] += 1

        total_frete += venda["frete"]
        total_descontos += venda["valor_desconto"]

    estados = []

    for estado in ESTADOS.keys():
        total_estado = round(vendas_por_estado[estado], 2)
        pedidos_estado = pedidos_por_estado[estado]

        ticket_estado = round(
            total_estado / pedidos_estado,
            2
        ) if pedidos_estado else 0

        produtos_estado = quantidade_produtos_por_estado[estado]

        if produtos_estado:
            produto_mais = max(
                produtos_estado.items(),
                key=lambda item: item[1]
            )

            produto_menos = min(
                produtos_estado.items(),
                key=lambda item: item[1]
            )
        else:
            produto_mais = ("Nenhum", 0)
            produto_menos = ("Nenhum", 0)

        estados.append({
            "estado": estado,
            "total_vendas": total_estado,
            "total_pedidos": pedidos_estado,
            "ticket_medio": ticket_estado,
            "produto_mais_vendido": {
                "produto": produto_mais[0],
                "quantidade": produto_mais[1]
            },
            "produto_menos_vendido": {
                "produto": produto_menos[0],
                "quantidade": produto_menos[1]
            }
        })

    pagamentos = []

    for pagamento in FORMAS_PAGAMENTO.keys():
        pedidos_pagamento = pedidos_por_pagamento[pagamento]
        total_pagamento = round(vendas_por_pagamento[pagamento], 2)

        percentual_pedidos = round(
            pedidos_pagamento / total_pedidos * 100,
            2
        ) if total_pedidos else 0

        percentual_valor = round(
            total_pagamento / vendas_total_ecommerce * 100,
            2
        ) if vendas_total_ecommerce else 0

        pagamentos.append({
            "forma_pagamento": pagamento,
            "total_vendas": total_pagamento,
            "total_pedidos": pedidos_pagamento,
            "percentual_pedidos": percentual_pedidos,
            "percentual_valor": percentual_valor
        })

    carrinhos_criados = SIMULADOR["carrinhos_criados"]
    carrinhos_abandonados = carrinhos_criados - total_pedidos

    taxa_abandono = round(
        carrinhos_abandonados / carrinhos_criados * 100,
        2
    ) if carrinhos_criados else 0

    validacao = {
        "soma_pagamentos_valor": round(
            sum(item["total_vendas"] for item in pagamentos),
            2
        ),
        "soma_pagamentos_pedidos": sum(
            item["total_pedidos"] for item in pagamentos
        ),
        "soma_estados_valor": round(
            sum(item["total_vendas"] for item in estados),
            2
        ),
        "soma_estados_pedidos": sum(
            item["total_pedidos"] for item in estados
        ),
        "vendas_total_ecommerce": vendas_total_ecommerce,
        "total_pedidos": total_pedidos
    }

    return {
        "coleta": {
            "numero": SIMULADOR["numero_coleta"],
            "ultima_atualizacao": SIMULADOR["ultima_atualizacao"],
            "tipo": "snapshot_consistente"
        },
        "resumo": {
            "vendas_total_ecommerce": vendas_total_ecommerce,
            "total_pedidos": total_pedidos,
            "ticket_medio_ecommerce": ticket_medio,
            "carrinhos_criados": carrinhos_criados,
            "carrinhos_abandonados": carrinhos_abandonados,
            "taxa_abandono_carrinho": taxa_abandono,
            "total_frete": round(total_frete, 2),
            "total_descontos": round(total_descontos, 2)
        },
        "estados": estados,
        "pagamentos": pagamentos,
        "validacao": validacao
    }


# ============================================================
# SNAPSHOT
# ============================================================

def atualizar_snapshot():
    SNAPSHOT["metricas"] = calcular_metricas()
    SNAPSHOT["endpoints"] = calcular_metricas_endpoint()
    SNAPSHOT["ultima_coleta"] = agora()


def obter_snapshot_metricas():
    if SNAPSHOT["metricas"] is None:
        atualizar_snapshot()

    return SNAPSHOT["metricas"]


def obter_snapshot_endpoints():
    if SNAPSHOT["endpoints"] is None:
        atualizar_snapshot()

    return SNAPSHOT["endpoints"]


def obter_endpoint_do_snapshot(caminho):
    endpoints = obter_snapshot_endpoints()

    for item in endpoints:
        if item["endpoint"] == caminho:
            return item

    return None


# ============================================================
# ROTAS WEB
# ============================================================

@app.route("/")
def index():
    return render_template("home.html", products=obter_store_products(), current_user=get_current_user())


@app.route("/admin")
def admin():
    return render_template("business.html")


@app.route("/admin/legacy")
def admin_legacy():
    return render_template("index.html")


@app.route("/api/store/products")
def api_store_products():
    return jsonify({"products": obter_store_products()})


@app.route("/api/store/summary")
def api_store_summary():
    return jsonify(obter_resumo_store())


@app.route("/api/catalog/search")
def api_catalog_search():
    q=(request.args.get("q") or "").strip().lower()
    category=(request.args.get("category") or "").strip()
    products=obter_store_products()
    filtered=[]
    for product in products:
        if q and q not in product["name"].lower() and q not in product["description"].lower() and q not in product["category"].lower():
            continue
        if category and category!="Todos" and product["category"]!=category:
            continue
        filtered.append(product)
    return jsonify({"products": filtered, "count": len(filtered)})


@app.route("/produto/<product_id>")
def product_detail(product_id):
    products=obter_store_products()
    product=next((p for p in products if p["id"]==product_id),None)
    if not product:
        return "Produto não encontrado",404
    return render_template("product.html", product=product, current_user=get_current_user())


@app.route("/api/cart")
def api_cart_get():
    return jsonify(cart_payload())


@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    payload=request.get_json(silent=True) or {}
    product_id=payload.get("product_id")
    quantity=max(1,min(int(payload.get("quantity",1)),5))
    cart_id=get_or_create_cart()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT quantity FROM inventory WHERE product_id=%s;",(product_id,))
            inv=cur.fetchone()
            if not inv:
                return jsonify({"status":0,"message":"Produto inválido"}),404
            if inv["quantity"]<=0:
                return jsonify({"status":0,"message":"Produto sem estoque"}),409
            cur.execute("""
                INSERT INTO cart_items(cart_id,product_id,quantity)
                VALUES(%s,%s,%s)
                ON CONFLICT(cart_id,product_id)
                DO UPDATE SET quantity=LEAST(cart_items.quantity+EXCLUDED.quantity,5);
            """,(cart_id,product_id,quantity))
            cur.execute("UPDATE carts SET updated_at=NOW() WHERE id=%s;",(cart_id,))
        conn.commit()
    return jsonify(cart_payload())


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    payload=request.get_json(silent=True) or {}
    cart_id=get_or_create_cart()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cart_items WHERE cart_id=%s AND product_id=%s;",(cart_id,payload.get("product_id")))
        conn.commit()
    return jsonify(cart_payload())


@app.route("/api/cart/clear", methods=["POST"])
def api_cart_clear():
    cart_id=get_or_create_cart()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cart_items WHERE cart_id=%s;",(cart_id,))
        conn.commit()
    return jsonify(cart_payload())


@app.route("/api/business/dashboard")
def api_business_dashboard():
    return jsonify(business_dashboard())


@app.route("/api/store/checkout", methods=["POST"])
def api_store_checkout():
    payload = request.get_json(silent=True) or {}
    source = payload.get("source") or "store"
    user_id = session.get("user_id")

    if source == "store" and not user_id:
        return jsonify({
            "status": 0,
            "message": "Faça login para finalizar a compra.",
            "login_url": url_for("login")
        }), 401

    try:
        order = registrar_pedido_store(
            customer=payload.get("customer") or {},
            items=payload.get("items") or [],
            payment_method=payload.get("payment_method") or "pix",
            source=source,
            user_id=user_id
        )
        return jsonify({"status": 1, "order": order}), 201
    except ValueError as error:
        return jsonify({"status": 0, "message": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"status": 0, "message": str(error)}), 503
    except Exception as error:
        app.logger.exception("Falha ao processar checkout")
        return jsonify({"status": 0, "message": "Falha interna no checkout"}), 500


# ============================================================
# ÚNICA ROTA QUE ALTERA TUDO
# Configure essa rota no Zabbix a cada 5 minutos.
# ============================================================

@app.route("/api/coleta")
def api_coleta():
    # Compatibilidade com integrações existentes: esta rota apenas atualiza
    # o snapshot. Nenhuma venda, latência ou erro é fabricado pela coleta.
    SIMULADOR["numero_coleta"] += 1
    SIMULADOR["ultima_atualizacao"] = agora()
    salvar_estado_simulador()
    atualizar_snapshot()

    metricas = obter_snapshot_metricas()

    return jsonify({
        "status": 1,
        "mensagem": "Snapshot atualizado com dados reais da aplicação",
        "ultima_coleta": SNAPSHOT["ultima_coleta"],
        "coleta": metricas["coleta"],
        "resumo": metricas["resumo"],
        "validacao": metricas["validacao"]
    })


# ============================================================
# ROTAS DE CONSULTA DO DASHBOARD
# Não alteram nada.
# ============================================================

@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(obter_snapshot_metricas())


@app.route("/api/vendas/ultimas")
def api_vendas_ultimas():
    ultimas = SIMULADOR["vendas"][-20:]

    return jsonify({
        "total": len(ultimas),
        "vendas": ultimas,
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


# ============================================================
# MÉTRICAS DE NEGÓCIO
# Não alteram nada.
# ============================================================

@app.route("/api/metrica/vendas-total")
def metrica_vendas_total():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "vendas_total_ecommerce",
        "valor": metricas["resumo"]["vendas_total_ecommerce"],
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/total-pedidos")
def metrica_total_pedidos():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "total_pedidos",
        "valor": metricas["resumo"]["total_pedidos"],
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/ticket-medio")
def metrica_ticket_medio():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "ticket_medio_ecommerce",
        "valor": metricas["resumo"]["ticket_medio_ecommerce"],
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/carrinhos-criados")
def metrica_carrinhos_criados():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "carrinhos_criados",
        "valor": metricas["resumo"]["carrinhos_criados"],
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/carrinhos-abandonados")
def metrica_carrinhos_abandonados():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "carrinhos_abandonados",
        "valor": metricas["resumo"]["carrinhos_abandonados"],
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/abandono-carrinho")
def metrica_abandono_carrinho():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "taxa_abandono_carrinho",
        "valor": metricas["resumo"]["taxa_abandono_carrinho"],
        "carrinhos_criados": metricas["resumo"]["carrinhos_criados"],
        "carrinhos_abandonados": metricas["resumo"]["carrinhos_abandonados"],
        "total_pedidos": metricas["resumo"]["total_pedidos"],
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/pagamentos")
def metrica_pagamentos():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "pagamentos",
        "dados": metricas["pagamentos"],
        "validacao": {
            "soma_pagamentos_valor": metricas["validacao"]["soma_pagamentos_valor"],
            "soma_pagamentos_pedidos": metricas["validacao"]["soma_pagamentos_pedidos"],
            "vendas_total_ecommerce": metricas["validacao"]["vendas_total_ecommerce"],
            "total_pedidos": metricas["validacao"]["total_pedidos"]
        },
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/vendas-por-estado")
def metrica_vendas_por_estado():
    metricas = obter_snapshot_metricas()

    return jsonify({
        "metrica": "vendas_por_estado",
        "dados": metricas["estados"],
        "validacao": {
            "soma_estados_valor": metricas["validacao"]["soma_estados_valor"],
            "soma_estados_pedidos": metricas["validacao"]["soma_estados_pedidos"],
            "vendas_total_ecommerce": metricas["validacao"]["vendas_total_ecommerce"],
            "total_pedidos": metricas["validacao"]["total_pedidos"]
        },
        "coleta": metricas["coleta"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


# ============================================================
# MÉTRICAS DOS ENDPOINTS
# Não alteram nada.
# Leem o último snapshot atualizado por /api/coleta.
# ============================================================

@app.route("/api/metrica/endpoints")
def metrica_endpoints():
    return jsonify({
        "metrica": "endpoints",
        "dados": obter_snapshot_endpoints(),
        "coleta": {
            "numero": SIMULADOR["numero_coleta"],
            "ultima_atualizacao": SIMULADOR["ultima_atualizacao"]
        },
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/endpoints/<path:endpoint_path>/status")
def metrica_endpoint_status(endpoint_path):
    caminho = "/" + endpoint_path

    metricas = obter_endpoint_do_snapshot(caminho)

    if metricas is None:
        return jsonify({
            "status": 0,
            "mensagem": "Endpoint não monitorado",
            "endpoint": caminho,
            "endpoints_monitorados": list(ENDPOINTS_MONITORADOS.keys())
        }), 404

    return jsonify(metricas)


@app.route("/api/metrica/endpoints/<path:endpoint_path>/response-code")
def metrica_endpoint_response_code(endpoint_path):
    caminho = "/" + endpoint_path

    metricas = obter_endpoint_do_snapshot(caminho)

    if metricas is None:
        return jsonify({
            "status": 0,
            "mensagem": "Endpoint não monitorado",
            "endpoint": caminho
        }), 404

    return jsonify({
        "endpoint": caminho,
        "response_code": metricas["response_code"],
        "status": metricas["status"],
        "ultima_chamada": metricas["ultima_chamada"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


@app.route("/api/metrica/endpoints/<path:endpoint_path>/latencia")
def metrica_endpoint_latencia(endpoint_path):
    caminho = "/" + endpoint_path

    metricas = obter_endpoint_do_snapshot(caminho)

    if metricas is None:
        return jsonify({
            "status": 0,
            "mensagem": "Endpoint não monitorado",
            "endpoint": caminho
        }), 404

    return jsonify({
        "endpoint": caminho,
        "latencia_media_ms": metricas["latencia_media_ms"],
        "total_chamadas": metricas["total_chamadas"],
        "ultima_chamada": metricas["ultima_chamada"],
        "ultima_coleta": SNAPSHOT["ultima_coleta"]
    })


# ============================================================
# ROTAS DA APLICAÇÃO ECOMMERCE
# Mantidas para testes reais.
# ============================================================

@app.route("/status")
@monitorar_endpoint
def status():
    return jsonify({
        "status": 1,
        "mensagem": "API online"
    })


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", current_user=get_current_user())
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id,name,email,state,password_hash FROM users WHERE email=%s;", (email,))
            user = cur.fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="E-mail ou senha inválidos."), 401
    session["user_id"] = int(user["id"])
    return redirect(url_for("account"))


@app.route("/cadastro", methods=["GET","POST"])
def cadastro():
    if request.method == "GET":
        return render_template("register.html")
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    state = (request.form.get("state") or "SP").upper()[:2]
    if not name or not email or len(password) < 6:
        return render_template("register.html", error="Preencha os campos e use uma senha com pelo menos 6 caracteres."), 400
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users(name,email,password_hash,state)
                    VALUES(%s,%s,%s,%s) RETURNING id;
                """,(name,email,generate_password_hash(password),state))
                user_id=cur.fetchone()[0]
            conn.commit()
    except psycopg2.IntegrityError:
        return render_template("register.html", error="Já existe uma conta com este e-mail."), 409
    session["user_id"]=int(user_id)
    return redirect(url_for("account"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/minha-conta")
def account():
    user=get_current_user()
    if not user:
        return redirect(url_for("login"))
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Migra pedidos antigos do mesmo e-mail para a conta autenticada.
            cur.execute("""
                UPDATE orders
                SET user_id=%s
                WHERE user_id IS NULL
                  AND customer_id IN (
                    SELECT id FROM customers WHERE LOWER(email)=LOWER(%s)
                  );
            """, (user["id"], user["email"]))
            cur.execute("""
                SELECT id,status,payment_method,total,source,created_at
                FROM orders
                WHERE user_id=%s
                   OR customer_id IN (
                       SELECT id FROM customers WHERE LOWER(email)=LOWER(%s)
                   )
                ORDER BY id DESC LIMIT 30;
            """,(user["id"], user["email"]))
            orders=[dict(x) for x in cur.fetchall()]
        conn.commit()
    return render_template("account.html", user=user, orders=orders)


@app.route("/produtos")
@monitorar_endpoint
def produtos():
    return jsonify({
        "status": 1,
        "mensagem": "Lista de produtos carregada com sucesso",
        "produtos": [
            {
                "nome": nome,
                "preco_min": dados["preco_min"],
                "preco_max": dados["preco_max"]
            }
            for nome, dados in PRODUTOS.items()
        ]
    })


@app.route("/carrinho/criar")
@monitorar_endpoint
def carrinho_criar():
    SIMULADOR["carrinhos_criados"] += 1
    SIMULADOR["ultima_atualizacao"] = agora()

    salvar_estado_simulador()
    invalidar_snapshot()

    return jsonify({
        "status": 1,
        "mensagem": "Carrinho criado com sucesso",
        "carrinhos_criados": SIMULADOR["carrinhos_criados"]
    })


@app.route("/carrinho/adicionar")
@monitorar_endpoint
def carrinho_adicionar():
    return jsonify({
        "status": 1,
        "mensagem": "Produto adicionado ao carrinho"
    })


@app.route("/carrinho/resumo")
@monitorar_endpoint
def carrinho_resumo():
    return jsonify({
        "status": 1,
        "mensagem": "Resumo do carrinho consultado"
    })


@app.route("/checkout")
@monitorar_endpoint
def checkout():
    return jsonify({
        "status": 1,
        "mensagem": "Checkout iniciado com sucesso"
    })


@app.route("/endereco")
@monitorar_endpoint
def endereco():
    return jsonify({
        "status": 1,
        "mensagem": "Endereço validado"
    })


@app.route("/pagamento/pix")
@monitorar_endpoint
def pagamento_pix():
    return jsonify({
        "status": 1,
        "mensagem": "Pagamento via Pix aprovado"
    })


@app.route("/pagamento/boleto")
@monitorar_endpoint
def pagamento_boleto():
    return jsonify({
        "status": 0,
        "mensagem": "Falha proposital simulada no boleto"
    }), 500


@app.route("/pagamento/cartao")
@monitorar_endpoint
def pagamento_cartao():
    return jsonify({
        "status": 1,
        "mensagem": "Pagamento no cartão aprovado"
    })


@app.route("/sucesso")
@monitorar_endpoint
def sucesso():
    nova_venda = gerar_venda(len(SIMULADOR["vendas"]) + 1)
    SIMULADOR["vendas"].append(nova_venda)

    salvar_venda_db(nova_venda)

    taxa_conversao = uniform(0.63, 0.67)
    novos_carrinhos = round(1 / taxa_conversao)

    SIMULADOR["carrinhos_criados"] += novos_carrinhos
    SIMULADOR["ultima_atualizacao"] = agora()

    salvar_estado_simulador()
    invalidar_snapshot()

    return jsonify({
        "status": 1,
        "mensagem": "Venda realizada com sucesso",
        "venda": nova_venda
    })


# ============================================================
# INICIALIZAÇÃO
# ============================================================

aguardar_banco()
inicializar_banco()
iniciar_base(qtd_inicial=200)
atualizar_snapshot()
threading.Thread(target=process_restock_cycle, daemon=True).start()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
