import type { Project, Task, TaskStatus, VersionConflict, Workspace } from "./types";

const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null) return fallback;
  if ("message" in body && typeof body.message === "string") return body.message;
  if ("detail" in body && typeof body.detail === "string") return body.detail;
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  const body = await response.json().catch(() => undefined);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(body, `Error HTTP ${response.status}`), body);
  }
  return body as T;
}

export const api = {
  register(email: string, password: string, workspaceName: string) {
    return request<{ user_id: string; workspace: Workspace }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, workspace_name: workspaceName }),
    });
  },
  login(email: string, password: string) {
    return request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  workspaces(token: string) {
    return request<Workspace[]>("/workspaces", {}, token);
  },
  projects(token: string, workspaceId: string) {
    return request<Project[]>(`/workspaces/${workspaceId}/projects`, {}, token);
  },
  createProject(token: string, workspaceId: string, name: string) {
    return request<Project>(
      `/workspaces/${workspaceId}/projects`,
      { method: "POST", body: JSON.stringify({ name }) },
      token,
    );
  },
  tasks(token: string, projectId: string) {
    return request<Task[]>(`/projects/${projectId}/tasks`, {}, token);
  },
  createTask(
    token: string,
    projectId: string,
    input: { title: string; description: string | null; status: TaskStatus },
  ) {
    return request<Task>(
      `/projects/${projectId}/tasks`,
      { method: "POST", body: JSON.stringify(input) },
      token,
    );
  },
  updateTask(
    token: string,
    projectId: string,
    taskId: string,
    input: { title: string; description: string | null; status: TaskStatus; version: number },
  ) {
    return request<Task>(
      `/projects/${projectId}/tasks/${taskId}`,
      { method: "PATCH", body: JSON.stringify(input) },
      token,
    );
  },
};

export function isVersionConflict(error: unknown): error is ApiError & { body: VersionConflict } {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    typeof error.body === "object" &&
    error.body !== null &&
    "code" in error.body &&
    error.body.code === "task_version_conflict"
  );
}
