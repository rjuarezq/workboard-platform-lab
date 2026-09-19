import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, api, isVersionConflict } from "./api";
import { clearToken, readToken, saveToken } from "./session";
import type { Project, Task, TaskStatus, Workspace } from "./types";

const STATUS_META: Record<TaskStatus, { label: string; eyebrow: string }> = {
  todo: { label: "Por hacer", eyebrow: "Lista" },
  in_progress: { label: "En curso", eyebrow: "Ahora" },
  done: { label: "Completadas", eyebrow: "Hecho" },
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "La sesión venció. Inicia sesión nuevamente.";
    if (error.status === 403) return "Tu rol permite consultar, pero no modificar este recurso.";
    if (error.status === 404) return "El recurso ya no está disponible o no pertenece a tu espacio.";
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "No pudimos completar la operación.";
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email"));
    const password = String(data.get("password"));
    try {
      if (mode === "register") {
        await api.register(email, password, String(data.get("workspace")));
      }
      const session = await api.login(email, password);
      saveToken(session.access_token);
      onAuthenticated(session.access_token);
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="Presentación">
        <a className="brand brand-light" href="/" aria-label="Workboard, inicio">
          <span className="brand-mark">W</span>
          Workboard
        </a>
        <div>
          <p className="kicker">Trabajo claro, equipo alineado</p>
          <h1>De la idea al resultado, sin perder el hilo.</h1>
          <p className="story-copy">
            Organiza proyectos, prioriza el trabajo y mantén cada cambio bajo control.
          </p>
        </div>
        <p className="auth-footnote">Un laboratorio de plataforma diseñado como un producto real.</p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <p className="kicker">{mode === "login" ? "Bienvenido de vuelta" : "Empieza hoy"}</p>
          <h2>{mode === "login" ? "Entra a tu espacio" : "Crea tu espacio"}</h2>
          <p className="muted">
            {mode === "login"
              ? "Continúa donde tu equipo lo dejó."
              : "Tu primera cuenta será propietaria del espacio."}
          </p>

          <form onSubmit={submit} className="stack-form">
            {mode === "register" && (
              <label>
                Nombre del espacio
                <input name="workspace" required maxLength={120} autoComplete="organization" />
              </label>
            )}
            <label>
              Correo electrónico
              <input name="email" type="email" required autoComplete="email" />
            </label>
            <label>
              Contraseña
              <input
                name="password"
                type="password"
                required
                minLength={mode === "register" ? 12 : 1}
                maxLength={128}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
              {mode === "register" && <small>Mínimo 12 caracteres.</small>}
            </label>
            {error && <div className="notice notice-error" role="alert">{error}</div>}
            <button className="button button-primary" disabled={submitting}>
              {submitting ? "Procesando…" : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
            </button>
          </form>

          <button
            type="button"
            className="text-button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
          >
            {mode === "login" ? "¿Nuevo en Workboard? Crea una cuenta" : "¿Ya tienes cuenta? Inicia sesión"}
          </button>
        </div>
      </section>
    </main>
  );
}

interface TaskEditorProps {
  task?: Task;
  onClose: () => void;
  onSave: (input: { title: string; description: string | null; status: TaskStatus }) => Promise<void>;
}

function TaskEditor({ task, onClose, onSave }: TaskEditorProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await onSave({
        title: String(data.get("title")).trim(),
        description: String(data.get("description")).trim() || null,
        status: String(data.get("status")) as TaskStatus,
      });
    } catch (caught) {
      setError(getErrorMessage(caught));
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="task-editor-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="kicker">{task ? `Versión ${task.version}` : "Nueva tarea"}</p>
            <h2 id="task-editor-title">{task ? "Editar tarea" : "Añadir tarea"}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Cerrar">×</button>
        </div>
        <form className="stack-form" onSubmit={submit}>
          <label>
            Título
            <input name="title" required maxLength={200} defaultValue={task?.title} autoFocus />
          </label>
          <label>
            Descripción
            <textarea name="description" rows={5} maxLength={10000} defaultValue={task?.description ?? ""} />
          </label>
          <label>
            Estado
            <select name="status" defaultValue={task?.status ?? "todo"}>
              {Object.entries(STATUS_META).map(([value, meta]) => <option key={value} value={value}>{meta.label}</option>)}
            </select>
          </label>
          {error && <div className="notice notice-error" role="alert">{error}</div>}
          <div className="form-actions">
            <button type="button" className="button button-secondary" onClick={onClose}>Cancelar</button>
            <button className="button button-primary" disabled={saving}>{saving ? "Guardando…" : "Guardar tarea"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function Board({ token, onSignOut }: { token: string; onSignOut: () => void }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<Task | "new" | null>(null);

  const workspace = workspaces.find((item) => item.id === workspaceId);
  const project = projects.find((item) => item.id === projectId);
  const canWrite = workspace?.role === "owner" || workspace?.role === "editor";

  const handleError = useCallback((caught: unknown) => {
    if (caught instanceof ApiError && caught.status === 401) {
      onSignOut();
      return;
    }
    setError(getErrorMessage(caught));
  }, [onSignOut]);

  const loadTasks = useCallback(async (selectedProject: string) => {
    if (!selectedProject) {
      setTasks([]);
      return;
    }
    try {
      setTasks(await api.tasks(token, selectedProject));
      setError("");
    } catch (caught) {
      handleError(caught);
    }
  }, [handleError, token]);

  useEffect(() => {
    void (async () => {
      try {
        const available = await api.workspaces(token);
        setWorkspaces(available);
        setWorkspaceId((current) => current || available[0]?.id || "");
      } catch (caught) {
        handleError(caught);
      } finally {
        setLoading(false);
      }
    })();
  }, [handleError, token]);

  useEffect(() => {
    if (!workspaceId) return;
    void (async () => {
      try {
        const available = await api.projects(token, workspaceId);
        setProjects(available);
        setProjectId(available[0]?.id || "");
        setTasks([]);
        if (available[0]) await loadTasks(available[0].id);
      } catch (caught) {
        handleError(caught);
      }
    })();
  }, [handleError, loadTasks, token, workspaceId]);

  const groupedTasks = useMemo(() => Object.fromEntries(
    Object.keys(STATUS_META).map((status) => [status, tasks.filter((task) => task.status === status)]),
  ) as Record<TaskStatus, Task[]>, [tasks]);

  async function addProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const created = await api.createProject(token, workspaceId, String(data.get("name")).trim());
      setProjects((current) => [...current, created]);
      setProjectId(created.id);
      setTasks([]);
      form.reset();
    } catch (caught) {
      handleError(caught);
    }
  }

  async function saveTask(input: { title: string; description: string | null; status: TaskStatus }) {
    try {
      const saved = editor === "new"
        ? await api.createTask(token, projectId, input)
        : await api.updateTask(token, projectId, editor!.id, { ...input, version: editor!.version });
      setTasks((current) => editor === "new"
        ? [...current, saved]
        : current.map((item) => item.id === saved.id ? saved : item));
      setEditor(null);
      setError("");
    } catch (caught) {
      if (isVersionConflict(caught)) {
        await loadTasks(projectId);
        setEditor(null);
        setError(`La tarea cambió mientras la editabas. Recargamos la versión ${caught.body.current_version}.`);
        return;
      }
      throw caught;
    }
  }

  if (loading) return <main className="center-message">Cargando tu espacio…</main>;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Workboard, inicio"><span className="brand-mark">W</span>Workboard</a>
        <div className="sidebar-section">
          <label className="select-label" htmlFor="workspace">Espacio</label>
          <select id="workspace" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}>
            {workspaces.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          {workspace && <span className="role-badge">{workspace.role}</span>}
        </div>

        <nav className="project-nav" aria-label="Proyectos">
          <p className="nav-title">Proyectos</p>
          {projects.map((item) => (
            <button
              key={item.id}
              className={item.id === projectId ? "project-link active" : "project-link"}
              onClick={() => { setProjectId(item.id); void loadTasks(item.id); }}
            >
              <span className="project-dot" />{item.name}
            </button>
          ))}
          {!projects.length && <p className="sidebar-empty">Aún no hay proyectos.</p>}
        </nav>

        {canWrite && (
          <form className="quick-create" onSubmit={addProject}>
            <input name="name" required maxLength={160} placeholder="Nuevo proyecto" aria-label="Nombre del proyecto" />
            <button type="submit" aria-label="Crear proyecto">+</button>
          </form>
        )}
        <button className="sign-out" type="button" onClick={onSignOut}>Cerrar sesión</button>
      </aside>

      <main className="workspace-main">
        <header className="page-header">
          <div>
            <p className="kicker">{workspace?.name ?? "Tu espacio"}</p>
            <h1>{project?.name ?? "Selecciona un proyecto"}</h1>
            <p className="muted">{tasks.length} {tasks.length === 1 ? "tarea" : "tareas"} en este tablero</p>
          </div>
          {canWrite && project && <button className="button button-primary" onClick={() => setEditor("new")}>+ Añadir tarea</button>}
        </header>

        {error && <div className="notice notice-error board-notice" role="alert">{error}<button onClick={() => setError("")} aria-label="Cerrar aviso">×</button></div>}

        {!project && (
          <section className="empty-state">
            <span className="empty-icon">◎</span>
            <h2>Crea tu primer proyecto</h2>
            <p>Los proyectos reúnen las tareas de un objetivo compartido.</p>
          </section>
        )}

        {project && (
          <section className="board" aria-label="Tablero de tareas">
            {(Object.keys(STATUS_META) as TaskStatus[]).map((status) => (
              <div className="column" key={status}>
                <div className="column-header">
                  <div><span>{STATUS_META[status].eyebrow}</span><h2>{STATUS_META[status].label}</h2></div>
                  <span className="count">{groupedTasks[status].length}</span>
                </div>
                <div className="task-list">
                  {groupedTasks[status].map((task) => (
                    <article className="task-card" key={task.id}>
                      <div className={`status-line status-${status}`} />
                      <h3>{task.title}</h3>
                      {task.description && <p>{task.description}</p>}
                      <div className="task-meta">
                        <span>v{task.version}</span>
                        {canWrite && <button onClick={() => setEditor(task)}>Editar</button>}
                      </div>
                    </article>
                  ))}
                  {!groupedTasks[status].length && <div className="column-empty">Sin tareas</div>}
                </div>
              </div>
            ))}
          </section>
        )}
      </main>

      {editor && <TaskEditor task={editor === "new" ? undefined : editor} onClose={() => setEditor(null)} onSave={saveTask} />}
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(readToken);

  const signOut = useCallback(() => {
    clearToken();
    setToken(null);
  }, []);

  if (!token) return <AuthScreen onAuthenticated={setToken} />;
  return <Board token={token} onSignOut={signOut} />;
}
