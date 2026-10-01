# ObsStore — Realistic Ecommerce Observability Lab

**ObsStore** é um e-commerce funcional criado para demonstrações, testes e ensino de observabilidade.

A proposta do projeto é ir além de um gerador artificial de métricas: a aplicação possui catálogo, estoque, clientes, carrinho, checkout, pedidos, pagamentos, PostgreSQL e um simulador autônomo de comportamento de usuários. A evolução planejada inclui instrumentação completa com OpenTelemetry e visualização no Zabbix 8 APM.

> Objetivo do laboratório: permitir que uma falha técnica possa ser relacionada ao impacto no negócio — por exemplo, latência no pagamento → falha no checkout → queda de conversão → perda de faturamento.

---

## Visão geral

```text
Visitantes reais / simulados
           |
           v
+-----------------------------+
|          ObsStore           |
|  Home / Catálogo / Carrinho |
|  Checkout / Pagamentos      |
+-------------+---------------+
              |
              v
+-----------------------------+
|          Flask API          |
| negócio + métricas + lab    |
+-------------+---------------+
              |
              v
+-----------------------------+
|       PostgreSQL 16         |
| produtos / estoque          |
| clientes / pedidos          |
| pagamentos / vendas         |
+-----------------------------+

ecommerce_simulator
       |
       +--> navega pela própria aplicação via HTTP
       +--> cria carrinhos
       +--> abandona jornadas
       +--> realiza pagamentos
       +--> gera pedidos reais no banco
```

---

## Meta de negócio do laboratório

Por padrão o simulador trabalha com uma referência de:

```text
Faturamento alvo diário: R$ 100.000
Visitantes virtuais:     ~11.520/dia
Carrinhos:               comportamento probabilístico
Pagamentos:              PIX / crédito / débito
Falhas de pagamento:     configuráveis
```

O simulador acompanha uma curva diária de faturamento. Quando a receita fica abaixo da trajetória necessária para chegar ao alvo, a probabilidade de conversão cresce gradualmente.

Isso evita simplesmente inserir R$ 100 mil no banco e cria uma operação que se comporta como um sistema vivo.

---

## Jornada simulada

Um visitante virtual pode executar uma jornada como:

```text
GET /
  |
GET /produtos
  |
POST/GET carrinho
  |
login
  |
checkout
  |
validação de endereço
  |
pagamento
  |
POST /api/store/checkout
  |
pedido persistido
```

Outros visitantes apenas navegam ou abandonam o carrinho. Uma parcela dos pagamentos falha propositalmente.

Essa abordagem é importante para APM porque cada compra gera uma sequência real de requisições que poderá produzir logs, métricas e traces.

---

## Funcionalidades atuais

### Loja

- Home responsiva
- busca de produtos
- filtros por categoria
- catálogo de produtos
- favoritos visuais
- carrinho lateral
- checkout funcional
- PIX, crédito e débito
- desconto para PIX
- controle de estoque
- confirmação de pedido

### Persistência

O PostgreSQL mantém:

```text
store_products
inventory
customers
orders
order_items
payments
vendas
simulador_state
```

As tabelas `vendas` e `simulador_state` permanecem por compatibilidade com o dashboard técnico original.

### Operação

```text
/        Loja ObsStore
/admin   Dashboard de negócio e operação
/status  Health/status da API
```

---

## Stack

- Python 3.12
- Flask
- PostgreSQL 16
- Docker
- Docker Compose
- Kubernetes
- GitHub Actions

Próxima camada:

- OpenTelemetry
- logs correlacionados
- métricas de aplicação
- distributed tracing
- Zabbix 8 APM
- ClickHouse

---

## Como executar

Clone o repositório:

```bash
git clone https://github.com/fvcunhaa/ecommerce-app.git
cd ecommerce-app
```

Para testar a versão ObsStore em desenvolvimento:

```bash
git checkout feature/obsstore-v2
```

Crie o arquivo de ambiente:

```bash
cp .env.example .env
```

Suba:

```bash
docker compose up -d --build
```

Valide:

```bash
docker compose ps
```

A loja ficará disponível em:

```text
http://localhost/
```

Dashboard:

```text
http://localhost/admin
```

---

## Containers

```text
ecommerce_app
ecommerce_postgres
ecommerce_simulator
```

Logs do simulador:

```bash
docker logs -f ecommerce_simulator
```

Exemplo:

```text
[simulator] ObsStore disponível.
[simulator] alvo diário=R$ 100000.00 | visitas/min=8.0
[simulator] pedido #18 | pix | R$ 727.40
[simulator] pedido #19 | credito | R$ 899.90
[simulator] pagamento recusado/indisponível; jornada abandonada.
```

