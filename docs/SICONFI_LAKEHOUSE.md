# Módulo SICONFI - Saúde Financeira Municipal (Arquitetura Lakehouse)

Este módulo foi projetado para coletar, armazenar e consultar dados contábeis de todos os municípios brasileiros através da API do Tesouro Nacional (SICONFI). 

Devido ao imenso volume de dados gerado pelos 5.570 municípios a cada bimestre, não utilizamos um banco de dados relacional (PostgreSQL) para armazenar os relatórios brutos. Em vez disso, adotamos uma arquitetura **Lakehouse** utilizando **Apache Parquet** e **DuckDB**.

## 🏗️ Arquitetura em Duas Camadas

### 1. Camada Prata (Silver)
Onde os dados brutos da API são armazenados da forma como chegam.
- **Como funciona:** O script baixa o JSON da API, limpa, tipa os dados via Pandas e salva arquivos `.parquet` particionados por ano (ex: `data_lake/silver/siconfi_rreo/ano=2023/`).
- **Tamanho:** Contém milhões de linhas detalhando todas as naturezas de despesa possíveis. Nenhuma API deve consultar esta camada diretamente.

### 2. Camada Ouro (Gold)
Onde residem os dados mastigados e prontos para uso em Dashboards/Frontend.
- **Como funciona:** Utilizamos um Catálogo Semântico (`siconfi_catalog.py`) que mapeia nomenclaturas confusas do governo para indicadores claros (ex: `DESPESA_SAUDE`, `RECEITA_TOTAL`).
- **O Processo:** O DuckDB varre os Parquets da camada Prata em milissegundos, realiza um PIVOT agrupando os dados por Município e Bimestre, e gera um arquivo minúsculo por ano: `kpis_macro_2023.parquet`.
- **Uso:** É este arquivo que as rotas do FastAPI leem para entregar os gráficos instantaneamente.

---

## 🚀 Como fazer a Carga Histórica (Para Contribuidores)

Se você acabou de clonar este projeto, o seu Data Lake local estará vazio. Não há necessidade de baixar o Brasil inteiro de 2018 até hoje se você não quiser. Você pode extrair apenas os anos que for analisar.

### O Script CLI
Criamos um script amigável e focado em Open Source para construir sua base histórica sem tomar bloqueio (*Rate Limit*) da API do Governo.

Pelo terminal, na raiz do projeto, rode:
```bash
python cli_carga_siconfi.py --anos 2023 2024 --delay 90.0
```

**Parâmetros:**
* `--anos`: Passe os anos separados por espaço. (ex: `--anos 2018 2019`). Padrão: 2018 a 2025.
* `--delay`: O tempo de espera em segundos entre cada município para evitar sobrecarga no servidor do Tesouro Nacional. O padrão é `90.0` (1,5 minutos). Se você for baixar um escopo pequeno, pode diminuir o delay por sua conta e risco (ex: `--delay 1.5`).

### À Prova de Falhas
O script foi construído para ser *resume-able*. Se a sua internet cair no meio da carga, não se preocupe. O script vai retomando de onde parou as gravações na pasta Parquet.

## 🛠️ Onde ficam os arquivos?
* **Catálogo de Indicadores:** `app/services/siconfi/siconfi_catalog.py` (Adicione novos indicadores do Tesouro aqui).
* **Motor do Lakehouse:** `app/services/siconfi/rreo_sync_service.py` (Lógica de conversão Bronze -> Prata -> Ouro).
* **Serviço de Comunicação HTTP:** `app/services/siconfi/siconfi_service.py`.
* **Data Lake Local:** `data_lake/` (Ignorado pelo Git, onde seus Parquets residem).
