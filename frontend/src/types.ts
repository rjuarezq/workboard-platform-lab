export type Role = "owner" | "editor" | "viewer";
export type TaskStatus = "todo" | "in_progress" | "done";

export interface Workspace {
  id: string;
  name: string;
  role: Role;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  created_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  created_by_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface VersionConflict {
  code: "task_version_conflict";
  message: string;
  current_version: number;
}
