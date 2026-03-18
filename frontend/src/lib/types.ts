export interface Message {
  type: "agent_message" | "status" | "needs_input" | "complete" | "error" | "user";
  role?: "physics_expert" | "formatter" | "user" | "system";
  content?: string;
  questions?: string[];
  missing?: string[];
  status?: string;
  message?: string;
}

export interface ParametersData {
  genic: Record<string, unknown>;
  gadget: Record<string, unknown>;
  status: string;
  missing: string[];
  sources: Array<{ param: string; value: unknown; location: string; page: number }>;
}

export interface SSEEvent {
  type: string;
  role?: string;
  content?: string;
  data?: ParametersData;
  questions?: string[];
  missing?: string[];
  status?: string;
  message?: string;
}

export interface SettingsData {
  llm: { provider: string; model: string; temperature: number };
  rag: { pdf_loader: string; vector_store: string; chunk_size: number; chunk_overlap: number; embedding_provider: string; embedding_model: string };
  extraction: { max_iterations: number; target_software: string };
  paths: { output_dir: string; software_docs_dir: string };
  slurm: Record<string, unknown> | null;
}

export type View = "chat" | "settings";
