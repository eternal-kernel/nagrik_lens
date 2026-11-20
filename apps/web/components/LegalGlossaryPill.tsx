"use client";

import React, { useState } from "react";
import { LegalGlossaryItem } from "@/lib/api";
import { BookOpen, ChevronDown, ChevronUp, Scale } from "lucide-react";

interface LegalGlossaryPillProps {
  item: LegalGlossaryItem;
}

export default function LegalGlossaryPill({ item }: LegalGlossaryPillProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Clean human-readable display title (no raw STAGE_ / CHARGES_ database keys)
  const getDisplayLabel = (): string => {
    const code = item.code_key.toUpperCase();
    if (code.startsWith("IPC_") || code.startsWith("BNS_")) {
      const section = item.code_key.replace("_", " ");
      if (item.term.toUpperCase().includes(section.toUpperCase())) {
        return item.term;
      }
      return `${section} — ${item.term}`;
    }
    // Procedural concepts: show human-readable term directly without raw key prefixes
    return item.term;
  };

  return (
    <div className="inline-block text-left">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-all ${
          isOpen
            ? "border-blue-400 bg-blue-100 text-blue-900 shadow-sm"
            : "border-blue-200 bg-blue-50/70 text-blue-800 hover:border-blue-300 hover:bg-blue-100/60"
        }`}
        aria-expanded={isOpen}
      >
        <BookOpen className="h-3 w-3 text-blue-600" />
        <span>{getDisplayLabel()}</span>
        {isOpen ? (
          <ChevronUp className="h-3 w-3 text-blue-600" />
        ) : (
          <ChevronDown className="h-3 w-3 text-blue-500" />
        )}
      </button>

      {isOpen && (
        <div className="mt-2 w-full rounded-xl border border-blue-200 bg-blue-50/90 p-4 text-xs text-blue-950 shadow-sm animate-fadeIn">
          <div className="mb-1.5 flex items-center justify-between border-b border-blue-200/60 pb-1.5">
            <div className="flex items-center gap-1.5 font-bold text-blue-900">
              <Scale className="h-3.5 w-3.5 text-blue-700" />
              <span>{item.term}</span>
            </div>
            <span className="rounded bg-white/80 px-2 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200">
              {item.act_name}
            </span>
          </div>
          <p className="leading-relaxed text-blue-900/90 whitespace-pre-line">
            {item.explanation}
          </p>
        </div>
      )}
    </div>
  );
}
