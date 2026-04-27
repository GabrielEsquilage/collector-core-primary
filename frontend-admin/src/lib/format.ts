export function formatDateTime(value: string | null) {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
  }).format(new Date(value));
}

export function formatInteger(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value);
}

export function formatCurrency(value: string | number) {
  const numeric =
    typeof value === "number" ? value : Number.parseFloat(value || "0");

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number.isNaN(numeric) ? 0 : numeric);
}

export function formatPercent(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}
