# 📊 DataCrypt Collector - Coletor de Dados Públicos

## 📖 Sobre o Projeto
O **DataCrypt Collector** é um sistema para extração, processamento e armazenamento de dados públicos brasileiros. Ele busca dados brutos de fontes governamentais (como Portal da Transparência, IBGE, PNCP, Compras.gov), os processa e os armazena de maneira estruturada para facilitar o consumo e a análise.

Além disso, a arquitetura do projeto foi pensada para facilitar a integração com modelos de Inteligência Artificial (como LLMs rodando localmente via Ollama), visando permitir análises exploratórias e buscas nas bases coletadas no futuro.

## 🏛️ Visão da Arquitetura
A arquitetura do DataCrypt Collector é dividida em alguns módulos principais:
- **API Central (FastAPI):** Expõe os endpoints de consulta e os gatilhos para agendamento de coletas.
- **Workers de Coleta:** Módulos assíncronos (construídos com *asyncio*) responsáveis por realizar as buscas nas APIs externas, lidando com detalhes como paginação e limites de requisição (rate limiting).
- **Processamento de Dados (ETL):** Utiliza ferramentas como `Polars` para a limpeza e estruturação dos dados coletados.
- **Armazenamento Híbrido:** Os dados podem ser exportados em formato de arquivo (`.parquet`) para pipelines de dados e também são persistidos em um banco de dados relacional.

## 🚀 Tecnologias Utilizadas
- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI (com Uvicorn)
- **Banco de Dados:** PostgreSQL
- **ORM & Drivers:** SQLAlchemy 2.0 e `asyncpg`
- **Manipulação de Dados:** Polars, PyArrow
- **Requisições HTTP:** `httpx`
- **Infraestrutura:** Docker e Docker Compose

## 🗄️ Modelagem de Dados
O esquema de dados (`datacrypt`) divide a informação em:
- **Dimensões:** Tabelas como `dim_regioes`, `dim_estados`, `dim_municipios` e catálogos do IBGE, para padronizar a geolocalização e os metadados.
- **Fatos:** Tabelas que armazenam os dados quantitativos, como `fato_repasse_municipio` e `fato_demografia`.
- **Controle e Logs:** Tabelas como `transparencia_carga_job` para acompanhamento, rastreio e log do status das coletas.

## ⚙️ Como Executar Localmente

### Pré-requisitos
- **Docker** e **Docker Compose** instalados na sua máquina.

### Passo a Passo
1. **Clone o repositório:**
```bash
git clone https://github.com/GabrielEsquilage/collector-core-primary.git
cd collector-core-primary
```

2. **Configure as Variáveis de Ambiente:**
Copie o arquivo de exemplo e edite conforme necessário:
```bash
cp .env.example .env
```
*(Lembre-se de adicionar a sua `PORTAL_TRANSPARENCIA_API_KEY` no arquivo `.env` para evitar bloqueios ao consultar a API do governo).*

3. **Suba os containers:**
```bash
docker-compose up -d --build
```

4. **Acesse a API:**
A aplicação estará rodando em: `http://localhost:8000`.
A documentação interativa (Swagger) fica disponível em: `http://localhost:8000/docs`.

## 📌 Principais Rotas
A API possui os seguintes sub-roteadores sob `/api/v1/`:
- `GET /api/v1/ibge`: Rotas para metadados e pesquisas do IBGE.
- `POST/GET /api/v1/transparencia`: Serviços de coleta e consulta para o Portal da Transparência.
- `GET /health` e `/health/startup-sync`: Endpoints de checagem de status e observabilidade da aplicação.

## 🤝 Contribuição
- Procure validar conexões e utilizar `AsyncSession` no banco de dados para evitar bloqueios no fluxo assíncrono.
- Consulte as documentações internas antes de implementar novas integrações ou alterações significativas na modelagem.

## 📄 Licença
Licenciado sob a política de software livre especificada no arquivo `LICENSE`.


<img width="1052" height="582" alt="image" src="https://github.com/user-attachments/assets/c3744f63-12a4-49f1-ab35-f5fe3bf6b31d" />

<img width="1010" height="586" alt="image" src="https://github.com/user-attachments/assets/faf24f94-2ccf-4a7c-b524-2a775906e0ec" />

<img width="1331" height="641" alt="image" src="https://github.com/user-attachments/assets/e9cb63e3-eee0-42ef-ad73-e887c490aa8a" />



