import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import App from "./App";

afterEach(() => vi.restoreAllMocks());

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

it("registers, logs in, and opens the empty workspace", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => response({ user_id: "user", workspace: { id: "space", name: "Alpha", role: "owner" } }, 201))
    .mockImplementationOnce(() => response({ access_token: "token", token_type: "bearer" }))
    .mockImplementationOnce(() => response([{ id: "space", name: "Alpha", role: "owner" }]))
    .mockImplementationOnce(() => response([]));

  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /crea una cuenta/i }));
  await user.type(screen.getByLabelText(/nombre del espacio/i), "Alpha");
  await user.type(screen.getByLabelText(/correo electrónico/i), "owner@example.com");
  await user.type(screen.getByLabelText(/^contraseña/i), "correct-horse-battery-staple");
  await user.click(screen.getByRole("button", { name: "Crear cuenta" }));

  expect(await screen.findByText("Crea tu primer proyecto")).toBeInTheDocument();
  expect(sessionStorage.getItem("workboard.access_token")).toBe("token");
  expect(fetchMock).toHaveBeenCalledTimes(4);
});

it("clears an invalid stored session", async () => {
  sessionStorage.setItem("workboard.access_token", "expired");
  vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => response({ detail: "Invalid credentials" }, 401));
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Entra a tu espacio" })).toBeInTheDocument();
  expect(sessionStorage.getItem("workboard.access_token")).toBeNull();
});

it("does not show mutation controls to a viewer", async () => {
  sessionStorage.setItem("workboard.access_token", "viewer-token");
  vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => response([{ id: "space", name: "Alpha", role: "viewer" }]))
    .mockImplementationOnce(() => response([{ id: "project", workspace_id: "space", name: "Read only", created_at: "2026-01-01" }]))
    .mockImplementationOnce(() => response([{ id: "task", project_id: "project", created_by_id: "owner", title: "Visible task", description: null, status: "todo", version: 1, created_at: "2026-01-01", updated_at: "2026-01-01" }]))
    .mockImplementationOnce(() => response([{ id: "task", project_id: "project", created_by_id: "owner", title: "Visible task", description: null, status: "todo", version: 1, created_at: "2026-01-01", updated_at: "2026-01-01" }]));

  render(<App />);
  expect(await screen.findByText("Visible task")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /añadir tarea/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Entra a tu espacio" })).toBeInTheDocument());
});
