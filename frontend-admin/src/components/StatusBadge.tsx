type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = `status-badge status-${status.replaceAll("_", "-")}`;

  return <span className={tone}>{status}</span>;
}
