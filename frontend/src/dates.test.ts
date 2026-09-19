import { expect, it } from "vitest";

import { formatLimaDateTime } from "./dates";

it("renders UTC instants in the America/Lima timezone", () => {
  const rendered = formatLimaDateTime("2026-01-15T15:30:00Z");
  expect(rendered).toContain("10:30");
});

it("does not render an invalid date", () => {
  expect(formatLimaDateTime("not-a-date")).toBe("Fecha no disponible");
});
