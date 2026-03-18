"use client";

import { useState, useCallback } from "react";
import type { ParametersData } from "@/lib/types";
import { updateParameters, getExportUrl } from "@/lib/api";

interface ParameterPanelProps {
  parameters: ParametersData | null;
  sessionId: string | null;
}

type Tab = "genic" | "gadget" | "sources";

export default function ParameterPanel({ parameters, sessionId }: ParameterPanelProps) {
  const [tab, setTab] = useState<Tab>("genic");
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState<Record<string, unknown>>({});

  const handleEdit = () => {
    if (!parameters) return;
    setEditMode(true);
    setEditData(
      tab === "genic"
        ? { ...parameters.genic }
        : tab === "gadget"
          ? { ...parameters.gadget }
          : {}
    );
  };

  const handleSave = useCallback(async () => {
    if (!sessionId || !parameters) return;
    try {
      const payload =
        tab === "genic"
          ? { genic: editData }
          : tab === "gadget"
            ? { gadget: editData }
            : {};
      await updateParameters(sessionId, payload);
      setEditMode(false);
    } catch (err) {
      console.error("Failed to save parameters:", err);
    }
  }, [sessionId, parameters, tab, editData]);

  const handleCancel = () => {
    setEditMode(false);
    setEditData({});
  };

  const handleExport = () => {
    if (!sessionId) return;
    window.open(getExportUrl(sessionId), "_blank");
  };

  const currentParams =
    tab === "genic"
      ? parameters?.genic
      : tab === "gadget"
        ? parameters?.gadget
        : null;

  const missingSet = new Set(parameters?.missing || []);

  return (
    <div className="flex h-full flex-col bg-[#0f0f1a]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1a1a2e] px-4 py-4">
        <h3 className="text-sm font-semibold text-[#e2e8f0]">Parameters</h3>
        <div className="flex items-center gap-2">
          {!editMode && tab !== "sources" && (
            <button
              onClick={handleEdit}
              disabled={!parameters}
              className="rounded-lg border border-[#2a2a4a] px-3 py-1.5 text-xs text-[#9ca3af] hover:text-[#e2e8f0] hover:border-[#7c3aed] transition-colors disabled:opacity-50"
            >
              Edit
            </button>
          )}
          {editMode && (
            <>
              <button
                onClick={handleCancel}
                className="rounded-lg border border-[#2a2a4a] px-3 py-1.5 text-xs text-[#9ca3af] hover:text-[#e2e8f0] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="rounded-lg bg-[#7c3aed] px-3 py-1.5 text-xs text-white hover:bg-[#6d28d9] transition-colors"
              >
                Save
              </button>
            </>
          )}
          <button
            onClick={handleExport}
            disabled={!sessionId}
            className="rounded-lg border border-[#2a2a4a] px-3 py-1.5 text-xs text-[#9ca3af] hover:text-[#e2e8f0] hover:border-[#7c3aed] transition-colors disabled:opacity-50"
          >
            Export
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1a1a2e]">
        {(["genic", "gadget", "sources"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setEditMode(false);
            }}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              tab === t
                ? "border-b-2 border-[#7c3aed] text-[#7c3aed]"
                : "text-[#666] hover:text-[#9ca3af]"
            }`}
          >
            {t === "genic" ? "GenIC" : t === "gadget" ? "Gadget" : "Sources"}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {!parameters ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-[#666]">
              No parameters yet. Upload a paper to start extraction.
            </p>
          </div>
        ) : tab === "sources" ? (
          <SourcesTab sources={parameters.sources} />
        ) : (
          <ParamTable
            params={editMode ? editData : (currentParams || {})}
            missing={missingSet}
            editMode={editMode}
            onValueChange={(key, value) =>
              setEditData((prev) => ({ ...prev, [key]: value }))
            }
          />
        )}
      </div>

      {/* Status bar */}
      {parameters && (
        <div className="flex items-center justify-between border-t border-[#1a1a2e] px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                parameters.status === "complete"
                  ? "bg-[#4ade80]"
                  : parameters.status === "in_progress"
                    ? "bg-[#f59e0b]"
                    : "bg-[#ff6b6b]"
              }`}
            />
            <span className="text-xs text-[#9ca3af] capitalize">
              {parameters.status}
            </span>
          </div>
          {parameters.missing.length > 0 && (
            <span className="text-xs text-[#ff6b6b]">
              {parameters.missing.length} missing
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function ParamTable({
  params,
  missing,
  editMode,
  onValueChange,
}: {
  params: Record<string, unknown>;
  missing: Set<string>;
  editMode: boolean;
  onValueChange: (key: string, value: string) => void;
}) {
  const entries = Object.entries(params);

  if (entries.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-[#666]">No parameters</p>
    );
  }

  return (
    <div className="space-y-1">
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-[#1a1a2e]/50"
        >
          <span
            className={`text-xs ${
              missing.has(key) ? "text-[#ff6b6b]" : "text-[#9ca3af]"
            }`}
          >
            {key}
          </span>
          {editMode ? (
            <input
              type="text"
              value={String(value ?? "")}
              onChange={(e) => onValueChange(key, e.target.value)}
              className="w-40 rounded border border-[#2a2a4a] bg-[#1a1a2e] px-2 py-1 text-xs text-[#4ade80] font-mono"
            />
          ) : (
            <span
              className={`text-xs font-mono ${
                value === null || value === undefined || value === ""
                  ? "text-[#ff6b6b]"
                  : "text-[#4ade80]"
              }`}
            >
              {value === null || value === undefined || value === ""
                ? "missing"
                : String(value)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function SourcesTab({
  sources,
}: {
  sources: Array<{ param: string; value: unknown; location: string; page: number }>;
}) {
  if (!sources || sources.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-[#666]">No sources tracked</p>
    );
  }

  return (
    <div className="space-y-2">
      {sources.map((src, i) => (
        <div
          key={i}
          className="rounded-lg bg-[#1a1a2e] px-3 py-2.5"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-[#e2e8f0]">
              {src.param}
            </span>
            <span className="text-xs font-mono text-[#4ade80]">
              {String(src.value)}
            </span>
          </div>
          <div className="text-xs text-[#666]">
            {src.location} (p. {src.page})
          </div>
        </div>
      ))}
    </div>
  );
}
