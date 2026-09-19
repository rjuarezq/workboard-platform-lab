import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, isVersionConflict } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("adds the bearer token and serializes task versions", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "task", version: 3 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await api.updateTask("token", "project", "task", {
      title: "Release",
      description: null,
      status: "done",
      version: 2,
    });

    const [path, options] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/v1/projects/project/tasks/task");
    expect(new Headers(options?.headers).get("Authorization")).toBe("Bearer token");
    expect(JSON.parse(String(options?.body))).toMatchObject({ version: 2, status: "done" });
  });

  it("preserves the conflict contract", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        code: "task_version_conflict",
        message: "changed",
        current_version: 4,
      }), { status: 409, headers: { "Content-Type": "application/json" } }),
    );

    const error = await api.updateTask("token", "project", "task", {
      title: "Release",
      description: null,
      status: "todo",
      version: 3,
    }).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(isVersionConflict(error)).toBe(true);
    if (isVersionConflict(error)) expect(error.body.current_version).toBe(4);
  });
});
