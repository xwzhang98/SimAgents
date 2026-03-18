"use client";

import type { View } from "@/lib/types";

interface SidebarProps {
  view: View;
  onViewChange: (view: View) => void;
}

export default function Sidebar({ view, onViewChange }: SidebarProps) {
  return (
    <div className="flex h-full w-[60px] flex-col items-center bg-[#12122a] py-4 border-r border-[#1a1a2e]">
      {/* Logo */}
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-lg bg-[#7c3aed] text-white font-bold text-lg select-none">
        S
      </div>

      {/* Nav icons */}
      <nav className="flex flex-1 flex-col items-center gap-2">
        <SidebarButton
          label="Chat"
          icon={
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
          }
          active={view === "chat"}
          onClick={() => onViewChange("chat")}
        />
        <SidebarButton
          label="Settings"
          icon={
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
            </svg>
          }
          active={view === "settings"}
          onClick={() => onViewChange("settings")}
        />
      </nav>

      {/* Bottom help */}
      <div className="mt-auto">
        <button
          className="flex h-10 w-10 items-center justify-center rounded-lg text-[#666] hover:text-[#9ca3af] transition-colors"
          title="Help"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </button>
      </div>
    </div>
  );
}

function SidebarButton({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
        active
          ? "bg-[#1a1a2e] text-[#7c3aed] border border-[#7c3aed]"
          : "text-[#666] hover:text-[#9ca3af] hover:bg-[#1a1a2e]/50"
      }`}
    >
      {icon}
    </button>
  );
}
