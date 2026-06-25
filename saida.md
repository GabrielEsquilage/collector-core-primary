# Alterações no Backend - Analytics do Município (Social)

Este documento descreve o novo endpoint implementado para suprir os dados do painel analítico da visão "Município (Social)", cruzando dados do município selecionado com o contexto do estado.

## Novo Endpoint

**URL:** `GET /transparencia/beneficios/analytics/municipio-kpis`

### Parâmetros de Query String (Obrigatórios)
- `tipoBeneficio` (string): Tipo de benefício a ser consultado (ex: `bolsa_familia`, `auxilio_brasil`).
- `ano` (int): Ano de referência (ex: `2023`).
- `uf` (string): Sigla do estado (ex: `PR`).
- `codigoIbge` (string): Código IBGE do município (ex: `4106902`).

### Estrutura de Resposta (JSON)

A resposta retorna todas as métricas agregadas em uma única requisição.

```json
{
  "tipo_beneficio": "bolsa_familia",
  "ano": 2023,
  "uf": "PR",
  "codigo_ibge": "4106902",
  "data": {
    "media_beneficiarios_municipio": 505.0,
    "valor_medio_mensal_municipio": 125000.0,
    "taxa_variacao_beneficiarios_municipio": 0.02,
    "populacao_total": 25444,
    "taxa_cobertura_social": 1.98,
    "repasse_per_capita": 58.95,
    "historico_mensal_municipio": [
      {
        "mes": 1,
        "valor": 120000.0,
        "quantidade_beneficiados": 500
      },
      {
        "mes": 2,
        "valor": 130000.0,
        "quantidade_beneficiados": 510
      }
    ]
  }
}
```

### Detalhamento dos Campos no objeto `data`:
- `media_beneficiarios_municipio` (float): A média mensal de beneficiários do município, calculada somando todos os beneficiários do ano de exercício filtrado e dividindo por 12.
- `valor_medio_mensal_municipio` (float): A média do valor financeiro repassado por mês ao município, dividindo o valor total do ano de exercício por 12.
- `taxa_variacao_beneficiarios_municipio` (float): A **variação mensal** da quantidade de beneficiários no município, comparando o último mês disponível com o mês imediatamente anterior. Exemplo: `0.02` representa um aumento de 2%, e `-0.10` representa uma queda de 10%.
- `populacao_total` (int ou str): A população residente total do município baseado na estimativa ou Censo do IBGE mais recente. Retorna a mensagem `"Dados do Censo indisponíveis para este município."` caso não haja dados demográficos populados no sistema para o município consultado.
- `taxa_cobertura_social` (float ou str): Percentual populacional coberto pelo benefício `(media_beneficiarios / populacao_total) * 100`. Indica qual fatia da cidade depende do programa (Ex: `1.98` = 1,98% da cidade). Retorna a mesma mensagem de indisponibilidade caso não haja população registrada.
- `repasse_per_capita` (float ou str): O montante anual injetado na cidade por habitante `(valor_total_ano / populacao_total)`. Demonstra a densidade econômica do repasse social. Retorna a mesma mensagem de indisponibilidade caso não haja população registrada.
- `historico_mensal_municipio` (array): Lista contendo os repasses mês a mês daquele município no `ano`. Cada objeto interno contém o número do `mes`, o `valor` financeiro (float) e a `quantidade_beneficiados` (int).

---
**Nota para o Frontend:** As integrações já podem ser realizadas conectando os parâmetros do filtro de tela diretamente à URL descrita.
