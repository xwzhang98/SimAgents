"use client";

import type { Message } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
}

function getRoleConfig(role?: string) {
  switch (role) {
    case "physics_expert":
      return {
        label: "Physics Expert",
        labelColor: "#4ade80",
        avatarBg: "#1e3a5a",
        avatarText: "PE",
      };
    case "formatter":
      return {
        label: "Formatter",
        labelColor: "#a78bfa",
        avatarBg: "#2a1e3a",
        avatarText: "FM",
      };
    case "system":
      return {
        label: "System",
        labelColor: "#9ca3af",
        avatarBg: "#2a2a4a",
        avatarText: "SY",
      };
    default:
      return {
        label: "Agent",
        labelColor: "#9ca3af",
        avatarBg: "#2a2a4a",
        avatarText: "AG",
      };
  }
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  // User message — right aligned, purple
  if (message.type === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-[#7c3aed] px-4 py-3 text-white">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  // Status message — centered, muted
  if (message.type === "status") {
    return (
      <div className="flex justify-center mb-4">
        <div className="flex items-center gap-2 rounded-full bg-[#1a1a2e] px-4 py-2 text-xs text-[#9ca3af]">
          {message.status === "uploading" || message.status === "starting" ? (
            <span className="inline-block h-2 w-2 rounded-full bg-[#f59e0b] animate-pulse" />
          ) : (
            <span className="inline-block h-2 w-2 rounded-full bg-[#4ade80]" />
          )}
          {message.message || message.status}
        </div>
      </div>
    );
  }

  // Complete message
  if (message.type === "complete") {
    return (
      <div className="flex justify-center mb-4">
        <div className="flex items-center gap-2 rounded-full bg-[#1a2e1a] px-4 py-2 text-xs text-[#4ade80]">
          <span className="inline-block h-2 w-2 rounded-full bg-[#4ade80]" />
          {message.message || "Extraction complete!"}
        </div>
      </div>
    );
  }

  // Error message
  if (message.type === "error") {
    return (
      <div className="flex justify-center mb-4">
        <div className="flex items-center gap-2 rounded-full bg-[#2e1a1a] px-4 py-2 text-xs text-[#ff6b6b]">
          <span className="inline-block h-2 w-2 rounded-full bg-[#ff6b6b]" />
          {message.message}
        </div>
      </div>
    );
  }

  // Needs input — shown as system message (QuickReply handles the input UI)
  if (message.type === "needs_input") {
    return (
      <div className="flex justify-start mb-4">
        <div className="flex gap-3 max-w-[85%]">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
            style={{ backgroundColor: "#2a2a4a" }}
          >
            <span style={{ color: "#f59e0b" }}>?</span>
          </div>
          <div>
            <div className="mb-1 text-xs font-medium" style={{ color: "#f59e0b" }}>
              Input Required
            </div>
            <div className="rounded-2xl rounded-bl-sm border border-[#f59e0b]/30 bg-[#1a1a2e] px-4 py-3">
              {message.questions && message.questions.length > 0 && (
                <ul className="space-y-1">
                  {message.questions.map((q, i) => (
                    <li key={i} className="text-sm text-[#e2e8f0]">
                      {q}
                    </li>
                  ))}
                </ul>
              )}
              {message.missing && message.missing.length > 0 && (
                <p className="mt-2 text-xs text-[#9ca3af]">
                  Missing: {message.missing.join(", ")}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Agent message — left aligned with avatar
  const config = getRoleConfig(message.role);
  return (
    <div className="flex justify-start mb-4">
      <div className="flex gap-3 max-w-[85%]">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
          style={{ backgroundColor: config.avatarBg }}
        >
          {config.avatarText}
        </div>
        <div>
          <div className="mb-1 text-xs font-medium" style={{ color: config.labelColor }}>
            {config.label}
          </div>
          <div className="rounded-2xl rounded-bl-sm bg-[#1a1a2e] px-4 py-3">
            <p className="text-sm text-[#e2e8f0] whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
