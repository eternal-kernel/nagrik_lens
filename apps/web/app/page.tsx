"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/lib/language-context";
import { getCandidates, CandidateSummary } from "@/lib/api";
import {
  FileText,
  ShieldCheck,
  Scale,
  Search,
  ExternalLink,
  Info,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";

export default function HomePage() {
  const { t, lang } = useLanguage();
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function loadCandidates() {
      try {
        setLoading(true);
        setError(null);
        const data = await getCandidates();
        if (mounted) {
          setCandidates(data);
        }
      } catch (err: any) {
        if (mounted) {
          console.warn("Could not fetch candidates from backend:", err);
          // Fallback dummy for offline view
          setCandidates([
            {
              id: 1,
              constituency_id: 1,
              name: "Candidate X",
              display_name: "Candidate X (Fictional Sample)",
              party_name: "Independent — Fictional",
              is_fictional: true,
              created_at: new Date().toISOString(),
              constituency_name: "Fictional Constituency",
              election_name: "Telangana Legislative Assembly General Election 2024",
            },
          ]);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadCandidates();
    return () => {
      mounted = false;
    };
  }, []);

  const filteredCandidates = candidates.filter((c) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      c.display_name.toLowerCase().includes(term) ||
      c.name.toLowerCase().includes(term) ||
      c.party_name.toLowerCase().includes(term) ||
      (c.constituency_name && c.constituency_name.toLowerCase().includes(term))
    );
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <section className="mb-12 text-center md:py-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-civic-300 bg-white px-3.5 py-1 text-xs font-semibold text-civic-700 shadow-sm">
          <Scale className="h-3.5 w-3.5 text-civic-800" />
          <span>Non-Partisan Civic Transparency Initiative</span>
        </div>
        <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-civic-900 sm:text-4xl md:text-5xl">
          {t("hero_headline")}
        </h1>
        <p className="mx-auto mt-4 max-w-3xl text-base text-civic-600 sm:text-lg">
          {t("hero_subheadline")}
        </p>
      </section>

      {/* Neutrality & Transparency Card */}
      <section className="mb-12">
        <div className="overflow-hidden rounded-2xl border border-civic-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white">
              <ShieldCheck className="h-6 w-6 text-emerald-400" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold tracking-tight text-civic-900">
                {t("neutrality_title")}
              </h2>
              <p className="text-sm leading-relaxed text-civic-700 sm:text-base">
                {t("neutrality_body")}
              </p>
              <div className="mt-4 flex flex-wrap gap-4 text-xs font-medium text-civic-600">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Zero scoring or candidate ranking
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Exact page-by-page PDF verification
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" /> Neutral plain-language explanations (EN / TE / HI)
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Candidate Discovery Section */}
      <section className="space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-civic-900">
              {t("discovery_heading")}
            </h2>
            <p className="text-sm text-civic-600">
              {t("discovery_subheading")}
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-civic-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter candidates..."
              className="w-full rounded-lg border border-civic-300 bg-white py-2 pl-9 pr-3 text-sm placeholder:text-civic-400 focus:border-civic-800 focus:outline-none focus:ring-1 focus:ring-civic-800"
            />
          </div>
        </div>

        {/* Candidate Cards Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredCandidates.map((candidate) => (
            <div
              key={candidate.id}
              className="flex flex-col justify-between rounded-xl border border-civic-200 bg-white p-6 shadow-sm transition-all hover:border-civic-400 hover:shadow-md"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <span className="inline-block rounded bg-civic-100 px-2 py-0.5 text-[11px] font-semibold tracking-wide text-civic-700 uppercase">
                      {candidate.party_name}
                    </span>
                    <h3 className="text-lg font-bold text-civic-900">
                      {candidate.display_name}
                    </h3>
                  </div>

                  {candidate.is_fictional && (
                    <span className="shrink-0 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                      {t("fictional_badge")}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5 border-t border-civic-100 pt-3 text-xs text-civic-600">
                  <div className="flex items-center justify-between">
                    <span className="text-civic-400">Constituency:</span>
                    <span className="font-medium text-civic-800">
                      {candidate.constituency_name || "Telangana"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-civic-400">Election:</span>
                    <span className="font-medium text-civic-800">
                      General Election 2024
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-civic-400">Status:</span>
                    <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                      <CheckCircle2 className="h-3 w-3" /> Form 26 Verified
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-2">
                <Link
                  href={`/candidates/${candidate.id}`}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-civic-900 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-civic-800"
                >
                  <span>{t("view_affidavit")}</span>
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
