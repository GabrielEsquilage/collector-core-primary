Implemente a primeira integração de benefícios do Portal da Transparência neste repositório, seguindo rigorosamente o AGENTS.md existente e o padrão arquitetural já usado no projeto.

Objetivo desta tarefa:
- implementar a coleta de “Novo Bolsa Família por município”
- persistir os dados no Postgres do collector core
- expor leitura via API interna
- manter o banco o mais enxuto possível
- não implementar dashboard nem ETL analítico agora

Endpoint externo:
GET /api-de-dados/novo-bolsa-familia-por-municipio

Base URL:
https://api.portaldatransparencia.gov.br/api-de-dados

Autenticação:
usar a variável de ambiente PORTAL_TRANSPARENCIA_API_KEY no header:
chave-api-dados: <valor>

Exemplo de consulta:
codigoIbge=5300108
mesAno=202301
pagina=1

Requisitos funcionais:
1. Criar integração para coletar dados de Novo Bolsa Família por município com paginação por `pagina`
2. Persistir no Postgres somente o mínimo necessário para baixo acoplamento relacional
3. Expor endpoint interno para consulta dos dados já persistidos
4. Não chamar a API externa no endpoint de leitura
5. Implementar idempotência para evitar duplicação
6. Seguir a estrutura e convenções já existentes no projeto

Modelagem mínima esperada no banco:
Criar uma tabela de fato enxuta para benefícios por município com estes campos:
- id
- id_externo
- tipo_beneficio
- data_referencia
- municipio_codigo_ibge
- valor
- quantidade_beneficiados
- payload_json
- collected_at

Regras de modelagem:
- não duplicar município, UF nem região em colunas relacionais
- usar apenas municipio_codigo_ibge como referência geográfica
- assumir que município, UF e região já existem no projeto em outra estrutura
- manter payload_json para rastreabilidade e reprocessamento
- criar restrição de unicidade ou estratégia de upsert para impedir duplicidade lógica por:
  id_externo + tipo_beneficio + data_referencia + municipio_codigo_ibge

Mapeamento esperado do payload externo:
- id -> id_externo
- dataReferencia -> data_referencia
- municipio.codigoIBGE -> municipio_codigo_ibge
- valor -> valor
- quantidadeBeneficiados -> quantidade_beneficiados
- tipo_beneficio -> valor fixo "novo_bolsa_familia"
- payload_json -> resposta original completa

Implementação esperada:
- cliente HTTP assíncrono com httpx
- timeout
- tratamento de erro HTTP
- paginação até resposta vazia
- serviço de coleta
- persistência com SQLAlchemy compatível com o projeto
- rota POST para disparar coleta
- rota GET para ler dados persistidos

Rotas internas desejadas:
- POST /transparencia/beneficios/novo-bolsa-familia/collect
- GET /transparencia/beneficios/novo-bolsa-familia

Comportamento da rota POST:
- aceitar parâmetros de coleta adequados para mesAno, codigoIbge e paginação
- permitir coletar ao menos um município e um mês por execução
- salvar os registros retornados no Postgres
- retornar resumo da coleta

Comportamento da rota GET:
- ler do Postgres
- permitir filtro por mesAno e codigoIbge
- não chamar a API externa

Variáveis de ambiente:
- PORTAL_TRANSPARENCIA_API_KEY
- PORTAL_TRANSPARENCIA_BASE_URL com default https://api.portaldatransparencia.gov.br/api-de-dados

Critérios de aceite:
- consigo coletar dados de Novo Bolsa Família por município para um codigoIbge e um mesAno
- os dados ficam persistidos no Postgres
- a leitura interna funciona sem acessar a API externa
- a tabela salva só o mínimo necessário
- não há duplicação lógica ao repetir a coleta
- o código segue a arquitetura já existente do projeto

Importante:
- antes de codar, inspecione os arquivos equivalentes do projeto para seguir o padrão real já usado
- reutilize estruturas existentes sempre que possível
- entregue os arquivos completos alterados
- ao final, rode os testes possíveis ou validações disponíveis e resuma o que foi criado

---

## Code Review: `app/services/transparencia/jobs/`

Analisando a estrutura e a implementação do diretório `app/services/transparencia/jobs/`, a base do projeto tem decisões arquiteturais sólidas, mas esconde gargalos críticos relacionados à concorrência e banco de dados.

### 🟢 Pontos Fortes

1. **Separação de Responsabilidades (Separation of Concerns):** A divisão é madura. `repository.py` lida com as queries do SQLAlchemy, `service.py` aplica regras de negócio (seed, queuing), `runner.py` orquestra a execução e `worker.py` roda o loop de background. 
2. **Tipagem Estática:** O uso extensivo de `TypedDict`, retornos tipados e listas (`tuple`, `list`, etc) mostra uma base sólida.
3. **Resiliência:** Lógica de *Stale Jobs* e contagem de tentativas (`max_attempts`) evita que jobs fiquem presos como `RUNNING`.
4. **Rate Limiting Dinâmico:** A classe `PortalRequestRateLimiter` adapta requests por horário, evitando bans de IP.