---

## Configuração do simulador

No `.env`:

```env
TARGET_REVENUE_DAILY=100000
VISITS_PER_MINUTE=8
PAYMENT_FAILURE_RATE=0.03
CART_RATE=0.42
BASE_CONVERSION_RATE=0.012
```

### TARGET_REVENUE_DAILY

Referência de receita que o simulador tenta acompanhar durante o dia.

### VISITS_PER_MINUTE

Quantidade média de novas jornadas por minuto.

```text
8/min
≈ 480/h
≈ 11.520/dia
```

### PAYMENT_FAILURE_RATE

Probabilidade de uma jornada chegar a uma falha proposital de pagamento.

### CART_RATE

Probabilidade de um visitante iniciar uma jornada de carrinho.

### BASE_CONVERSION_RATE

Conversão mínima. A taxa efetiva é ajustada automaticamente quando a operação está abaixo da curva de receita esperada.

---

## APIs da ObsStore

### Produtos

```http
GET /api/store/products
```

### Resumo diário

```http
GET /api/store/summary
```

Exemplo:

```json
{
  "revenue_today": 68421.90,
  "orders_today": 84,
  "average_ticket": 814.54,
  "customers": 426,
  "stock_units": 1187
}
```

### Checkout

```http
POST /api/store/checkout
Content-Type: application/json
```

Exemplo:

```json
{
  "customer": {
    "name": "Cliente Demo",
    "email": "cliente@obsstore.lab",
    "state": "ES"
  },
  "payment_method": "pix",
  "source": "store",
  "items": [
    {
      "product_id": "ssd-nvme-2tb",
      "quantity": 1
    }
  ]
}
```

---

## Métricas já existentes

O projeto preserva os endpoints originais de negócio:

```text
/api/metrica/vendas-total
/api/metrica/total-pedidos
/api/metrica/ticket-medio
/api/metrica/carrinhos-criados
/api/metrica/carrinhos-abandonados
/api/metrica/abandono-carrinho
/api/metrica/pagamentos
/api/metrica/vendas-por-estado
/api/metrica/endpoints
```

---

## Smoke test

Após subir o ambiente:

```bash
bash scripts/smoke-test.sh
```

O teste valida:

- health da aplicação
- catálogo
- resumo operacional
- criação de um pedido real
- persistência do checkout

---

## Kubernetes

O repositório já possui manifests em `k8s/` para aplicação e PostgreSQL.

A arquitetura Kubernetes será evoluída em uma etapa posterior para incluir:

```text
frontend
backend
postgres
simulator
payment-service
catalog-service
order-service
```

Isso permitirá demonstrar distributed tracing entre componentes.

---

## Roadmap de observabilidade

### Fase 1 — Ecommerce funcional

- [x] identidade visual ObsStore
- [x] catálogo
- [x] PostgreSQL
- [x] estoque
- [x] clientes
- [x] checkout
- [x] pedidos
- [x] pagamentos
- [x] simulador de usuários
- [x] meta de faturamento

### Fase 2 — Simulação avançada

- [ ] painel /lab
- [ ] gateway de pagamento lento
- [ ] banco lento
- [ ] HTTP 500 configurável
- [ ] Black Friday
- [ ] estoque crítico
- [ ] recuperação automática
- [ ] perfis de usuários

### Fase 3 — OpenTelemetry

- [ ] instrumentação Flask
- [ ] HTTP spans
- [ ] PostgreSQL spans
- [ ] custom spans de negócio
- [ ] métricas OTLP
- [ ] logs estruturados
- [ ] trace_id / span_id nos logs

### Fase 4 — Zabbix 8 APM

- [ ] envio OTLP
- [ ] ClickHouse
- [ ] visualização de traces
- [ ] análise de erros
- [ ] correlação log → trace
- [ ] métricas de negócio
- [ ] troubleshooting ponta a ponta

---

## Cenário que queremos demonstrar

```text
Faturamento começa a cair
          |
          v
Conversão de checkout cai
          |
          v
Latência de pagamento aumenta
          |
          v
Trace aponta payment.authorize
          |
          v
Log mostra timeout
          |
          v
Zabbix correlaciona impacto técnico e negócio
```

Esse é o objetivo central do ObsStore.

---

## Propósito

**ObsStore — Realistic Ecommerce Observability Lab**

Um ecommerce completo projetado para ensinar e demonstrar observabilidade.

Não é apenas um aplicativo que gera métricas. É um ambiente no qual negócio, infraestrutura, aplicações e experiência do usuário podem ser observados como partes da mesma operação.
