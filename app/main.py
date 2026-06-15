import os
import time
import psycopg2

from flask import Flask, jsonify, render_template, request
from random import randint, uniform, choices
from collections import defaultdict
from datetime import datetime, timedelta
from time import perf_counter
from functools import wraps
from psycopg2.extras import RealDictCursor


app = Flask(__name__)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ecommerce:ecommerce123@postgres:5432/ecommerce"
)


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


def atualizar_endpoints_por_coleta():
    simulacao = {
        "/status": {
            "response_code": 200,
            "latencia_ms": uniform(40, 90)
        },
        "/login": {
            "response_code": 200,
            "latencia_ms": uniform(90, 220)
        },
        "/produtos": {
            "response_code": 200,
            "latencia_ms": uniform(120, 280)
        },
        "/carrinho/criar": {
            "response_code": 200,
            "latencia_ms": uniform(100, 260)
        },
        "/carrinho/adicionar": {
            "response_code": 200,
            "latencia_ms": uniform(90, 240)
        },
        "/carrinho/resumo": {
            "response_code": 200,
            "latencia_ms": uniform(100, 260)
        },
        "/checkout": {
            "response_code": 200,
            "latencia_ms": uniform(180, 420)
        },
        "/endereco": {
            "response_code": 200,
            "latencia_ms": uniform(120, 300)
        },
        "/pagamento/pix": {
            "response_code": 200,
            "latencia_ms": uniform(180, 450)
        },
        "/pagamento/boleto": {
            "response_code": 500,
            "latencia_ms": uniform(7000, 12000)
        },
        "/pagamento/cartao": {
            "response_code": 200,
            "latencia_ms": uniform(250, 650)
        },
        "/sucesso": {
            "response_code": 200,
            "latencia_ms": uniform(100, 250)
        }
    }

    for caminho, dados in simulacao.items():
        response_code = dados["response_code"]
        latencia_simulada_ms = dados["latencia_ms"]

        endpoint = ENDPOINTS_MONITORADOS[caminho]

        endpoint["total_chamadas"] += 1
        endpoint["ultimo_status"] = response_code
        endpoint["ultima_chamada"] = agora()
        endpoint["tempo_total_ms"] += latencia_simulada_ms

        if response_code < 400:
            endpoint["sucessos"] += 1
        else:
            endpoint["falhas"] += 1


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
    return render_template("index.html")


# ============================================================
# ÚNICA ROTA QUE ALTERA TUDO
# Configure essa rota no Zabbix a cada 5 minutos.
# ============================================================

@app.route("/api/coleta")
def api_coleta():
    novas_vendas = adicionar_novas_vendas()

    atualizar_endpoints_por_coleta()
    atualizar_snapshot()

    metricas = obter_snapshot_metricas()

    return jsonify({
        "status": 1,
        "mensagem": "Coleta executada com sucesso",
        "novas_vendas": novas_vendas,
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


@app.route("/login")
@monitorar_endpoint
def login():
    return jsonify({
        "status": 1,
        "mensagem": "Login realizado com sucesso"
    })


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
atualizar_endpoints_por_coleta()
atualizar_snapshot()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
