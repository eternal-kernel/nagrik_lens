"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useLanguage } from "@/lib/language-context";
import {
  getCandidateDetail,
  getAffidavitDisclosures,
  getAffidavitPdfUrl,
  CandidateDetail,
  RenderedDisclosure,
} from "@/lib/api";
import PdfViewer from "@/components/PdfViewer";
import VoiceButton from "@/components/VoiceButton";
import LegalGlossaryPill from "@/components/LegalGlossaryPill";
import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  FileText,
  Landmark,
  GraduationCap,
  Coins,
  Building2,
  CreditCard,
  AlertOctagon,
  Scale,
  Sparkles,
  ExternalLink,
} from "lucide-react";

export default function CandidateAffidavitPage() {
  const params = useParams();
  const candidateId = params.id as string;
  const { lang, t } = useLanguage();

  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [disclosures, setDisclosures] = useState<RenderedDisclosure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // PDF Viewer navigation state
  const [currentPdfPage, setCurrentPdfPage] = useState<number>(1);
  const [activeInspectingBadge, setActiveInspectingBadge] = useState<string | null>(null);
  const [activeDisclosureId, setActiveDisclosureId] = useState<number | null>(null);

  // Load candidate details
  useEffect(() => {
    let mounted = true;
    async function loadCandidate() {
      try {
        setLoading(true);
        setError(null);
        const candData = await getCandidateDetail(candidateId);
        if (mounted) {
          setCandidate(candData);
        }
      } catch (err: any) {
        if (mounted) {
          console.error("Failed to load candidate:", err);
          setError("Failed to load candidate data. Please ensure the backend is running.");
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadCandidate();
    return () => {
      mounted = false;
    };
  }, [candidateId]);

  // Load disclosures whenever active affidavit or language changes
  useEffect(() => {
    if (!candidate || candidate.affidavits.length === 0) return;

    const affidavitId = candidate.affidavits[0].id;
    let mounted = true;

    async function loadDisclosures() {
      try {
        const discs = await getAffidavitDisclosures(affidavitId, lang);
        if (mounted) {
          setDisclosures(discs);
        }
      } catch (err) {
        console.error("Failed to load disclosures:", err);
      }
    }
    loadDisclosures();

    return () => {
      mounted = false;
    };
  }, [candidate, lang]);

  const affidavit = candidate?.affidavits?.[0];
  const pdfUrl = affidavit ? getAffidavitPdfUrl(affidavit.id) : "";

  // Category Icon & Label mapping
  const getCategoryMeta = (category: string) => {
    switch (category) {
      case "education":
        return {
          label: t("cat_education"),
          icon: GraduationCap,
          color: "text-blue-700 bg-blue-50 border-blue-200",
        };
      case "movable_assets":
        return {
          label: t("cat_movable_assets"),
          icon: Coins,
          color: "text-emerald-700 bg-emerald-50 border-emerald-200",
        };
      case "immovable_assets":
        return {
          label: t("cat_immovable_assets"),
          icon: Building2,
          color: "text-teal-700 bg-teal-50 border-teal-200",
        };
      case "liabilities":
        return {
          label: t("cat_liabilities"),
          icon: CreditCard,
          color: "text-amber-700 bg-amber-50 border-amber-200",
        };
      case "pending_criminal_cases":
        return {
          label: t("cat_pending_criminal_cases"),
          icon: AlertOctagon,
          color: "text-rose-700 bg-rose-50 border-rose-200",
        };
      case "convictions":
        return {
          label: t("cat_convictions"),
          icon: Scale,
          color: "text-indigo-700 bg-indigo-50 border-indigo-200",
        };
      default:
        return {
          label: category,
          icon: FileText,
          color: "text-civic-700 bg-civic-50 border-civic-200",
        };
    }
  };

  const getSubjectLabel = (subject: string) => {
    switch (subject) {
      case "self":
        return t("subj_self");
      case "spouse":
        return t("subj_spouse");
      case "huf":
        return t("subj_huf");
      case "dependent_1":
        return t("subj_dependent_1");
      case "dependent_2":
        return t("subj_dependent_2");
      case "dependent_3":
        return t("subj_dependent_3");
      case "joint":
        return t("subj_joint");
      default:
        return subject;
    }
  };

  const handleInspectPage = (pageNumber: number, category: string, disclosureId: number) => {
    setCurrentPdfPage(pageNumber);
    setActiveDisclosureId(disclosureId);
    const meta = getCategoryMeta(category);
    setActiveInspectingBadge(`Inspecting Source: Page ${pageNumber} (${meta.label})`);

    // On mobile, scroll up to the PDF viewer
    if (window.innerWidth < 1024) {
      const viewerEl = document.getElementById("pdf-viewer-section");
      if (viewerEl) {
        viewerEl.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8 text-civic-600">
        <p className="text-sm font-medium animate-pulse">{t("loading")}</p>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-800">
          <p className="text-sm font-semibold">{error || t("error_loading")}</p>
          <Link
            href="/"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-red-900 underline hover:no-underline"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>{t("back_to_candidates")}</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Fictional Sample Banner */}
      {candidate.is_fictional && (
        <div className="mb-6 flex items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs font-bold tracking-wide text-amber-900 shadow-sm">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
          <span>{t("fictional_banner")}</span>
        </div>
      )}

      {/* Candidate Header Summary */}
      <div className="mb-6 space-y-3 rounded-2xl border border-civic-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-civic-600 transition hover:text-civic-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>{t("back_to_candidates")}</span>
          </Link>

          {affidavit && (
            <div className="flex items-center gap-1.5 text-xs text-civic-500">
              <Calendar className="h-3.5 w-3.5" />
              <span>
                {t("historical_notice", { date: affidavit.filing_date })}
              </span>
            </div>
          )}
        </div>

        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end border-t border-civic-100 pt-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="rounded bg-civic-100 px-2.5 py-0.5 text-xs font-semibold text-civic-700 uppercase tracking-wider">
                {candidate.party_name}
              </span>
              <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                {t("status_verified")}
              </span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-civic-900 sm:text-3xl">
              {candidate.display_name}
            </h1>
            <p className="text-xs text-civic-600">
              {candidate.constituency.name} ({candidate.constituency.code}), {candidate.constituency.state} • {candidate.election?.name || "General Election 2024"}
            </p>
          </div>
        </div>
      </div>

      {/* Main 2-Column Split Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
        {/* LEFT PANEL: Affidavit PDF Viewer */}
        <section
          id="pdf-viewer-section"
          className="lg:col-span-6 lg:sticky lg:top-20 space-y-2"
        >
          <div className="flex items-center justify-between px-1">
            <h2 className="flex items-center gap-1.5 text-sm font-bold text-civic-900">
              <FileText className="h-4 w-4 text-civic-700" />
              <span>{t("pdf_panel_title")}</span>
            </h2>
            <span className="text-[11px] text-civic-500">
              Official ECI Form 26
            </span>
          </div>

          <div className="h-[620px] lg:h-[750px]">
            {pdfUrl ? (
              <PdfViewer
                pdfUrl={pdfUrl}
                currentPage={currentPdfPage}
                onPageChange={(p) => setCurrentPdfPage(p)}
                inspectingBadgeText={activeInspectingBadge}
              />
            ) : (
              <div className="flex h-full items-center justify-center rounded-xl border border-civic-200 bg-white p-8 text-center text-xs text-civic-500">
                Affidavit PDF document not available.
              </div>
            )}
          </div>
        </section>

        {/* RIGHT PANEL: Verified Plain-Language Explanations */}
        <section className="lg:col-span-6 space-y-4">
          <div className="border-b border-civic-200 pb-3">
            <h2 className="text-lg font-bold tracking-tight text-civic-900">
              {t("explanations_panel_title")}
            </h2>
            <p className="text-xs text-civic-600">
              {t("explanations_panel_subtitle")}
            </p>
          </div>

          {/* Disclosure Cards List */}
          <div className="space-y-4">
            {disclosures.map((disc) => {
              const meta = getCategoryMeta(disc.category);
              const CategoryIcon = meta.icon;
              const isSelected = activeDisclosureId === disc.id;

              return (
                <article
                  key={disc.id}
                  className={`relative rounded-xl border bg-white p-5 shadow-sm transition-all duration-200 ${
                    isSelected
                      ? "border-civic-800 ring-2 ring-civic-800/10 shadow-md"
                      : "border-civic-200 hover:border-civic-300"
                  }`}
                >
                  {/* Card Header: Category & Subject Badge */}
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-bold ${meta.color}`}>
                        <CategoryIcon className="h-3.5 w-3.5" />
                        <span>{meta.label}</span>
                      </div>
                      <span className="rounded-md bg-civic-100 px-2 py-0.5 text-xs font-semibold text-civic-700">
                        {getSubjectLabel(disc.subject_type)}
                      </span>
                    </div>

                    {/* Voice "Listen" Button */}
                    <VoiceButton text={disc.explanation} lang={lang} />
                  </div>

                  {/* Verified Plain-Language Explanation */}
                  <div className="text-sm leading-relaxed text-civic-900 font-normal">
                    {disc.explanation}
                  </div>

                  {/* Expandable Legal Glossary (For Pending Criminal Cases) */}
                  {disc.glossary_items && disc.glossary_items.length > 0 && (
                    <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50/50 p-3">
                      <div className="mb-2 text-[11px] font-bold tracking-wide text-blue-900 uppercase">
                        {t("legal_glossary_heading")}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {disc.glossary_items.map((item) => (
                          <LegalGlossaryPill key={item.code_key} item={item} />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Card Footer: Page Jump / Inspect Source Button */}
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-civic-100 pt-3">
                    <button
                      onClick={() => handleInspectPage(disc.page_number, disc.category, disc.id)}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                        isSelected && currentPdfPage === disc.page_number
                          ? "bg-civic-900 text-white"
                          : "border border-civic-200 bg-civic-50 text-civic-800 hover:bg-civic-100"
                      }`}
                    >
                      <FileText className="h-3.5 w-3.5" />
                      <span>{t("btn_inspect_page", { page: disc.page_number })}</span>
                    </button>

                    <span className="text-[11px] text-civic-500 font-medium">
                      Sworn declaration on Page {disc.page_number}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
