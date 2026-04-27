import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { api, ApiError } from "../lib/api/client";
import { formatInteger } from "../lib/format";

export function IbgePage() {
  const [selectedRegion, setSelectedRegion] = useState("");
  const [selectedState, setSelectedState] = useState("");
  const [municipioNome, setMunicipioNome] = useState("");

  const regioesQuery = useQuery({
    queryKey: ["ibge", "regioes"],
    queryFn: ({ signal }) => api.getRegioes(signal),
  });

  const estadosQuery = useQuery({
    queryKey: ["ibge", "estados"],
    queryFn: ({ signal }) => api.getEstados(signal),
  });

  const municipiosQuery = useQuery({
    queryKey: ["ibge", "municipios", selectedState, municipioNome],
    queryFn: ({ signal }) =>
      api.getEstadoMunicipios(
        Number(selectedState),
        {
          nome: municipioNome || undefined,
          limit: 1000,
          offset: 0,
        },
        signal,
      ),
    enabled: Boolean(selectedState),
  });

  const filteredStates = (estadosQuery.data ?? []).filter((estado) => {
    if (!selectedRegion) {
      return true;
    }

    return String(estado.regiao.id_regiao) === selectedRegion;
  });

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Referência geográfica"
        title="Malha IBGE"
        description="Navegue por região, estado e município para alimentar filtros das outras telas e validar cobertura de carga."
      />

      <section className="stats-grid">
        <article className="stat-card accent-copper">
          <span>Regioes</span>
          <strong>{formatInteger(regioesQuery.data?.length ?? 0)}</strong>
          <small>hierarquia de entrada</small>
        </article>
        <article className="stat-card accent-teal">
          <span>Estados</span>
          <strong>{formatInteger(filteredStates.length)}</strong>
          <small>após filtro de região</small>
        </article>
        <article className="stat-card accent-amber">
          <span>Municípios</span>
          <strong>{formatInteger(municipiosQuery.data?.total ?? 0)}</strong>
          <small>do estado selecionado</small>
        </article>
      </section>

      <Panel title="Explorador geográfico" description="Selecione a região e depois um estado para carregar os municípios vinculados.">
        <div className="filter-grid filter-grid-wide">
          <label className="field">
            <span>Região</span>
            <select
              value={selectedRegion}
              onChange={(event) => {
                setSelectedRegion(event.target.value);
                setSelectedState("");
              }}
            >
              <option value="">Todas</option>
              {(regioesQuery.data ?? []).map((regiao) => (
                <option key={regiao.id_regiao} value={regiao.id_regiao}>
                  {regiao.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Estado</span>
            <select
              value={selectedState}
              onChange={(event) => setSelectedState(event.target.value)}
            >
              <option value="">Selecione</option>
              {filteredStates.map((estado) => (
                <option key={estado.id_estado} value={estado.id_estado}>
                  {estado.sigla} · {estado.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Busca de município</span>
            <input
              type="text"
              value={municipioNome}
              onChange={(event) => setMunicipioNome(event.target.value)}
              placeholder="Nome parcial"
              disabled={!selectedState}
            />
          </label>
        </div>
      </Panel>

      <div className="split-layout">
        <Panel title="Estados disponíveis" description="Seleção rápida com região vinculada.">
          {estadosQuery.isLoading ? <p className="feedback">Carregando estados...</p> : null}
          {estadosQuery.isError ? (
            <p className="feedback feedback-error">
              {(estadosQuery.error as ApiError).detail}
            </p>
          ) : null}

          <div className="state-list">
            {filteredStates.map((estado) => (
              <button
                key={estado.id_estado}
                type="button"
                className={
                  String(estado.id_estado) === selectedState
                    ? "state-chip state-chip-active"
                    : "state-chip"
                }
                onClick={() => setSelectedState(String(estado.id_estado))}
              >
                <strong>{estado.sigla}</strong>
                <span>{estado.nome}</span>
                <small>{estado.regiao.nome}</small>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title="Municípios" description="Base para filtros de código IBGE nas telas de benefício e agendamentos de coleta.">
          {selectedState === "" ? (
            <EmptyState
              title="Escolha um estado"
              description="A lista de municípios é carregada somente após a seleção de um estado."
            />
          ) : null}
          {municipiosQuery.isLoading ? (
            <p className="feedback">Carregando municípios...</p>
          ) : null}
          {municipiosQuery.isError ? (
            <p className="feedback feedback-error">
              {(municipiosQuery.error as ApiError).detail}
            </p>
          ) : null}

          {selectedState !== "" && (municipiosQuery.data?.items.length ?? 0) > 0 ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Município</th>
                    <th>Código IBGE</th>
                    <th>UF</th>
                    <th>Região</th>
                  </tr>
                </thead>
                <tbody>
                  {(municipiosQuery.data?.items ?? []).map((municipio) => (
                    <tr key={municipio.id_municipio}>
                      <td data-label="Município">{municipio.nome}</td>
                      <td data-label="Código IBGE">{municipio.id_municipio}</td>
                      <td data-label="UF">{municipio.estado.sigla}</td>
                      <td data-label="Região">
                        {
                          filteredStates.find(
                            (estado) => estado.id_estado === municipio.id_estado,
                          )?.regiao.nome
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
