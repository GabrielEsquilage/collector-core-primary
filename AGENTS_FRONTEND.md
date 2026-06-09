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
* **Rota do Backend:** `GET /api/v1/admin/audit/jobs`
* **Parâmetros:** Aceita paginação (`limit`, `offset`).
* **Retorno:** Retorna apenas os jobs que estão com o status `running` ou `completed`. O backend já faz o filtro internamente.

### 3. O que exibir na Tabela de Auditoria
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

### 4. Regras de Ouro
* Mantenha as cores e o Design System atual da aplicação.
* **NÃO APAGUE MÉTODOS ANTERIORES.** Se o usuário acessava uma tela onde podia escolher status "pending", criar agendamentos e clicar em "Executar", essa tela DEVE continuar lá, intacta. A auditoria é um complemento.
