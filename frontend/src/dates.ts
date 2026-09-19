const limaDateTime = new Intl.DateTimeFormat("es-PE", {
  timeZone: "America/Lima",
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatLimaDateTime(utcValue: string): string {
  const instant = new Date(utcValue);
  if (Number.isNaN(instant.getTime())) return "Fecha no disponible";
  return limaDateTime.format(instant);
}
