import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { api, ApiError } from "../lib/api/client";
import { formatCurrency, formatDate, formatDateTime, formatInteger } from "../lib/format";

const pageSizeOptions = [50, 100, 250];

const benefitOptions = [
  {
    key: "bolsa-familia" as const,
    label: "Bolsa Família",
    range: "201301 até 202110",
  },
  {
    key: "auxilio-brasil" as const,
    label: "Auxílio Brasil",
    range: "202111 até 202302",
  },
  {
    key: "novo-bolsa-familia" as const,
    label: "Novo Bolsa Família",
    range: "202303 em diante",
  },
];

function getMunicipioNome(payload: Record<string, unknown>) {
  const municipio = payload.municipio;
  if (typeof municipio === "object" && municipio !== null) {
    const nome = (municipio as { nomeIBGE?: unknown }).nomeIBGE;
    if (typeof nome === "string" && nome.length > 0) {
      return nome;
    }
  }

  return "Município não identificado";
}

export function BeneficiosPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
  const [resource, setResource] =
    useState<"bolsa-familia" | "auxilio-brasil" | "novo-bolsa-familia">(
      "bolsa-familia",
    );
  const [estadoId, setEstadoId] = useState("");
  const [municipioCodigo, setMunicipioCodigo] = useState("");
  const [mesAno, setMesAno] = useState("");

  const estadosQuery = useQuery({
    queryKey: ["ibge", "estados"],
    queryFn: ({ signal }) => api.getEstados(signal),
  });

  const municipiosQuery = useQuery({
    queryKey: ["ibge", "estado-municipios", estadoId],
    queryFn: ({ signal }) =>
      api.getEstadoMunicipios(Number(estadoId), { limit: 1000, offset: 0 }, signal),
    enabled: Boolean(estadoId),
  });

  const selectedEstado = (estadosQuery.data ?? []).find(
    (estado) => String(estado.id_estado) === estadoId,
  );

  useEffect(() => {
    setMunicipioCodigo("");
  }, [estadoId]);

  useEffect(() => {
    setPage(1);
  }, [resource, estadoId, municipioCodigo, mesAno, pageSize]);

  const beneficiosQuery = useQuery({
    queryKey: [
      "beneficios",
      resource,
      selectedEstado?.sigla ?? "",
      municipioCodigo,
      mesAno,
      page,
      pageSize,
    ],
    queryFn: ({ signal }) =>
      api.getBeneficios(
        resource,
        {
          estadoSigla: selectedEstado?.sigla || undefined,
          codigoIbge: municipioCodigo || undefined,
          mesAno: mesAno || undefined,
          limit: pageSize,
          offset: (page - 1) * pageSize,
        },
        signal,
      ),
    placeholderData: (previousData) => previousData,
  });

  const rows = beneficiosQuery.data?.items ?? [];
  const total = beneficiosQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = total === 0 ? 0 : Math.min((page - 1) * pageSize + rows.length, total);
  const totalBeneficiados = rows.reduce(
    (accumulator, row) => accumulator + row.quantidade_beneficiados,
    0,
  );
  const mediaBeneficiados = rows.length === 0 ? 0 : totalBeneficiados / rows.length;
  const mediaBeneficiadosTruncada = Math.trunc(mediaBeneficiados);
  const totalValor = rows.reduce(
    (accumulator, row) => {
      const parsed = Number.parseFloat(row.valor);
      return accumulator + (Number.isNaN(parsed) ? 0 : parsed);
    },
    0,
  );
  const currentBenefit = benefitOptions.find((option) => option.key === resource);

  useEffect(() => {
    if (beneficiosQuery.data && page > totalPages) {
      setPage(totalPages);
    }
  }, [beneficiosQuery.data, page, totalPages]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Validação"
        title="Benefícios por município"
        description="Compare a persistência local com o período correto de cada base e filtre a coleta pela malha do IBGE."
      />

      <Panel
        title="Faixas de cobertura"
        description="A regra de negócio muda por período. Use a aba adequada para validar o dataset correto."
      >
        <div className="segmented-control" role="tablist" aria-label="Tipos de benefício">
          {benefitOptions.map((option) => (
            <button
              key={option.key}
              type="button"
              role="tab"
              aria-selected={resource === option.key}
              className={
                resource === option.key
                  ? "segment-button segment-button-active"
                  : "segment-button"
              }
              onClick={() => setResource(option.key)}
            >
              <span>{option.label}</span>
              <small>{option.range}</small>
            </button>
          ))}
        </div>
      </Panel>

      <section className="stats-grid">
        <article className="stat-card accent-teal">
          <span>Registros totais</span>
          <strong>{formatInteger(total)}</strong>
          <small>{currentBenefit?.label}</small>
        </article>
        <article className="stat-card accent-copper">
          <span>Valor listado</span>
          <strong>{formatCurrency(totalValor)}</strong>
          <small>somatório dos itens visíveis</small>
        </article>
        <article className="stat-card accent-amber">
          <span>Média de beneficiados</span>
          <strong>{formatInteger(mediaBeneficiadosTruncada)}</strong>
          <small>média dos itens visíveis</small>
        </article>
      </section>

      <Panel title="Filtros" description="Use a base do IBGE para evitar digitação manual de código.">
        <div className="filter-grid filter-grid-wide">
          <label className="field">
            <span>Estado</span>
            <select value={estadoId} onChange={(event) => setEstadoId(event.target.value)}>
              <option value="">Todos</option>
              {(estadosQuery.data ?? []).map((estado) => (
                <option key={estado.id_estado} value={estado.id_estado}>
                  {estado.sigla} · {estado.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Município</span>
            <select
              value={municipioCodigo}
              onChange={(event) => setMunicipioCodigo(event.target.value)}
              disabled={!estadoId || municipiosQuery.isLoading}
            >
              <option value="">{estadoId ? "Todos" : "Selecione um estado"}</option>
              {(municipiosQuery.data?.items ?? []).map((municipio) => (
                <option key={municipio.id_municipio} value={municipio.id_municipio}>
                  {municipio.nome} · {municipio.id_municipio}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Mês/Ano</span>
            <input
              type="text"
              value={mesAno}
              onChange={(event) =>
                setMesAno(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              placeholder="202303"
              inputMode="numeric"
            />
          </label>
        </div>
      </Panel>

      <Panel
        title="Base persistida"
        description="Leitura interna do banco local. Nenhum desses filtros deve chamar a API externa."
      >
        {beneficiosQuery.isLoading ? (
          <p className="feedback">Carregando registros...</p>
        ) : null}
        {beneficiosQuery.isError ? (
          <p className="feedback feedback-error">
            {(beneficiosQuery.error as ApiError).detail}
          </p>
        ) : null}

        {!beneficiosQuery.isLoading && rows.length === 0 ? (
          <EmptyState
            title="Nenhum registro encontrado"
            description="Verifique se a coleta já foi executada para o período e município selecionados."
          />
        ) : null}

        {rows.length > 0 ? (
          <div className="result-stack">
            <div className="result-summary">
              <p>
                Exibindo <strong>{formatInteger(rangeStart)}</strong> a{" "}
                <strong>{formatInteger(rangeEnd)}</strong> de{" "}
                <strong>{formatInteger(total)}</strong> registros.
              </p>
              <label className="inline-field">
                <span>Itens por página</span>
                <select
                  value={pageSize}
                  onChange={(event) => setPageSize(Number(event.target.value))}
                >
                  {pageSizeOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Município</th>
                    <th>Referência</th>
                    <th>Valor</th>
                    <th>Beneficiados</th>
                    <th>Coletado em</th>
                    <th>Código IBGE</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.id}>
                      <td data-label="#">
                        <strong>{formatInteger(rangeStart + index)}</strong>
                      </td>
                      <td data-label="Município">
                        <div className="cell-title">
                          <strong>{getMunicipioNome(row.payload_json)}</strong>
                          <span>{row.tipo_beneficio}</span>
                        </div>
                      </td>
                      <td data-label="Referência">{formatDate(row.data_referencia)}</td>
                      <td data-label="Valor">{formatCurrency(row.valor)}</td>
                      <td data-label="Beneficiados">
                        {formatInteger(row.quantidade_beneficiados)}
                      </td>
                      <td data-label="Coletado em">{formatDateTime(row.collected_at)}</td>
                      <td data-label="Código IBGE">{row.municipio_codigo_ibge}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination-bar">
              <div className="pagination-meta">
                <span>
                  Página <strong>{formatInteger(page)}</strong> de{" "}
                  <strong>{formatInteger(totalPages)}</strong>
                </span>
              </div>

              <div className="pagination-actions">
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                  disabled={page === 1 || beneficiosQuery.isFetching}
                >
                  Anterior
                </button>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() =>
                    setPage((currentPage) => Math.min(totalPages, currentPage + 1))
                  }
                  disabled={page >= totalPages || beneficiosQuery.isFetching}
                >
                  Próxima
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
