# Arquitetura da Plataforma de Dados Públicos com IA

Este documento descreve a arquitetura do sistema projetado para coletar, armazenar, processar e disponibilizar dados públicos de forma inteligente usando tecnologias modernas e Inteligência Artificial. Este documento baseia-se no diagrama visual "Arquitetura da Plataforma de Dados Públicos com IA".

## 1. Fontes de Dados (APIs Externas)
A plataforma se conecta a diversas fontes de dados públicos brasileiras:
- **Portal da Transparência:** Via chave de API gratuita.
- **PNCP (Portal Nacional de Contratações Públicas):** Sem autenticação requerida.
- **Compras.gov:** Sem autenticação requerida.
- **IBGE:** Sem autenticação requerida.
- **Câmara dos Deputados:** Sem autenticação requerida.
- **SIAPE / SIOP:** Autenticação via OAuth gov.br.
- **SICONFI (Tesouro Nacional):** Sem autenticação requerida.

## 2. API Collectors (Coleta Agendada)
Camada responsável por buscar os dados ativamente nas fontes:
- **Tecnologias:** `APScheduler` e `httpx`.
- **Recursos:** Implementa *rate limiting* para evitar bloqueios, *retry* com *backoff* exponencial para falhas, normalização de múltiplos formatos (JSON, CSV, XML) e trilha de logs detalhada.

## 3. Armazenamento
Arquitetura dividida para otimizar velocidade e confiabilidade:
- **Data Lake (Armazenamento Bruto):** Guarda os arquivos *raw* particionados por fonte e data (nos formatos Parquet e JSON). Serve como um cofre permanente da coleta.
- **Data Warehouse (Armazenamento Estruturado):** Banco de dados **PostgreSQL** para armazenar as entidades, tabelas fato e seus relacionamentos. Projetado para consultas ultra-rápidas.

## 4. Pipeline ETL (Transformação e Correlação)
Camada de processamento dos dados coletados:
- **Tecnologias:** `Pandas` e `Polars` (para máxima performance).
- **Recursos:** Limpeza dos dados sujos, enriquecimento, *join* estratégico entre bases diferentes (cruzamento por CNPJ, UF, período) e algoritmos para detecção primária de anomalias.

## 5. Camada de IA (Inteligência Artificial)
Inteligência embutida para análises profundas:
- **LLM Local:** Integração com o `Ollama` rodando o `Llama 3.2` para garantir privacidade e baixo custo na análise exploratória e geração de narrativas sobre os dados.
- **Busca Semântica:** Uso de *RAG* (Retrieval-Augmented Generation) e *Embeddings* para permitir que o usuário faça perguntas naturais e encontre dados dentro da plataforma.

## 6. Backend e APIs Internas
O motor principal da plataforma e orquestração:
- **Tecnologias:** `FastAPI`.
- **Recursos:** Fornece os *endpoints* REST de análise e consulta, gerencia autenticação, gerencia *cache* veloz via `Redis`, paginação inteligente e conexões bidirecionais via `WebSockets` para acompanhar *jobs* demorados em tempo real.

## 7. Saídas e Consumo (Outputs)
Maneiras como o usuário e outros sistemas consomem os dados processados:
- **Dashboards:** Interfaces em `Jupyter` ou `Streamlit` para análise exploratória visual e geração de gráficos interativos.
- **Relatórios:** Exportação periódica ou sob-demanda em PDF e Excel.
- **Alertas:** Notificações automáticas via E-mail, Slack ou *Webhooks* de anomalias encontradas.
- **API Pública:** Rotas abertas para consumo externo ou de terceiros interessados nos dados consolidados.

## 8. Observabilidade e Monitoramento
Saúde e acompanhamento em tempo real:
- **Tecnologias e Ferramentas:** `Loguru` (logs), `Prometheus` (métricas), `Sentry` (rastreio de erros) e sistemas de *Health Checks* individuais por coletor, garantindo alertas precisos se uma fonte parar de funcionar.

## 9. Infraestrutura Base
- **Desenvolvimento:** Orquestração local simples usando `Docker Compose`.
- **Produção:** *Deploy* pronto para VPS clássica ou serviços de nuvem PaaS como `Railway`.
- **Agendamento:** Tarefas baseadas em cron via `APScheduler`.
