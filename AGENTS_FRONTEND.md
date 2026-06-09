# Tarefa Frontend: Submenu de Auditoria de Agendamentos

## Objetivo Principal
Você deve criar uma nova tela de **Auditoria** focada apenas em acompanhamento do histórico de execuções (Jobs concluídos ou em execução). 

**IMPORTANTE:** Você **NÃO DEVE** remover o "Botão de Executar", o modal de filtros, ou alterar o funcionamento da tela principal de Agendamentos que já existe. Todas as suas mudanças devem focar em CRIAR uma tela nova para auditoria, e não destruir/substituir o que já funciona.

O backend foi atualizado (na branch `feature/admin-auditoria-jobs`) para expor um endpoint que traz exclusivamente os dados que precisamos.

## Especificação da Nova Tela de Auditoria

### 1. Novo Menu/Submenu
* **Localização:** Adicione um item de navegação chamado **"Auditoria"** (pode ser um submenu debaixo do menu atual "Agendamentos").
* **Página Nova:** Crie uma rota e um componente de página dedicado (`AuditPage.tsx` ou `.vue` dependendo do seu framework) para abrigar a listagem.

### 2. Consumo de API
* **Rota Principal (Listagem):** `GET /api/v1/admin/audit/jobs`
  * **Parâmetros:** Aceita paginação (`limit`, `offset`), filtro de status opcional (`status=running` ou `status=completed`), e filtro de município (`codigo_ibge=1234567`). Se o `status` não for fornecido, retorna ambos (running e completed).
  * **Retorno:** Retorna os jobs de auditoria. O backend já garante que apenas jobs de auditoria apareçam.
* **Rota de Detalhes (Itens do Job):** `GET /api/v1/admin/audit/jobs/{job_id}/items`
  * **Parâmetros:** Apenas `limit` e `offset`. **NÃO inclua opções de filtragem por status na interface de detalhes.** O usuário quer ver tudo que pertence àquele job diretamente.
  * **Retorno:** Retorna os sub-itens do job selecionado. O JSON de resposta possui um array `items` com os seguintes campos que **devem** ser exibidos numa tabela detalhada:
    - `codigo_ibge` (Código do Município)
    - `mes_ano` (Mês e Ano)
    - `status` (Status do item, ex: success, failed)
    - `attempts` (Número de tentativas)
    - `pages_collected` (Páginas coletadas)
    - `records_received` (Registros recebidos)
    - `last_error` (O log de erro, se houver)
    - `started_at` e `finished_at` (Datas de execução)
* **Rota de Consulta de Payload:** `GET /api/v1/admin/audit/items/{item_id}/payloads`
  * **Parâmetros:** Nenhum.
  * **Retorno:** Retorna um array com todos os JSONs originais coletados para aquele item.

### 3. O que exibir na Tabela de Auditoria Principal
**Acima da Tabela (Filtros Opcionais):**
* Adicione um campo/select para filtrar por **Status** (`running` ou `completed`).
* Adicione um campo para filtrar por **Município** (esperando o `codigo_ibge`, mas você pode usar o componente de busca de municípios que já existe no projeto para enviar o código correto).
* Quando preenchidos, passe-os como `?status=...&codigo_ibge=...` para a rota principal `/audit/jobs`.

A tabela de auditoria deve focar na transparência das requisições e no progresso. As informações retornadas em cada item contêm o objeto `metadata_json`, que representa as "informações da request" solicitadas pelo usuário.
Você deve exibir em colunas:
1. **Código do Job (`job_code`)**
2. **Status (`status`)**: Deve ser `running` ou `completed`.
3. **Detalhes do Request (Parâmetros):**
   * Você pode ler de `metadata_json.resource`, `metadata_json.estado_sigla`, `metadata_json.mes_ano_inicio`, `metadata_json.mes_ano_fim`.
   * Formate essas informações em uma coluna clara (ex: "Bolsa Família - PR (01/2024 até 12/2024)").
4. **Métricas de Execução:**
   * Mostrar os totais de itens: `success_items` (completados), `failed_items` (com erro) em relação ao `total_items`.
5. **Datas:**
   * Exibir `started_at` (Início) e `finished_at` (Fim).
6. **Ação "Ver Detalhes":**
   * Em cada linha do job na tabela principal, crie um botão "Ver Detalhes". Quando o usuário clicar, consuma a **Rota de Detalhes** (`/audit/jobs/{job_id}/items`) passando o ID do job para listar todos os sub-itens.
   * **IMPORTANTE:** Para cada linha dessa tabela de sub-itens, se o `status` for `success`, exiba um botão **"Ver Payload"**. Ao clicar, faça uma requisição para a **Rota de Consulta de Payload** (`/audit/items/{item_id}/payloads`) passando o `id` daquele sub-item e exiba o JSON retornado formatado bonito na tela (um modal com `<pre>` ou um visualizador JSON embutido). Isso é essencial!

### 4. Regras de Ouro
* Mantenha as cores e o Design System atual da aplicação.
* **NÃO APAGUE MÉTODOS ANTERIORES.** Se o usuário acessava uma tela onde podia escolher status "pending", criar agendamentos e clicar em "Executar", essa tela DEVE continuar lá, intacta. A auditoria é um complemento.
