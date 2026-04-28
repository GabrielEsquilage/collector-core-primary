export type PaginatedResponse<T> = {
  total: number;
  limit: number;
  offset: number;
  items: T[];
};

export type Regiao = {
  id_regiao: number;
  nome: string;
};

export type EstadoSummary = {
  id_estado: number;
  nome: string;
  sigla: string;
  id_regiao: number;
};

export type Estado = EstadoSummary & {
  regiao: Regiao;
};

export type Municipio = {
  id_municipio: number;
  nome: string;
  id_estado: number;
  estado: EstadoSummary;
};

export type Job = {
  id: number;
  job_code: string;
  descricao: string;
  tipo_carga: string;
  status: string;
  metadata_json: Record<string, unknown>;
  total_items: number;
  pending_items: number;
  running_items: number;
  success_items: number;
  failed_items: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type SeedResource =
  | "bolsa-familia-por-municipio"
  | "auxilio-brasil-por-municipio"
  | "novo-bolsa-familia-por-municipio";

export type SeedTipoBeneficio =
  | "bolsa_familia"
  | "auxilio_brasil"
  | "novo_bolsa_familia";

export type JobSeedRequest = {
  estadoSigla: string;
  resource: SeedResource;
  tipoBeneficio?: SeedTipoBeneficio | null;
  jobGranularity?: "estado_mes" | "municipio_mes";
  ano?: number | null;
  mesAnoInicio?: string | null;
  mesAnoFim?: string | null;
  municipioCodigosIbge?: string[] | null;
  jobCodePrefix?: string;
  descricaoPrefix?: string;
};

export type JobSeedResponse = {
  created_count: number;
  existing_count: number;
  jobs: Job[];
};

export type BeneficioRecord = {
  id: number;
  id_externo: number;
  tipo_beneficio: string;
  data_referencia: string;
  municipio_codigo_ibge: string;
  valor: string;
  quantidade_beneficiados: number;
  payload_json: Record<string, unknown>;
  collected_at: string;
};