### 🔴 Pontos de Atenção Críticos (Gargalos)

1. **Bloqueio do Event Loop (Crítico):** No `worker.py`, `asyncio.gather` chama métodos síncronos com SQLAlchemy (`SessionLocal`). Como as conexões não são assíncronas, *cada query no banco bloqueia todo o event loop do processo*, inutilizando o paralelismo do `gather` e travando potenciais rotas HTTP (FastAPI) no mesmo worker. O correto é migrar para `AsyncSession` (via `asyncpg`).
2. **Custo de Conexões (`runner.py`):** O job item no `runner.py` abre e fecha a sessão `SessionLocal` em CADA etapa do fluxo. Um job com 10.000 itens vai recriar o contexto 30.000 vezes, gerando enorme overhead no connection pool.
3. **State Global no Rate Limiter:** `PortalRequestRateLimiter` usa locks do `asyncio` em memória. Com múltiplos workers (gunicorn/pods), o estado é segmentado e o Rate Limit passa a não ser global. Ideal é migrar o state lock para um controle via Redis.
4. **Commit Excessivo no Seed:** Em `service.py`, `db.commit()` ocorre dentro do laço `for plan in plans`. Falhas no meio geram DB inconsistente; deve-se preferir `flush` ou adicionar todos e comitar apenas no final.
5. **Paginação com Offset:** Consultas que utilizam `.offset().limit()` em tabelas de logging tenderão a ficar ineficientes; sugere-se paginação Keysets (Cursor).

### Plano de Ação:
* **Refatoração Async:** Implementar suporte oficial ao driver `asyncpg` no banco de dados e modificar os repositórios do fluxo de jobs para retornarem chamadas assíncronas reais.
* **Agrupamento de Transações:** Revisar injeção de sessão nas rotinas que abrem excessivamente a conexão.

---


Objetivo da Refatoração: Otimização de I/O entre Polars e PostgreSQL

Esta documentação técnica define a alteração necessária no pipeline ELT (arquivo elr.py) para eliminar um pequeno gargalo de memória na ponte entre o Polars (Rust) e o psycopg2 (Python).
1. O Problema

Atualmente, o processo de serialização dos dados extraídos utiliza o método .to_dicts(). Isso força o Polars a converter os dados ultrarrápidos dele em Dicionários Python (que são pesados), e depois você gasta mais CPU criando uma lista de Tuplas.
2. A Solução

A otimização consiste em utilizar um recurso nativo mais eficiente. O Polars possui um método nativo chamado .rows() que já extrai os dados diretamente como uma lista de tuplas puras, na exata ordem das colunas do DataFrame. Você pode substituir toda a conversão de to_dicts e a List Comprehension por uma única linha.
3. Guia de Implementação no elr.py

A. Remover o bloco de código abaixo:
Busque no seu script o trecho onde o DataFrame é convertido e iterado, e exclua estas linhas:
Python

    records = df_clean.to_dicts()
    
    print(f"Registros únicos pós-limpeza: {len(records)}")
    
    # ... código de conexão do banco ...
        
        values = [
            (
                r["tipo_beneficio"],
                r["data_referencia"],
                r["municipio_codigo_ibge"],
                r["valor"],
                r["quantidade_beneficiados"]
            )
            for r in records
        ]

B. Substituir pelo método otimizado:
No lugar da conversão em dicionário e da List Comprehension, insira a extração direta das tuplas usando .rows():
Python

    # Extrai os dados em formato nativo de tuplas
    values = df_clean.rows()
    
    print(f"Registros únicos pós-limpeza prontos para inserção: {len(values)}")
    
    # ... código de conexão do banco ...
    # O execute_values já receberá a variável 'values' normalmente

4. Checklist de Validação

    Ordem das Colunas: Verifique se o df.select([ ... ]) que cria o df_clean está exatamente na mesma ordem dos campos do INSERT INTO. O método .rows() confia que a ordem das colunas do DataFrame corresponde aos valores esperados pelo banco de dados.

---

# Integração IBGE - Metadados e SIDRA (Collector Primary)

## 📌 Contexto e Objetivo
Expandir a integração existente do IBGE (que atualmente sincroniza Estados e Municípios) no `Collector Primary`. O objetivo é automatizar a descoberta de pesquisas ativas via API de Metadados, identificar novos períodos disponíveis e realizar a extração pesada dos dados estatísticos demográficos brutos via API do SIDRA, armazenando tudo no PostgreSQL e servindo via API interna.

