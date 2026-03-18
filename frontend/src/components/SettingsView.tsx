"use client";

import { useState, useEffect } from "react";
import type { SettingsData } from "@/lib/types";
import { getSettings, updateSettings } from "@/lib/api";

export default function SettingsView() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [draft, setDraft] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setLoading(true);
    getSettings()
      .then((data) => {
        setSettings(data);
        setDraft(data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await updateSettings(draft);
      setSettings(updated);
      setDraft(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setDraft(settings);
    setError(null);
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-[#666]">Loading settings...</p>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-[#ff6b6b]">
          {error || "Failed to load settings"}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-[#e2e8f0]">Settings</h2>
        <div className="flex gap-2">
          <button
            onClick={handleCancel}
            className="rounded-lg border border-[#2a2a4a] px-4 py-2 text-sm text-[#9ca3af] hover:text-[#e2e8f0] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-[#7c3aed] px-4 py-2 text-sm font-medium text-white hover:bg-[#6d28d9] transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-[#2e1a1a] px-4 py-3 text-sm text-[#ff6b6b]">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 rounded-lg bg-[#1a2e1a] px-4 py-3 text-sm text-[#4ade80]">
          Settings saved successfully.
        </div>
      )}

      <div className="space-y-6">
        {/* LLM Section */}
        <Section title="LLM Configuration">
          <Field
            label="Provider"
            value={draft.llm.provider}
            onChange={(v) =>
              setDraft({ ...draft, llm: { ...draft.llm, provider: v } })
            }
          />
          <Field
            label="Model"
            value={draft.llm.model}
            onChange={(v) =>
              setDraft({ ...draft, llm: { ...draft.llm, model: v } })
            }
          />
          <Field
            label="Temperature"
            value={String(draft.llm.temperature)}
            onChange={(v) =>
              setDraft({
                ...draft,
                llm: { ...draft.llm, temperature: parseFloat(v) || 0 },
              })
            }
            type="number"
          />
        </Section>

        {/* RAG Section */}
        <Section title="RAG Configuration">
          <Field
            label="PDF Loader"
            value={draft.rag.pdf_loader}
            onChange={(v) =>
              setDraft({ ...draft, rag: { ...draft.rag, pdf_loader: v } })
            }
          />
          <Field
            label="Vector Store"
            value={draft.rag.vector_store}
            onChange={(v) =>
              setDraft({ ...draft, rag: { ...draft.rag, vector_store: v } })
            }
          />
          <Field
            label="Chunk Size"
            value={String(draft.rag.chunk_size)}
            onChange={(v) =>
              setDraft({
                ...draft,
                rag: { ...draft.rag, chunk_size: parseInt(v) || 0 },
              })
            }
            type="number"
          />
          <Field
            label="Chunk Overlap"
            value={String(draft.rag.chunk_overlap)}
            onChange={(v) =>
              setDraft({
                ...draft,
                rag: { ...draft.rag, chunk_overlap: parseInt(v) || 0 },
              })
            }
            type="number"
          />
          <Field
            label="Embedding Provider"
            value={draft.rag.embedding_provider}
            onChange={(v) =>
              setDraft({
                ...draft,
                rag: { ...draft.rag, embedding_provider: v },
              })
            }
          />
          <Field
            label="Embedding Model"
            value={draft.rag.embedding_model}
            onChange={(v) =>
              setDraft({
                ...draft,
                rag: { ...draft.rag, embedding_model: v },
              })
            }
          />
        </Section>

        {/* Extraction Section */}
        <Section title="Extraction">
          <Field
            label="Max Iterations"
            value={String(draft.extraction.max_iterations)}
            onChange={(v) =>
              setDraft({
                ...draft,
                extraction: {
                  ...draft.extraction,
                  max_iterations: parseInt(v) || 0,
                },
              })
            }
            type="number"
          />
          <Field
            label="Target Software"
            value={draft.extraction.target_software}
            onChange={(v) =>
              setDraft({
                ...draft,
                extraction: { ...draft.extraction, target_software: v },
              })
            }
          />
        </Section>

        {/* Paths Section */}
        <Section title="Paths">
          <Field
            label="Output Directory"
            value={draft.paths.output_dir}
            onChange={(v) =>
              setDraft({ ...draft, paths: { ...draft.paths, output_dir: v } })
            }
          />
          <Field
            label="Software Docs Directory"
            value={draft.paths.software_docs_dir}
            onChange={(v) =>
              setDraft({
                ...draft,
                paths: { ...draft.paths, software_docs_dir: v },
              })
            }
          />
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-[#1a1a2e] p-5">
      <h3 className="mb-4 text-sm font-semibold text-[#e2e8f0]">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <label className="shrink-0 text-sm text-[#9ca3af]">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-64 rounded-lg border border-[#2a2a4a] bg-[#12122a] px-3 py-2 text-sm text-[#e2e8f0]"
      />
    </div>
  );
}
