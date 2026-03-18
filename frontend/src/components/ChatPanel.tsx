"use client";

import { useRef, useEffect, useState } from "react";
import type { Message } from "@/lib/types";
import MessageBubble from "./MessageBubble";
import QuickReply from "./QuickReply";
import FileUpload from "./FileUpload";

interface ChatPanelProps {
  messages: Message[];
  isExtracting: boolean;
  waitingForInput: boolean;
  pendingQuestions: string[];
  onFileUpload: (file: File) => void;
  onSendMessage: (text: string) => void;
  onQuickReply: (answers: Record<string, unknown>) => void;
}

export default function ChatPanel({
  messages,
  isExtracting,
  waitingForInput,
  pendingQuestions,
  onFileUpload,
  onSendMessage,
  onQuickReply,
}: ChatPanelProps) {
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const text = inputText.trim();
    if (!text) return;
    setInputText("");
    onSendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1a1a2e] px-6 py-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-[#e2e8f0]">SimAgents</h2>
          {isExtracting && (
            <span className="flex items-center gap-1.5 rounded-full bg-[#1a1a2e] px-3 py-1 text-xs text-[#f59e0b]">
              <span className="inline-block h-2 w-2 rounded-full bg-[#f59e0b] animate-pulse" />
              Extracting...
            </span>
          )}
          {!isExtracting && messages.some((m) => m.type === "complete") && (
            <span className="flex items-center gap-1.5 rounded-full bg-[#1a2e1a] px-3 py-1 text-xs text-[#4ade80]">
              <span className="inline-block h-2 w-2 rounded-full bg-[#4ade80]" />
              Complete
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#7c3aed]/20 text-[#7c3aed]">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-medium text-[#e2e8f0]">
              Upload a Paper
            </h3>
            <p className="max-w-sm text-sm text-[#9ca3af]">
              Upload a PDF of a scientific paper to extract simulation parameters.
              Click the paperclip icon below or drag and drop.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Reply for HITL */}
      {waitingForInput && pendingQuestions.length > 0 && (
        <QuickReply questions={pendingQuestions} onSubmit={onQuickReply} />
      )}

      {/* Input Area */}
      <div className="border-t border-[#1a1a2e] px-4 py-3">
        <div className="flex items-center gap-2 rounded-xl bg-[#1a1a2e] px-3 py-2">
          <FileUpload onFileSelect={onFileUpload} disabled={isExtracting} />
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              waitingForInput
                ? "Type your answer..."
                : isExtracting
                  ? "Extraction in progress..."
                  : "Upload a PDF to start..."
            }
            disabled={isExtracting && !waitingForInput}
            className="flex-1 border-none bg-transparent px-2 py-1 text-sm text-[#e2e8f0] placeholder-[#666] outline-none"
          />
          <button
            onClick={handleSend}
            disabled={(isExtracting && !waitingForInput) || !inputText.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#7c3aed] text-white hover:bg-[#6d28d9] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
