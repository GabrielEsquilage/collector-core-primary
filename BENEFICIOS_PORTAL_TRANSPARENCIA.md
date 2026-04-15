# Beneficios do Portal da Transparencia

Este arquivo registra a regra operacional para escolher entre os endpoints de beneficios por municipio do Portal da Transparencia.

## Regra de uso por periodo

- `bolsa-familia-por-municipio`: usar de `201301` ate `202110`
- `auxilio-brasil-por-municipio`: usar de `202111` ate `202302`
- `novo-bolsa-familia-por-municipio`: usar de `202303` em diante

## Regra por ano

- `2013` ate `2020`: usar `bolsa-familia-por-municipio`
- `2021`: usar `auxilio-brasil-por-municipio` apenas de novembro em diante
- `2021-01` ate `2021-10`: usar `bolsa-familia-por-municipio`
- `2021-11` e `2021-12`: usar `auxilio-brasil-por-municipio`
- `2022`: usar `auxilio-brasil-por-municipio`
- `2023`: ano de transicao
- `2023-01` e `2023-02`: usar `auxilio-brasil-por-municipio`
- `2023-03` em diante: usar `novo-bolsa-familia-por-municipio`
- `2024+`: usar `novo-bolsa-familia-por-municipio`

## Observacao operacional

Se o agendamento for mensal, usar a regra por `mesAno`.

Se o agendamento for anual, `2023` nao deve ser tratado por um unico endpoint. O ideal e quebrar esse ano por mes.

Se o periodo desejado for anterior a `202111`, usar `bolsa-familia-por-municipio`. Pelo Portal da Transparencia, essa base cobre de `01/2013` ate `10/2021`.

## Referencias

- O Portal da Transparencia informa a cobertura historica das bases de beneficios aos cidadaos:
  `https://portaldatransparencia.gov.br/origem-dos-dados`
- Auxilio Brasil comeca a ser pago em `17/11/2021`:
  `https://www.gov.br/mds/pt-br/noticias-e-conteudos/desenvolvimento-social/noticias-desenvolvimento-social/auxilio-brasil-comeca-a-ser-pago-no-dia-17-de-novembro`
- O MDS informa que o Auxilio Brasil foi substituido pelo Bolsa Familia em `marco de 2023`:
  `https://www.gov.br/mds/pt-br/acesso-a-informacao/perguntas_frequentes/bolsa-familia-beneficiario/1-o-programa-auxilio-brasil`
- O Novo Bolsa Familia tem ato normativo de `02/03/2023`:
  `https://www.gov.br/secom/pt-br/assuntos/obrasilvoltou/cuidado/novo-bolsa-familia`
- A pagina da API lista `bolsa-familia-por-municipio` entre os endpoints disponiveis:
  `https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email`
