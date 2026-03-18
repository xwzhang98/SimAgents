"use client";

import { useState } from "react";

interface QuickReplyProps {
  questions: string[];
  onSubmit: (answers: Record<string, unknown>) => void;
}

export default function QuickReply({ questions, onSubmit }: QuickReplyProps) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    questions.forEach((_, i) => {
      initial[`q${i}`] = "";
    });
    return initial;
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(answers);
  };

  if (questions.length === 0) return null;

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-4 mb-4 rounded-xl border border-[#f59e0b]/30 bg-[#1a1a2e] p-4"
    >
      <div className="mb-3 flex items-center gap-2 text-xs font-medium text-[#f59e0b]">
        <span className="inline-block h-2 w-2 rounded-full bg-[#f59e0b] animate-pulse" />
        Input Required
      </div>
      <div className="space-y-3">
        {questions.map((q, i) => (
          <div key={i}>
            <label className="mb-1 block text-sm text-[#e2e8f0]">{q}</label>
            <input
              type="text"
              value={answers[`q${i}`] || ""}
              onChange={(e) =>
                setAnswers((prev) => ({ ...prev, [`q${i}`]: e.target.value }))
              }
              className="w-full rounded-lg px-3 py-2 text-sm"
              placeholder="Type your answer..."
            />
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-end">
        <button
          type="submit"
          className="rounded-lg bg-[#7c3aed] px-4 py-2 text-sm font-medium text-white hover:bg-[#6d28d9] transition-colors"
        >
          Send
        </button>
      </div>
    </form>
  );
}
