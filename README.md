# Ecommerce App Demo

Aplicação simples simulando um ecommerce, com dashboard, métricas de negócio, endpoints monitorados e persistência de dados em PostgreSQL.

Este projeto foi criado para demonstração, testes, estudo e integração com ferramentas de monitoramento como Zabbix.

---

## Tecnologias utilizadas

- Python 3.12
- Flask
- PostgreSQL 16
- Docker
- Docker Compose

---

## Estrutura do projeto

```text
ecommerce-app/
├── app/
│   ├── main.py
│   └── templates/
│       └── index.html
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
└── README.md
```

---

## Sobre o arquivo `.env`

Este projeto possui um arquivo `.env` versionado propositalmente porque é um ambiente de laboratório/demo.

O objetivo é permitir que qualquer pessoa clone o projeto e suba a aplicação rapidamente com Docker Compose, sem precisar configurar variáveis manualmente.

> Atenção: em ambiente de produção, nunca publique senhas reais no GitHub.

Arquivo `.env` usado neste lab:

```env
FLASK_ENV=development

POSTGRES_DB=ecommerce
POSTGRES_USER=ecommerce
POSTGRES_PASSWORD=ecommerce123
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

DATABASE_URL=postgresql://ecommerce:ecommerce123@postgres:5432/ecommerce
```

---

## Como executar a aplicação

Clone o projeto:

```bash
git clone https://github.com/fvcunhaa/ecommerce-app.git
cd ecommerce-app
```

Suba os containers:

```bash
docker compose up -d --build
```

Verifique se os containers subiram:

```bash
docker ps
```

A aplicação ficará disponível em:

```text
http://localhost
```

Se estiver rodando em uma VM ou servidor, acesse pelo IP público ou privado da máquina:

```text
http://IP-DO-SERVIDOR
```

---

## Serviços criados pelo Docker Compose

O projeto sobe dois containers:

```text
ecommerce_app
ecommerce_postgres
```

A aplicação Flask escuta internamente na porta `5000`, mas é publicada na porta `80` do host.

Mapeamento:

```text
Host: 80
Container Flask: 5000
```

O PostgreSQL usa:

```text
Host: postgres
Porta: 5432
Database: ecommerce
User: ecommerce
Password: ecommerce123
```

---

## Endpoints principais

### Página principal

```text
http://localhost
```

### Status da API

```text
http://localhost/status
```

### Dashboard geral

```text
http://localhost/api/dashboard
```

### Executar nova coleta

```text
http://localhost/api/coleta
```

Essa rota simula novas vendas, atualiza os endpoints monitorados e recalcula o snapshot de métricas.

### Últimas vendas

```text
http://localhost/api/vendas/ultimas
```

### Lista de produtos

```text
http://localhost/produtos
```

---

## Endpoints de métricas de negócio

### Total de vendas

```text
http://localhost/api/metrica/vendas-total
```

### Total de pedidos

```text
http://localhost/api/metrica/total-pedidos
```

### Ticket médio

```text
http://localhost/api/metrica/ticket-medio
```

### Carrinhos criados

```text
http://localhost/api/metrica/carrinhos-criados
```

### Carrinhos abandonados

```text
http://localhost/api/metrica/carrinhos-abandonados
```

### Taxa de abandono de carrinho

```text
http://localhost/api/metrica/abandono-carrinho
```

### Pagamentos

```text
http://localhost/api/metrica/pagamentos
```

### Vendas por estado

```text
http://localhost/api/metrica/vendas-por-estado
```

---

## Endpoints de monitoramento

### Todos os endpoints monitorados

```text
http://localhost/api/metrica/endpoints
```

### Status de um endpoint específico

Exemplo:

```text
http://localhost/api/metrica/endpoints/status/status
```

### Response code de um endpoint específico

Exemplo:

```text
http://localhost/api/metrica/endpoints/status/response-code
```

### Latência de um endpoint específico

Exemplo:

```text
http://localhost/api/metrica/endpoints/status/latencia
```

