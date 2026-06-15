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
- Kubernetes

---

## Estrutura do projeto

```text
ecommerce-app/
├── app/
│   ├── main.py
│   └── templates/
│       └── index.html
├── k8s/
│   ├── 00-namespace.yaml
│   ├── 01-secret.yaml
│   ├── 02-postgres-pvc.yaml
│   ├── 03-postgres.yaml
│   ├── 04-app.yaml
│   └── 05-ingress.yaml
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

## Como executar com Docker Compose

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

## Acessar o PostgreSQL com Docker Compose

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

## Parar a aplicação com Docker Compose

```bash
docker compose down
```

---

## Subir novamente com Docker Compose

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

## Logs com Docker Compose

Ver logs do Flask:

```bash
docker logs -f ecommerce_app
```

Ver logs do PostgreSQL:

```bash
docker logs -f ecommerce_postgres
```

---

# Deploy em Kubernetes

Este projeto também possui exemplos de manifests Kubernetes na pasta `k8s/`.

Esses arquivos servem como referência para subir a aplicação em um cluster Kubernetes com PostgreSQL.

> Observação: este repositório deixa os manifests prontos como exemplo. Antes de aplicar em um cluster real, publique a imagem Docker em um registry ou altere o campo `image` no arquivo `k8s/04-app.yaml`.

---

## Estrutura dos manifests Kubernetes

```text
k8s/
├── 00-namespace.yaml
├── 01-secret.yaml
├── 02-postgres-pvc.yaml
├── 03-postgres.yaml
├── 04-app.yaml
└── 05-ingress.yaml
```

---

## Recursos criados no Kubernetes

Os manifests criam:

```text
Namespace: ecommerce-lab
Secret: ecommerce-secret
PVC: postgres-pvc
Deployment: postgres
Service: postgres
Deployment: ecommerce-app
Service: ecommerce-app
Ingress: ecommerce-app
```

---

## Atenção sobre a imagem Docker

O arquivo `k8s/04-app.yaml` usa a seguinte imagem como exemplo:

```text
ghcr.io/fvcunhaa/ecommerce-app:latest
```

Antes de aplicar em um cluster Kubernetes real, é necessário publicar a imagem Docker em um registry ou alterar o campo `image` no arquivo:

```text
k8s/04-app.yaml
```

Exemplo usando Docker Hub:

```yaml
image: docker.io/SEU-USUARIO/ecommerce-app:latest
```

Exemplo usando GitHub Container Registry:

```yaml
image: ghcr.io/SEU-USUARIO/ecommerce-app:latest
```

---

## Como publicar a imagem manualmente

Exemplo com Docker Hub:

```bash
docker build -t SEU-USUARIO/ecommerce-app:latest .
docker login
docker push SEU-USUARIO/ecommerce-app:latest
```

Depois altere o arquivo `k8s/04-app.yaml`:

```yaml
image: docker.io/SEU-USUARIO/ecommerce-app:latest
```

Exemplo com GitHub Container Registry:

```bash
docker build -t ghcr.io/SEU-USUARIO/ecommerce-app:latest .
docker login ghcr.io
docker push ghcr.io/SEU-USUARIO/ecommerce-app:latest
```

Depois altere o arquivo `k8s/04-app.yaml`:

```yaml
image: ghcr.io/SEU-USUARIO/ecommerce-app:latest
```

---

## Aplicar no Kubernetes

Com `kubectl` configurado para o cluster:

```bash
kubectl apply -f k8s/
```

---

## Verificar recursos criados

```bash
kubectl get all -n ecommerce-lab
kubectl get pvc -n ecommerce-lab
kubectl get secrets -n ecommerce-lab
kubectl get ingress -n ecommerce-lab
```

---

## Acessar via NodePort

O service da aplicação usa NodePort na porta `30080`.

Acesse:

```text
http://IP-DO-NODE:30080
```

Exemplos:

```bash
curl http://IP-DO-NODE:30080/status
curl http://IP-DO-NODE:30080/api/dashboard
curl http://IP-DO-NODE:30080/api/coleta
```

---

## Acessar com Minikube

Se estiver usando Minikube:

```bash
minikube service ecommerce-app -n ecommerce-lab
```

Ou veja o IP do Minikube:

```bash
minikube ip
```

Depois acesse:

```text
http://IP-DO-MINIKUBE:30080
```

---

## Acessar com Ingress

O arquivo `k8s/05-ingress.yaml` é opcional e depende de um Ingress Controller instalado no cluster, como NGINX Ingress Controller.

Host configurado no exemplo:

```text
ecommerce.local
```

Para teste local, adicione no `/etc/hosts` da sua máquina:

```text
IP-DO-INGRESS ecommerce.local
```

Depois acesse:

```text
http://ecommerce.local
```

---

## Ver logs no Kubernetes

Ver logs da aplicação:

```bash
kubectl logs -f deployment/ecommerce-app -n ecommerce-lab
```

Ver logs do PostgreSQL:

```bash
kubectl logs -f deployment/postgres -n ecommerce-lab
```

---

## Entrar no PostgreSQL no Kubernetes

```bash
kubectl exec -it deployment/postgres -n ecommerce-lab -- psql -U ecommerce -d ecommerce
```

Consultar vendas:

```sql
SELECT COUNT(*) FROM vendas;

SELECT id, estado, produto, forma_pagamento, total, data
FROM vendas
ORDER BY id DESC
LIMIT 10;
```

Sair do PostgreSQL:

```sql
\q
```

---

## Remover ambiente Kubernetes

Remover usando os manifests:

```bash
kubectl delete -f k8s/
```

Ou remover o namespace inteiro:

```bash
kubectl delete namespace ecommerce-lab
```

---

## Observação sobre credenciais no Kubernetes

As credenciais no arquivo `k8s/01-secret.yaml` são de laboratório:

```text
POSTGRES_DB=ecommerce
POSTGRES_USER=ecommerce
POSTGRES_PASSWORD=ecommerce123
```

Em produção, não versionar secrets reais no GitHub.

Para produção, recomenda-se:

- Usar secrets gerenciados pelo provedor cloud
- Usar External Secrets Operator ou Sealed Secrets
- Não expor o PostgreSQL publicamente
- Usar senhas fortes
- Configurar backup do banco
- Configurar limites de CPU e memória
- Configurar probes com tempos adequados
- Usar Ingress com HTTPS
- Restringir acesso por firewall ou Security Groups

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

As credenciais presentes no arquivo `.env` e nos manifests Kubernetes são credenciais simples de lab:

```text
User: ecommerce
Password: ecommerce123
```

Para produção, recomenda-se:

- Não versionar o arquivo `.env`
- Não versionar secrets Kubernetes reais
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