## 🛠 Arquitetura e Padrões
* **Framework Base:** Python 3.10+ com FastAPI.
* **ORM e Migrations:** SQLAlchemy (ou SQLModel) e Alembic.
* **Processamento de Dados:** Polars (manipulação estrutural de alto desempenho e limpeza do JSON do SIDRA).
* **Requisições HTTP:** `httpx` (cliente assíncrono).
* **Orquestração:** Celery, APScheduler ou similar para agendamento dos jobs de sincronização.
* **Banco de Dados:** PostgreSQL (cargas via *Upsert* / `ON CONFLICT DO UPDATE`).

---

## 📋 Épicos e Tarefas (Tasks)

### Fase 1: Modelagem do Catálogo de Metadados
**Objetivo:** Criar a tabela dimensão e a rotina de sincronização das pesquisas disponíveis.

* [ ] **Task 1.1: Criar Modelos SQLAlchemy e Migration Alembic (`dim_pesquisa_ibge`)**
    * **Campos:** `codigo` (String, Primary Key), `nome` (String), `situacao` (String), `categoria` (String), `periodicidade_divulgacao` (String), `tags_tematicas` (ARRAY de Strings ou JSONB), `atualizado_em` (DateTime, default `func.now()`).
* [ ] **Task 1.2: Criar Job de Sincronização do Catálogo**
    * **Endpoint:** `GET https://servicodados.ibge.gov.br/api/v2/metadados/pesquisas`
    * **Regra de Negócio Crítica:** Ingerir/Atualizar APENAS os registros onde a chave `"situacao"` for igual a `"Ativa"`.
    * **Ação:** Utilizar `httpx.AsyncClient` e fazer um *Upsert* usando a sintaxe do SQLAlchemy (`insert().on_conflict_do_update()`).

### Fase 2: Orquestração e Descoberta de Períodos
**Objetivo:** Identificar automaticamente quando o IBGE libera novos dados para as pesquisas ativas.

* [ ] **Task 2.1: Criar Job de Varredura de Períodos**
    * **Lógica:** Buscar no banco todos os códigos de pesquisas ativas. Para cada código, fazer a requisição:
    * **Endpoint:** `GET /pesquisas/{codigo_pesquisa}/periodos`
    * **Ação:** Comparar os períodos retornados com os já mapeados no banco. Se houver um período novo (ex: virou o ano do Censo), colocar uma mensagem na fila ou disparar diretamente a Task 3.1.

### Fase 3: Ingestão Pesada de Dados (Integração SIDRA)
**Objetivo:** Extrair o dado populacional/demográfico real via processamento em lote.

* [ ] **Task 3.1: Extração e Transformação com Polars**
    * **Endpoint de Exemplo:** `GET https://apisidra.ibge.gov.br/values/t/9514/n6/in%20n3%2041/v/93/p/2022`
    * **Regra de Negócio Crítica (Parsing):** O array retornado do SIDRA possui cabeçalho descritivo no índice `0`. Carregar o DataFrame Polars ignorando a primeira linha (`raw_df = pl.DataFrame(data[1:])`).
* [ ] **Task 3.2: Limpeza e Tipagem (`Polars`)**
    * Selecionar e renomear: `D1C` para `codigo_ibge_municipio` (Int64) e `V` para `valor_estatistico` (Int64/Float64).
* [ ] **Task 3.3: Carga Batch no PostgreSQL**
    * Converter o DataFrame tratado e realizar inserção em lote (ex: `write_database` do Polars usando engine SQLAlchemy ou *Bulk Upsert* nativo) na tabela `dim_municipio` ou `fato_demografia`.

### Fase 4: Camada de Distribuição (API FastAPI)
**Objetivo:** Servir os dados limpos e consolidados.

* [ ] **Task 4.1: Criar Routers (`APIRouter`) no FastAPI**
    * **Rota sugerida:** `GET /api/v1/demografia/municipios/{codigo_ibge}`
    * **Ação:** Criar funções assíncronas mapeando parâmetros opcionais (Query Parameters como `?ano=2022`) para montar a query SQLAlchemy de forma dinâmica.
* [ ] **Task 4.2: Configurar Schemas Pydantic**
    * Criar os modelos Pydantic de `Response` para garantir a validação e formatação correta de saída do JSON (padronização camelCase se exigido pelo frontend).

### Fase 5: Garantia de Qualidade (QA)
**Objetivo:** Assegurar resiliência das integrações.

* [ ] **Task 5.1: Resiliência de Rede**
    * Adicionar um mecanismo de retry (como a biblioteca `tenacity` do Python) nas chamadas `httpx` para lidar com falhas temporárias (Status 503, Timeout) nas APIs do IBGE.
* [ ] **Task 5.2: Testes Automatizados com Pytest**
    * Utilizar `pytest` + `pytest-asyncio`.
    * Usar a biblioteca `respx` ou `pytest-httpx` para *mockar* as respostas das APIs do IBGE, testando especificamente a lógica de exclusão do `índice 0` do SIDRA e os filtros de situação `"Ativa"`.