---

## Endpoints simulados do ecommerce

A aplicação possui endpoints simulando um fluxo simples de ecommerce:

```text
/status
/login
/produtos
/carrinho/criar
/carrinho/adicionar
/carrinho/resumo
/checkout
/endereco
/pagamento/pix
/pagamento/boleto
/pagamento/cartao
/sucesso
```

Observação: o endpoint de boleto retorna erro propositalmente para simular falha:

```text
/pagamento/boleto
```

Ele retorna HTTP 500 para representar uma API de boleto indisponível.

---

## Persistência no PostgreSQL

As vendas simuladas e o estado do simulador são salvos no PostgreSQL.

Tabelas criadas automaticamente:

```text
vendas
simulador_state
```

A tabela `vendas` armazena os pedidos simulados.

A tabela `simulador_state` armazena informações gerais do simulador, como:

```text
carrinhos_criados
numero_coleta
ultima_atualizacao
```

---

## Acessar o PostgreSQL

Entre no banco com:

```bash
docker exec -it ecommerce_postgres psql -U ecommerce -d ecommerce
```

Consultar quantidade de vendas:

```sql
SELECT COUNT(*) FROM vendas;
```

Consultar últimas vendas:

```sql
SELECT id, estado, produto, forma_pagamento, total, data
FROM vendas
ORDER BY id DESC
LIMIT 10;
```

Consultar estado do simulador:

```sql
SELECT *
FROM simulador_state;
```

Sair do PostgreSQL:

```sql
\q
```

---

## Testar a aplicação via terminal

Status:

```bash
curl http://localhost/status
```

Dashboard:

```bash
curl http://localhost/api/dashboard
```

Executar coleta:

```bash
curl http://localhost/api/coleta
```

Últimas vendas:

```bash
curl http://localhost/api/vendas/ultimas
```

---

## Validar persistência dos dados

Execute uma coleta:

```bash
curl http://localhost/api/coleta
```

Consulte a quantidade de vendas:

```bash
docker exec -it ecommerce_postgres psql -U ecommerce -d ecommerce -c "SELECT COUNT(*) FROM vendas;"
```

Reinicie apenas a aplicação:

```bash
docker restart ecommerce_app
```

Consulte novamente:

```bash
docker exec -it ecommerce_postgres psql -U ecommerce -d ecommerce -c "SELECT COUNT(*) FROM vendas;"
```

Se a quantidade continuar, significa que os dados estão persistidos corretamente no PostgreSQL.

---

## Parar a aplicação

```bash
docker compose down
```

---

## Subir novamente

```bash
docker compose up -d
```

---

## Recriar a aplicação após alterações no código

```bash
docker compose up -d --build
```

---

## Apagar tudo, incluindo dados do banco

Atenção: este comando remove também o volume do PostgreSQL e apaga os dados persistidos.

```bash
docker compose down -v
```

Depois, para subir novamente do zero:

```bash
docker compose up -d --build
```

---

## Logs da aplicação

Ver logs do Flask:

```bash
docker logs -f ecommerce_app
```

Ver logs do PostgreSQL:

```bash
docker logs -f ecommerce_postgres
```

---

## Publicar alterações no GitHub

Depois de alterar arquivos, use:

```bash
git add .
git status
git commit -m "Atualiza documentação e configuração do projeto"
git push
```

---

## Observação de segurança

Este projeto é apenas para laboratório, estudo e demonstração.

As credenciais presentes no arquivo `.env` são credenciais simples de lab:

```text
User: ecommerce
Password: ecommerce123
```

Para produção, recomenda-se:

- Não versionar o arquivo `.env`
- Usar senhas fortes
- Usar secrets do ambiente
- Não expor o PostgreSQL publicamente
- Utilizar HTTPS
- Restringir acesso por firewall
- Configurar backup do banco de dados

---

## Autor

Projeto mantido por Francisco Cunha.

GitHub:

```text
https://github.com/fvcunhaa
```
