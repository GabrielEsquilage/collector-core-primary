import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent, type MouseEvent } from "react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { api, ApiError } from "../lib/api/client";
import { formatDateTime, formatInteger, formatPercent } from "../lib/format";
import type {
  JobSeedRequest,
  SeedResource,
  SeedTipoBeneficio,
} from "../lib/api/types";

const activeStatuses = new Set(["queued", "running"]);
const resettableStatuses = new Set(["failed", "completed_with_errors"]);

type SeedMode = "year" | "range";

type SeedOption = {
  resource: SeedResource;
  tipoBeneficio: SeedTipoBeneficio;
  label: string;
  range: string;
};

type SeedNotice = {
  createdCount: number;
  existingCount: number;
  label: string;
  estadoSigla: string;
};

const seedOptions: SeedOption[] = [
  {
    resource: "bolsa-familia-por-municipio",
    tipoBeneficio: "bolsa_familia",
    label: "Bolsa Família",
    range: "201301 até 202110",
  },
  {
    resource: "auxilio-brasil-por-municipio",
    tipoBeneficio: "auxilio_brasil",
    label: "Auxílio Brasil",
    range: "202111 até 202302",
  },
  {
    resource: "novo-bolsa-familia-por-municipio",
    tipoBeneficio: "novo_bolsa_familia",
    label: "Novo Bolsa Família",
    range: "202303 em diante",
  },
];

function getSeedOption(resource: SeedResource): SeedOption {
  return seedOptions.find((option) => option.resource === resource) ?? seedOptions[0]!;
}

function isValidMesAno(value: string) {
  if (!/^\d{6}$/.test(value)) {
    return false;
  }

  const month = Number(value.slice(4, 6));
  return month >= 1 && month <= 12;
}

function getMonthCount(start: string, end: string) {
  if (!isValidMesAno(start) || !isValidMesAno(end) || start > end) {
    return 0;
  }

  const startYear = Number(start.slice(0, 4));
  const startMonth = Number(start.slice(4, 6));
  const endYear = Number(end.slice(0, 4));
  const endMonth = Number(end.slice(4, 6));

  return (endYear - startYear) * 12 + (endMonth - startMonth) + 1;
}

function getSeedValidationMessage(mode: SeedMode, ano: string, start: string, end: string) {
  if (mode === "year") {
    if (!/^\d{4}$/.test(ano)) {
      return "Informe um ano com quatro dígitos para criar os agendamentos.";
    }

    return "";
  }

  if (!isValidMesAno(start)) {
    return "Informe um Mês/Ano inicial válido no formato YYYYMM.";
  }

  if (!isValidMesAno(end)) {
    return "Informe um Mês/Ano final válido no formato YYYYMM.";
  }

  if (start > end) {
    return "O Mês/Ano inicial não pode ser maior que o Mês/Ano final.";
  }

  return "";
}

