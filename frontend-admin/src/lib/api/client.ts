import type {
  BeneficioRecord,
  Estado,
  JobSeedRequest,
  JobSeedResponse,
  Job,
  Municipio,
  PaginatedResponse,
  Regiao,
} from "./types";

type QueryValue = string | number | boolean | null | undefined;

type RequestOptions = {
  method?: "GET" | "POST";
  params?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

type FastApiValidationDetail = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function formatValidationDetail(detail: FastApiValidationDetail) {
  const location =
    Array.isArray(detail.loc) && detail.loc.length > 0
      ? detail.loc
          .map((item) => String(item))
          .filter((item) => item !== "query" && item !== "body" && item !== "path")
          .join(" > ")
      : "";

  if (location && detail.msg) {
    return `${location}: ${detail.msg}`;
  }

  if (detail.msg) {
    return detail.msg;
  }

  return "Erro de validação na requisição.";
}

function normalizeApiDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (isRecord(item)) {
          return formatValidationDetail(item as FastApiValidationDetail);
        }

        return String(item);
      })
      .filter((message) => message.trim().length > 0);

    if (messages.length > 0) {
      return messages.join(" | ");
    }
  }

  if (isRecord(detail)) {
    return formatValidationDetail(detail as FastApiValidationDetail);
  }

  return "Erro inesperado ao comunicar com a API.";
}

function buildUrl(path: string, params?: Record<string, QueryValue>) {
  const url = new URL(`/api/v1${path}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") {
        return;
      }

      url.searchParams.set(key, String(value));
    });
  }

  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}) {
  const response = await fetch(buildUrl(path, options.params), {
    method: options.method ?? "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!response.ok) {
    let detail = "Erro inesperado ao comunicar com a API.";

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if ("detail" in payload) {
        detail = normalizeApiDetail(payload.detail);
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export const api = {
  getRegioes(signal?: AbortSignal) {
    return request<Regiao[]>("/ibge/regioes", { signal });
  },
  getEstados(signal?: AbortSignal) {
    return request<Estado[]>("/ibge/estados", { signal });
  },
  getEstadoMunicipios(
    idEstado: number,
    params?: { nome?: string; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) {
    return request<PaginatedResponse<Municipio>>(
      `/ibge/estados/${idEstado}/municipios`,
      {
        params,
        signal,
      },
    );
  },
  getJobs(
    params?: {
      status?: string;
      estadoSigla?: string;
      limit?: number;
      offset?: number;
    },
    signal?: AbortSignal,
  ) {
    return request<PaginatedResponse<Job>>("/transparencia/jobs", {
      params,
      signal,
    });
  },
  getJob(jobId: number, signal?: AbortSignal) {
    return request<Job>(`/transparencia/jobs/${jobId}`, {
      signal,
    });
  },
  runJob(jobId: number) {
    return request<Job>(`/transparencia/jobs/${jobId}/run`, {
      method: "POST",
    });
  },
  resetJobToPending(jobId: number) {
    return request<Job>(`/transparencia/jobs/${jobId}/reset-pending`, {
      method: "POST",
    });
  },
  seedBeneficioJobs(payload: JobSeedRequest) {
    return request<JobSeedResponse>("/transparencia/jobs/beneficios/seed", {
      method: "POST",
      body: payload,
    });
  },
  getBeneficios(
    resource: "bolsa-familia" | "auxilio-brasil" | "novo-bolsa-familia",
    params?: {
      estadoSigla?: string;
      mesAno?: string;
      codigoIbge?: string;
      limit?: number;
      offset?: number;
    },
    signal?: AbortSignal,
  ) {
    return request<PaginatedResponse<BeneficioRecord>>(
      `/transparencia/beneficios/${resource}`,
      {
        params,
        signal,
      },
    );
  },
};
