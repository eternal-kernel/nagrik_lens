"use client";

import Link from "next/link";
import { useLanguage, SupportedLang } from "@/lib/language-context";
import { Globe, ShieldCheck, CheckSquare } from "lucide-react";

export default function Navbar() {
  const { lang, setLang, t } = useLanguage();

  const languages: { code: SupportedLang; label: string; native: string }[] = [
    { code: "en", label: "English", native: "English" },
    { code: "te", label: "Telugu", native: "తెలుగు" },
    { code: "hi", label: "Hindi", native: "हिन्दी" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-civic-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-90">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-civic-900 text-white shadow-sm">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-bold tracking-tight text-civic-900">
              {t("brand")}
            </span>
            <span className="hidden text-[10px] font-medium tracking-wider text-civic-500 uppercase sm:inline">
              Form 26 Civic Information
            </span>
          </div>
        </Link>

        {/* Right Nav / Language Switcher */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Subtle Reviewer Console link for demonstrations */}
          <Link
            href="/admin/review"
            className="inline-flex items-center gap-1.5 rounded-lg border border-civic-200 bg-white px-2.5 py-1 text-xs font-semibold text-civic-700 transition hover:border-civic-300 hover:bg-civic-50"
            title="Human Verification Review Console"
          >
            <CheckSquare className="h-3.5 w-3.5 text-civic-600" />
            <span className="hidden sm:inline">Reviewer Console</span>
            <span className="sm:hidden">Review</span>
          </Link>

          <div className="flex items-center gap-1.5 rounded-lg border border-civic-200 bg-civic-50 p-1">
            <Globe className="ml-1.5 h-4 w-4 text-civic-500" />
            <div className="flex items-center">
              {languages.map((l) => (
                <button
                  key={l.code}
                  onClick={() => setLang(l.code)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
                    lang === l.code
                      ? "bg-civic-900 text-white shadow-sm"
                      : "text-civic-700 hover:bg-civic-200/60"
                  }`}
                  title={`${l.label} (${l.native})`}
                >
                  {l.native}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
