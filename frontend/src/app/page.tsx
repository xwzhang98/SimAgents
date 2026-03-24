"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { View, Message, ParametersData, SSEEvent, ResourceEstimates } from "@/lib/types";
import {
  uploadFile,
  startExtraction,
  respondToQuestion,
  getParameters,
  getStreamUrl,
  getSessionStatus,
} from "@/lib/api";
import { connectSSE } from "@/lib/sse";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";
import ParameterPanel from "@/components/ParameterPanel";
import SettingsView from "@/components/SettingsView";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [parameters, setParameters] = useState<ParametersData | null>(null);
  const [resourceEstimates, setResourceEstimates] = useState<ResourceEstimates | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [waitingForInput, setWaitingForInput] = useState(false);
  const [pendingQuestions, setPendingQuestions] = useState<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    getSessionStatus()
      .then((data) => {
        if (data.session_id && data.status) {
          setSessionId(data.session_id);
          if (data.messages) setMessages(data.messages);
          if (data.status === "running") {
            setIsExtracting(true);
          }
        }
      })
      .catch(() => {
        // No existing session
      });
  }, []);

  const closeSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const handleSSEEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case "agent_message":
          setMessages((prev) => [
            ...prev,
            {
              type: "agent_message",
              role: event.role as Message["role"],
              content: event.content,
            },
          ]);
          break;
        case "status":
          setMessages((prev) => [
            ...prev,
            { type: "status", status: event.status, message: event.message },
          ]);
          break;
        case "needs_input":
          setWaitingForInput(true);
          setPendingQuestions(event.questions || []);
          setMessages((prev) => [
            ...prev,
            {
              type: "needs_input",
              questions: event.questions,
              missing: event.missing,
            },
          ]);
          break;
        case "parameters_update":
          if (event.data) {
            setParameters(event.data as ParametersData);
          }
          break;
        case "resource_estimates":
          if (event.data) {
            setResourceEstimates(event.data as ResourceEstimates);
          }
          break;
        case "complete":
          setIsExtracting(false);
          setMessages((prev) => [
            ...prev,
            { type: "complete", message: event.message || "Extraction complete!" },
          ]);
          closeSSE();
          // Fetch final parameters
          if (sessionId) {
            getParameters(sessionId)
              .then(setParameters)
              .catch(console.error);
          }
          break;
        case "error":
          setIsExtracting(false);
          setMessages((prev) => [
            ...prev,
            { type: "error", message: event.message || "An error occurred" },
          ]);
          closeSSE();
          break;
      }
    },
    [closeSSE, sessionId]
  );

  const startSSE = useCallback(
    (sid: string) => {
      closeSSE();
      const source = connectSSE(
        getStreamUrl(sid),
        handleSSEEvent,
        () => {
          // onClose
        },
        (err) => {
          console.error("SSE error:", err);
        }
      );
      eventSourceRef.current = source;
    },
    [closeSSE, handleSSEEvent]
  );

  const handleFileUpload = useCallback(
    async (file: File) => {
      try {
        setMessages((prev) => [
          ...prev,
          { type: "user", role: "user", content: `Uploaded: ${file.name}` },
        ]);
        setMessages((prev) => [
          ...prev,
          { type: "status", status: "uploading", message: "Uploading file..." },
        ]);

        const { file_id } = await uploadFile(file);

        setMessages((prev) => [
          ...prev,
          { type: "status", status: "starting", message: "Starting extraction..." },
        ]);

        setIsExtracting(true);
        const { session_id } = await startExtraction({ file_id });
        setSessionId(session_id);
        startSSE(session_id);
      } catch (err) {
        setIsExtracting(false);
        setMessages((prev) => [
          ...prev,
          {
            type: "error",
            message: `Upload failed: ${err instanceof Error ? err.message : String(err)}`,
          },
        ]);
      }
    },
    [startSSE]
  );

  const handleSendMessage = useCallback(
    async (text: string) => {
      setMessages((prev) => [
        ...prev,
        { type: "user", role: "user", content: text },
      ]);

      if (waitingForInput && sessionId) {
        try {
          // Build answers from questions + single response
          const answers: Record<string, unknown> = {};
          pendingQuestions.forEach((q, i) => {
            answers[`q${i}`] = text;
          });
          if (pendingQuestions.length === 0) {
            answers["response"] = text;
          }

          await respondToQuestion(sessionId, answers);
          setWaitingForInput(false);
          setPendingQuestions([]);
          startSSE(sessionId);
        } catch (err) {
          setMessages((prev) => [
            ...prev,
            {
              type: "error",
              message: `Failed to send response: ${err instanceof Error ? err.message : String(err)}`,
            },
          ]);
        }
      }
    },
    [waitingForInput, sessionId, pendingQuestions, startSSE]
  );

  const handleQuickReply = useCallback(
    async (answers: Record<string, unknown>) => {
      if (!sessionId) return;
      try {
        setMessages((prev) => [
          ...prev,
          {
            type: "user",
            role: "user",
            content: Object.values(answers).join(", "),
          },
        ]);
        await respondToQuestion(sessionId, answers);
        setWaitingForInput(false);
        setPendingQuestions([]);
        startSSE(sessionId);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            type: "error",
            message: `Failed to send response: ${err instanceof Error ? err.message : String(err)}`,
          },
        ]);
      }
    },
    [sessionId, startSSE]
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar view={view} onViewChange={setView} />

      {view === "settings" ? (
        <div className="flex-1 overflow-y-auto">
          <SettingsView />
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Chat Panel */}
          <div className="flex flex-[3] flex-col overflow-hidden">
            <ChatPanel
              messages={messages}
              isExtracting={isExtracting}
              waitingForInput={waitingForInput}
              pendingQuestions={pendingQuestions}
              onFileUpload={handleFileUpload}
              onSendMessage={handleSendMessage}
              onQuickReply={handleQuickReply}
            />
          </div>

          {/* Parameter Panel */}
          <div className="flex flex-[2] flex-col overflow-hidden border-l border-[#1a1a2e]">
            <ParameterPanel
              parameters={parameters}
              sessionId={sessionId}
              resourceEstimates={resourceEstimates}
            />
          </div>
        </div>
      )}
    </div>
  );
}
