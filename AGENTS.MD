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