export function JobsPage() {
  const [status, setStatus] = useState("");
  const [filterEstadoId, setFilterEstadoId] = useState("");
  const [isSeedModalOpen, setIsSeedModalOpen] = useState(false);
  const [seedNotice, setSeedNotice] = useState<SeedNotice | null>(null);
  const [seedResource, setSeedResource] = useState<SeedResource>(
    "bolsa-familia-por-municipio",
  );
  const [seedEstadoId, setSeedEstadoId] = useState("");
  const [seedMode, setSeedMode] = useState<SeedMode>("year");
  const [seedYear, setSeedYear] = useState("");
  const [seedStart, setSeedStart] = useState("");
  const [seedEnd, setSeedEnd] = useState("");
  const [jobCodePrefix, setJobCodePrefix] = useState("");
  const [descricaoPrefix, setDescricaoPrefix] = useState("");
  const queryClient = useQueryClient();

  const estadosQuery = useQuery({
    queryKey: ["ibge", "estados"],
    queryFn: ({ signal }) => api.getEstados(signal),
  });

  const selectedFilterEstado = (estadosQuery.data ?? []).find(
    (estado) => String(estado.id_estado) === filterEstadoId,
  );
  const selectedSeedEstado = (estadosQuery.data ?? []).find(
    (estado) => String(estado.id_estado) === seedEstadoId,
  );
  const selectedSeedOption = getSeedOption(seedResource);
  const seedValidationMessage = getSeedValidationMessage(
    seedMode,
    seedYear,
    seedStart,
    seedEnd,
  );
  const plannedJobs = seedMode === "year" ? 12 : getMonthCount(seedStart, seedEnd);
  const shouldShowSeedValidation =
    seedMode === "year" ? seedYear.length > 0 : seedStart.length > 0 || seedEnd.length > 0;

  useEffect(() => {
    if (seedEstadoId || !estadosQuery.data || estadosQuery.data.length === 0) {
      return;
    }

    const defaultEstado =
      estadosQuery.data.find((estado) => estado.sigla === "PR") ?? estadosQuery.data[0];

    if (defaultEstado) {
      setSeedEstadoId(String(defaultEstado.id_estado));
    }
  }, [seedEstadoId, estadosQuery.data]);

  const jobsQuery = useQuery({
    queryKey: ["jobs", status, selectedFilterEstado?.sigla ?? ""],
    queryFn: ({ signal }) =>
      api.getJobs(
        {
          status: status || undefined,
          estadoSigla: selectedFilterEstado?.sigla || undefined,
          limit: 100,
          offset: 0,
        },
        signal,
      ),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return items.some((job) => activeStatuses.has(job.status)) ? 4_000 : false;
    },
  });

  const seedJobsMutation = useMutation({
    mutationFn: (payload: JobSeedRequest) => api.seedBeneficioJobs(payload),
    onSuccess: async (data, variables) => {
      const option = getSeedOption(variables.resource);
      setSeedNotice({
        createdCount: data.created_count,
        existingCount: data.existing_count,
        label: option.label,
        estadoSigla: variables.estadoSigla,
      });
      setIsSeedModalOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const canSubmit =
    Boolean(selectedSeedEstado) &&
    seedValidationMessage === "" &&
    !seedJobsMutation.isPending;

  const runJobMutation = useMutation({
    mutationFn: (jobId: number) => api.runJob(jobId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const refreshJobMutation = useMutation({
    mutationFn: (jobId: number) => api.getJob(jobId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const resetPendingMutation = useMutation({
    mutationFn: (jobId: number) => api.resetJobToPending(jobId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const jobs = jobsQuery.data?.items ?? [];
  const total = jobsQuery.data?.total ?? 0;
  const completedCount = jobs.filter((job) => job.status === "completed").length;
  const activeCount = jobs.filter((job) => activeStatuses.has(job.status)).length;
  const failedCount = jobs.filter((job) =>
    ["failed", "completed_with_errors"].includes(job.status),
  ).length;

  function handleResetSeedForm() {
    const defaultEstado =
      (estadosQuery.data ?? []).find((estado) => estado.sigla === "PR") ??
      (estadosQuery.data ?? [])[0];

    setSeedResource("bolsa-familia-por-municipio");
    setSeedMode("year");
    setSeedYear("");
    setSeedStart("");
    setSeedEnd("");
    setJobCodePrefix("");
    setDescricaoPrefix("");
    setSeedEstadoId(defaultEstado ? String(defaultEstado.id_estado) : "");
    seedJobsMutation.reset();
  }

  function handleOpenSeedModal() {
    handleResetSeedForm();
    setIsSeedModalOpen(true);
  }

  function handleCloseSeedModal() {
    if (seedJobsMutation.isPending) {
      return;
    }

    setIsSeedModalOpen(false);
    seedJobsMutation.reset();
  }

  function handleBackdropClick() {
    handleCloseSeedModal();
  }

  function handleModalClick(event: MouseEvent<HTMLDivElement>) {
    event.stopPropagation();
  }

  function handleSeedSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedSeedEstado || seedValidationMessage) {
      return;
    }

    seedJobsMutation.reset();

    seedJobsMutation.mutate({
      estadoSigla: selectedSeedEstado.sigla,
      resource: selectedSeedOption.resource,
      tipoBeneficio: selectedSeedOption.tipoBeneficio,
      ano: seedMode === "year" ? Number(seedYear) : null,
      mesAnoInicio: seedMode === "range" ? seedStart : null,
      mesAnoFim: seedMode === "range" ? seedEnd : null,
      jobCodePrefix: jobCodePrefix.trim() || undefined,
      descricaoPrefix: descricaoPrefix.trim() || undefined,
    });
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operação"
        title="Agendamentos de coleta"
        description="Acompanhe a fila operacional, crie novos lotes de coleta e dispare reprocessamentos de forma controlada."
        actions={
          <button
            type="button"
            className="button button-primary"
            onClick={handleOpenSeedModal}
          >
            Novo agendamento
          </button>
        }
      />

      <section className="stats-grid">
        <article className="stat-card accent-copper">
          <span>Total carregado</span>
          <strong>{formatInteger(total)}</strong>
          <small>lista atual com filtro aplicado</small>
        </article>
        <article className="stat-card accent-teal">
          <span>Concluídos</span>
          <strong>{formatInteger(completedCount)}</strong>
          <small>agendamentos fechados sem pendência</small>
        </article>
        <article className="stat-card accent-amber">
          <span>Ativos</span>
          <strong>{formatInteger(activeCount)}</strong>
          <small>queued ou running com polling automático</small>
        </article>
        <article className="stat-card accent-crimson">
          <span>Com falha</span>
          <strong>{formatInteger(failedCount)}</strong>
          <small>falhos ou concluídos com erro</small>
        </article>
      </section>

      {seedNotice ? (
        <div className="notice-banner notice-banner-success" role="status">
          <strong>{seedNotice.label}</strong> em <strong>{seedNotice.estadoSigla}</strong>:{" "}
          {formatInteger(seedNotice.createdCount)} agendamentos criados e{" "}
          {formatInteger(seedNotice.existingCount)} já existentes.
        </div>
      ) : null}

      <Panel title="Filtros" description="Refine a visão operacional antes de acionar um lote.">
        <div className="filter-grid">
          <label className="field">
            <span>Status</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Todos</option>
              <option value="pending">pending</option>
              <option value="queued">queued</option>
              <option value="running">running</option>
              <option value="completed">completed</option>
              <option value="completed_with_errors">completed_with_errors</option>
              <option value="failed">failed</option>
            </select>
          </label>

          <label className="field">
            <span>UF</span>
            <select
              value={filterEstadoId}
              onChange={(event) => setFilterEstadoId(event.target.value)}
            >
              <option value="">Todos</option>
              {(estadosQuery.data ?? []).map((estado) => (
                <option key={estado.id_estado} value={estado.id_estado}>
                  {estado.sigla} · {estado.nome}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <Panel
        title="Lista de agendamentos"
        description="Ações de execução só devem ser usadas quando o lote estiver pronto para processamento ou reprocessamento."
      >
        {jobsQuery.isLoading ? <p className="feedback">Carregando agendamentos...</p> : null}
        {jobsQuery.isError ? (
          <p className="feedback feedback-error">
            {(jobsQuery.error as ApiError).detail}
          </p>
        ) : null}
        {runJobMutation.isError ? (
          <p className="feedback feedback-error">
            {(runJobMutation.error as ApiError).detail}
          </p>
        ) : null}
        {refreshJobMutation.isError ? (
          <p className="feedback feedback-error">
            {(refreshJobMutation.error as ApiError).detail}
          </p>
        ) : null}
        {resetPendingMutation.isError ? (
          <p className="feedback feedback-error">
            {(resetPendingMutation.error as ApiError).detail}
          </p>
        ) : null}

        {!jobsQuery.isLoading && jobs.length === 0 ? (
          <EmptyState
            title="Nenhum agendamento encontrado"
            description="Ajuste os filtros ou use o botão de criação para abrir um novo lote."
          />
        ) : null}

        {jobs.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agendamento</th>
                  <th>Período</th>
                  <th>Status</th>
                  <th>Progresso</th>
                  <th>Atualização</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  const totalItems = job.total_items || 0;
                  const processedItems =
                    job.success_items + job.failed_items + job.running_items;
                  const ratio = totalItems > 0 ? processedItems / totalItems : 0;
                  const estado = String(job.metadata_json.estado_sigla ?? "—");
                  const start = String(job.metadata_json.mes_ano_inicio ?? "—");
                  const end = String(job.metadata_json.mes_ano_fim ?? "—");
                  const hasExecutionHistory =
                    activeStatuses.has(job.status) ||
                    job.started_at !== null ||
                    job.finished_at !== null;
                  const canResetToPending = resettableStatuses.has(job.status);
                  const isRunningAction =
                    (runJobMutation.isPending && runJobMutation.variables === job.id) ||
                    (refreshJobMutation.isPending &&
                      refreshJobMutation.variables === job.id);
                  const actionLabel = hasExecutionHistory
                    ? isRunningAction
                      ? "Consultando..."
                      : "Atualizar progresso"
                    : isRunningAction
                      ? "Enfileirando..."
                      : "Executar";

                  return (
                    <tr key={job.id}>
                      <td data-label="Agendamento">
                        <div className="cell-title">
                          <strong>{job.job_code}</strong>
                          <span>{job.descricao}</span>
                          <small>{estado}</small>
                        </div>
                      </td>
                      <td data-label="Período">
                        {start}
                        {start !== end ? ` até ${end}` : ""}
                      </td>
                      <td data-label="Status">
                        <StatusBadge status={job.status} />
                      </td>
                      <td data-label="Progresso">
                        <div className="progress-copy">
                          <strong>{formatPercent(ratio)}</strong>
                          <span>
                            {formatInteger(job.success_items)} sucesso /{" "}
                            {formatInteger(job.failed_items)} falha /{" "}
                            {formatInteger(job.pending_items)} pendente
                          </span>
                        </div>
                      </td>
                      <td data-label="Atualização">
                        <div className="cell-title">
                          <strong>{formatDateTime(job.updated_at)}</strong>
                          <span>início {formatDateTime(job.started_at)}</span>
                          <span>fim {formatDateTime(job.finished_at)}</span>
                        </div>
                      </td>
                      <td data-label="Ação" className="actions-cell">
                        <div className="actions-stack">
                          <button
                            type="button"
                            className="button button-secondary"
                            disabled={
                              runJobMutation.isPending ||
                              refreshJobMutation.isPending ||
                              resetPendingMutation.isPending
                            }
                            onClick={() =>
                              hasExecutionHistory
                                ? refreshJobMutation.mutate(job.id)
                                : runJobMutation.mutate(job.id)
                            }
                          >
                            {actionLabel}
                          </button>
                          {canResetToPending ? (
                            <button
                              type="button"
                              className="button button-secondary"
                              disabled={
                                runJobMutation.isPending ||
                                refreshJobMutation.isPending ||
                                resetPendingMutation.isPending
                              }
                              onClick={() => resetPendingMutation.mutate(job.id)}
                            >
                              {resetPendingMutation.isPending &&
                              resetPendingMutation.variables === job.id
                                ? "Voltando..."
                                : "Voltar para pending"}
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>

      {isSeedModalOpen ? (
        <div className="modal-backdrop" onClick={handleBackdropClick}>
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="seed-modal-title"
            onClick={handleModalClick}
          >
            <div className="modal-header">
              <div className="modal-title-group">
                <p className="eyebrow">Criação</p>
                <h3 id="seed-modal-title">Novo agendamento</h3>
                <p>Defina benefício, UF e período da carga.</p>
              </div>
              <button
                type="button"
                className="button button-ghost"
                onClick={handleCloseSeedModal}
                disabled={seedJobsMutation.isPending}
                aria-label="Fechar criação de agendamento"
              >
                Fechar
              </button>
            </div>

            {estadosQuery.isLoading ? (
              <p className="feedback">Carregando estados para criação...</p>
            ) : null}
            {estadosQuery.isError ? (
              <p className="feedback feedback-error">
                {(estadosQuery.error as ApiError).detail}
              </p>
            ) : null}
            {seedJobsMutation.isError ? (
              <p className="feedback feedback-error">
                {(seedJobsMutation.error as ApiError).detail}
              </p>
            ) : null}

            <form className="form-stack" onSubmit={handleSeedSubmit}>
              <div className="filter-grid filter-grid-wide">
                <label className="field">
                  <span>Benefício</span>
                  <select
                    value={seedResource}
                    onChange={(event) =>
                      setSeedResource(event.target.value as SeedResource)
                    }
                  >
                    {seedOptions.map((option) => (
                      <option key={option.resource} value={option.resource}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>UF</span>
                  <select
                    value={seedEstadoId}
                    onChange={(event) => setSeedEstadoId(event.target.value)}
                    disabled={estadosQuery.isLoading}
                  >
                    <option value="">Selecione</option>
                    {(estadosQuery.data ?? []).map((estado) => (
                      <option key={estado.id_estado} value={estado.id_estado}>
                        {estado.sigla} · {estado.nome}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Modo do período</span>
                  <select
                    value={seedMode}
                    onChange={(event) => setSeedMode(event.target.value as SeedMode)}
                  >
                    <option value="year">Ano fechado</option>
                    <option value="range">Intervalo Mês/Ano</option>
                  </select>
                </label>
              </div>

              <div className="seed-preview">
                <div className="seed-preview-copy">
                  <strong>{selectedSeedOption.label}</strong>
                  <span>
                    {selectedSeedEstado
                      ? `${selectedSeedEstado.sigla} · ${selectedSeedEstado.nome}`
                      : "Selecione uma UF para o seed"}
                  </span>
                </div>
                <small>
                  {seedMode === "year"
                    ? "Serão gerados 12 agendamentos mensais para o ano informado."
                    : plannedJobs > 0
                      ? `${formatInteger(plannedJobs)} agendamentos mensais previstos para o intervalo.`
                      : "Informe um intervalo válido."}
                </small>
              </div>

              {seedMode === "year" ? (
                <div className="filter-grid">
                  <label className="field">
                    <span>Ano</span>
                    <input
                      type="text"
                      value={seedYear}
                      onChange={(event) =>
                        setSeedYear(event.target.value.replace(/\D/g, "").slice(0, 4))
                      }
                      placeholder="2024"
                      inputMode="numeric"
                    />
                  </label>

                  <label className="field">
                    <span>Cobertura esperada</span>
                    <input type="text" value={selectedSeedOption.range} readOnly />
                  </label>
                </div>
              ) : (
                <div className="filter-grid">
                  <label className="field">
                    <span>Mês/Ano inicial</span>
                    <input
                      type="text"
                      value={seedStart}
                      onChange={(event) =>
                        setSeedStart(event.target.value.replace(/\D/g, "").slice(0, 6))
                      }
                      placeholder="202303"
                      inputMode="numeric"
                    />
                  </label>

                  <label className="field">
                    <span>Mês/Ano final</span>
                    <input
                      type="text"
                      value={seedEnd}
                      onChange={(event) =>
                        setSeedEnd(event.target.value.replace(/\D/g, "").slice(0, 6))
                      }
                      placeholder="202312"
                      inputMode="numeric"
                    />
                  </label>
                </div>
              )}

              <div className="filter-grid">
                <label className="field">
                  <span>Prefixo de job code</span>
                  <input
                    type="text"
                    value={jobCodePrefix}
                    onChange={(event) => setJobCodePrefix(event.target.value)}
                    placeholder="Opcional"
                  />
                </label>

                <label className="field">
                  <span>Prefixo de descrição</span>
                  <input
                    type="text"
                    value={descricaoPrefix}
                    onChange={(event) => setDescricaoPrefix(event.target.value)}
                    placeholder="Opcional"
                  />
                </label>
              </div>

              {shouldShowSeedValidation && seedValidationMessage ? (
                <p className="feedback feedback-error seed-feedback">
                  {seedValidationMessage}
                </p>
              ) : null}

              <div className="panel-actions">
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={!canSubmit || estadosQuery.isLoading}
                >
                  {seedJobsMutation.isPending
                    ? "Criando agendamentos..."
                    : "Criar agendamentos"}
                </button>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={handleResetSeedForm}
                  disabled={seedJobsMutation.isPending}
                >
                  Limpar
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
