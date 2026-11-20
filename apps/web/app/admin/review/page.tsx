"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  getAdminAffidavitDisclosures,
  patchAdminDisclosure,
  getAffidavitPdfUrl,
  AdminDisclosureRead,
  ReviewEvent,
} from "@/lib/api";
import PdfViewer from "@/components/PdfViewer";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  KeyRound,
  RotateCw,
  ExternalLink,
  Clock,
  History,
  FileCheck,
  Check,
  Send,
  AlertCircle,
  ArrowRight,
} from "lucide-react";

export default function AdminReviewPage() {
  const [adminKey, setAdminKey] = useState<string>("dev-secret-key");
  const [affidavitId, setAffidavitId] = useState<number>(1);
  const [disclosures, setDisclosures] = useState<AdminDisclosureRead[]>([]);
  const [selectedDisclosure, setSelectedDisclosure] = useState<AdminDisclosureRead | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<{ message: string; candidateId: number } | null>(null);

  // Editor form state
  const [editPageNumber, setEditPageNumber] = useState<number>(1);
  const [editJsonText, setEditJsonText] = useState<string>("");
  const [jsonParseError, setJsonParseError] = useState<string | null>(null);
  const [reviewerName, setReviewerName] = useState<string>("Demo Reviewer");
  const [reviewNote, setReviewNote] = useState<string>("");
  const [currentPdfPage, setCurrentPdfPage] = useState<number>(1);

  // Fetch disclosures for the affidavit
  const fetchDisclosures = async (targetAffidavitId: number = affidavitId, keyToUse: string = adminKey) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAdminAffidavitDisclosures(targetAffidavitId, keyToUse);
      setDisclosures(data);

      // Auto-select first needs_review item, or the first item
      if (data.length > 0) {
        const priorityItem = data.find((d) => d.verification_status === "needs_review") || data[0];
        handleSelectDisclosure(priorityItem);
      } else {
        setSelectedDisclosure(null);
      }
    } catch (err: any) {
      console.error("Failed to load admin disclosures:", err);
      setError(err.message || "Failed to authenticate or fetch disclosures.");
      setDisclosures([]);
      setSelectedDisclosure(null);
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchDisclosures(1, "dev-secret-key");
  }, []);

  const handleSelectDisclosure = (disc: AdminDisclosureRead) => {
    setSelectedDisclosure(disc);
    setEditPageNumber(disc.page_number);
    setCurrentPdfPage(disc.page_number);
    setEditJsonText(JSON.stringify(disc.structured_value, null, 2));
    setJsonParseError(null);
    setReviewNote("");
  };

  const handleAction = async (targetStatus: "verified" | "needs_review" | "rejected") => {
    if (!selectedDisclosure) return;

    // Validate JSON
    let parsedJson: Record<string, any>;
    try {
      parsedJson = JSON.parse(editJsonText);
      setJsonParseError(null);
    } catch (err: any) {
      setJsonParseError(`JSON Syntax Error: ${err.message}`);
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const payload = {
        verification_status: targetStatus,
        page_number: editPageNumber,
        structured_value: parsedJson,
        reviewer_name: reviewerName.trim() || "Demo Reviewer",
        review_note:
          reviewNote.trim() ||
          `Status changed to '${targetStatus}' via Human-Verification Review Console`,
      };

      const updated = await patchAdminDisclosure(selectedDisclosure.id, payload, adminKey);

      // Refresh disclosures list
      const refreshedDisclosures = disclosures.map((d) =>
        d.id === updated.id ? updated : d
      );
      setDisclosures(refreshedDisclosures);
      setSelectedDisclosure(updated);

      setSuccessBanner({
        message: `Disclosure #${updated.id} (${updated.category}) successfully updated to "${targetStatus}".`,
        candidateId: 1,
      });

      // Clear review note for next action
      setReviewNote("");
    } catch (err: any) {
      console.error("Failed to patch disclosure:", err);
      setError(err.message || "Failed to update disclosure.");
    } finally {
      setSubmitting(false);
    }
  };

  // Sort disclosures: 'needs_review' at top, then by page and id
  const sortedDisclosures = [...disclosures].sort((a, b) => {
    if (a.verification_status === "needs_review" && b.verification_status !== "needs_review") {
      return -1;
    }
    if (a.verification_status !== "needs_review" && b.verification_status === "needs_review") {
      return 1;
    }
    return a.page_number - b.page_number || a.id - b.id;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "needs_review":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-bold text-amber-800">
            <AlertTriangle className="h-3 w-3 text-amber-600" />
            Needs Review
          </span>
        );
      case "verified":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
            Verified
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-rose-300 bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-800">
            <XCircle className="h-3 w-3 text-rose-600" />
            Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-civic-300 bg-civic-50 px-2.5 py-0.5 text-xs font-semibold text-civic-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Top Header & Admin Auth Bar */}
      <div className="mb-6 rounded-2xl border border-civic-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-civic-900">
                Human-Verification Review Console
              </h1>
              <span className="rounded bg-civic-100 px-2 py-0.5 text-[10px] font-semibold text-civic-700 uppercase tracking-wide">
                Local Dev Mode
              </span>
            </div>
            <p className="text-xs text-civic-600">
              Review and verify candidate sworn disclosures against official Form 26 PDF source pages.
            </p>
          </div>

          {/* Admin Key & Action Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <KeyRound className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-civic-400" />
              <input
                type="password"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                placeholder="X-Admin-Key"
                className="rounded-lg border border-civic-300 bg-white py-1.5 pl-8 pr-3 text-xs font-mono text-civic-800 focus:border-civic-800 focus:outline-none focus:ring-1 focus:ring-civic-800"
              />
            </div>

            <button
              onClick={() => fetchDisclosures(affidavitId, adminKey)}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-civic-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-civic-800 disabled:opacity-50"
            >
              <RotateCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Load Affidavit #{affidavitId}</span>
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-800">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
        )}

        {/* Success Banner */}
        {successBanner && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900 animate-fadeIn">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 shrink-0 text-emerald-600" />
              <span className="font-semibold">{successBanner.message}</span>
            </div>
            <Link
              href={`/candidates/${successBanner.candidateId}`}
              className="inline-flex items-center gap-1 font-bold text-emerald-800 underline hover:no-underline"
            >
              <span>View Updated Public Affidavit View</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </div>

      {/* Main 2-Column Split Workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
        {/* LEFT PANEL: Reused PDF Viewer */}
        <section className="lg:col-span-6 lg:sticky lg:top-20 space-y-2">
          <div className="flex items-center justify-between px-1">
            <h2 className="flex items-center gap-1.5 text-sm font-bold text-civic-900">
              <FileText className="h-4 w-4 text-civic-700" />
              <span>Original Sworn Form 26 PDF</span>
            </h2>
            <span className="text-[11px] text-civic-500 font-medium">
              Candidate X Affidavit
            </span>
          </div>

          <div className="h-[620px] lg:h-[760px]">
            <PdfViewer
              pdfUrl={getAffidavitPdfUrl(affidavitId)}
              currentPage={currentPdfPage}
              onPageChange={(p) => setCurrentPdfPage(p)}
              inspectingBadgeText={
                selectedDisclosure
                  ? `Inspecting Disclosure #${selectedDisclosure.id}: Page ${selectedDisclosure.page_number} (${selectedDisclosure.category})`
                  : null
              }
            />
          </div>
        </section>

        {/* RIGHT PANEL: Disclosure Queue & Inline Verification Editor */}
        <section className="lg:col-span-6 space-y-6">
          {/* Disclosure Selection List */}
          <div className="rounded-2xl border border-civic-200 bg-white p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-civic-100 pb-2.5">
              <h2 className="text-sm font-bold text-civic-900">
                Disclosures Queue ({disclosures.length})
              </h2>
              <span className="text-[11px] text-civic-500">
                Select an item to verify
              </span>
            </div>

            <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
              {sortedDisclosures.map((disc) => {
                const isSelected = selectedDisclosure?.id === disc.id;
                const isNeedsReview = disc.verification_status === "needs_review";

                return (
                  <button
                    key={disc.id}
                    onClick={() => handleSelectDisclosure(disc)}
                    className={`flex w-full items-center justify-between rounded-lg border p-2.5 text-left text-xs transition-all ${
                      isSelected
                        ? "border-civic-900 bg-civic-900 text-white shadow-sm"
                        : isNeedsReview
                        ? "border-amber-300 bg-amber-50/70 text-civic-900 hover:bg-amber-100/60"
                        : "border-civic-200 bg-civic-50/50 text-civic-800 hover:bg-civic-100/70"
                    }`}
                  >
                    <div className="space-y-0.5 truncate pr-2">
                      <div className="flex items-center gap-1.5 font-bold">
                        <span>#{disc.id}</span>
                        <span className="uppercase tracking-wide">{disc.category}</span>
                        <span className="font-normal opacity-80">({disc.subject_type})</span>
                      </div>
                      <p className={`truncate text-[11px] ${isSelected ? "text-civic-200" : "text-civic-500"}`}>
                        Page {disc.page_number} • {disc.field_key}
                      </p>
                    </div>

                    <div className="shrink-0">
                      {isSelected ? (
                        <span className="rounded bg-white/20 px-2 py-0.5 text-[10px] font-bold text-white uppercase">
                          Active
                        </span>
                      ) : (
                        getStatusBadge(disc.verification_status)
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Inline Verification Editor */}
          {selectedDisclosure ? (
            <div className="rounded-2xl border border-civic-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-civic-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-civic-900">
                    Editing Disclosure #{selectedDisclosure.id}
                  </span>
                  {getStatusBadge(selectedDisclosure.verification_status)}
                </div>
                <span className="text-xs font-semibold text-civic-600">
                  {selectedDisclosure.category} ({selectedDisclosure.subject_type})
                </span>
              </div>

              {/* Source Excerpt from Form 26 */}
              <div className="rounded-lg border border-civic-200 bg-civic-50 p-3 text-xs">
                <span className="block font-bold text-civic-700 text-[11px] uppercase tracking-wide mb-1">
                  Raw Affidavit Source Excerpt (Page {selectedDisclosure.page_number}):
                </span>
                <p className="font-mono text-civic-800 leading-relaxed bg-white border border-civic-200 p-2 rounded">
                  {selectedDisclosure.raw_excerpt || "No raw excerpt recorded"}
                </p>
              </div>

              {/* Current Plain-Language Explanation Preview */}
              <div className="rounded-lg border border-blue-100 bg-blue-50/60 p-3 text-xs text-blue-950">
                <span className="block font-bold text-blue-900 text-[11px] uppercase tracking-wide mb-1">
                  Active Plain-Language Explanation (EN):
                </span>
                <p className="leading-relaxed">{selectedDisclosure.explanation}</p>
              </div>

              {/* Form Controls: Page Number & Structured JSON */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <label className="text-xs font-bold text-civic-700 w-28">
                    Page Number:
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={editPageNumber}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 1;
                      setEditPageNumber(val);
                      setCurrentPdfPage(val);
                    }}
                    className="w-24 rounded-lg border border-civic-300 px-3 py-1.5 text-xs text-civic-800 focus:border-civic-800 focus:outline-none focus:ring-1 focus:ring-civic-800"
                  />
                  <span className="text-[11px] text-civic-500">
                    (PDF viewer will automatically sync to this page)
                  </span>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-bold text-civic-700">
                      Structured Value Payload (JSON):
                    </label>
                    <span className="text-[11px] text-civic-500">PostgreSQL JSONB-compatible</span>
                  </div>
                  <textarea
                    rows={6}
                    value={editJsonText}
                    onChange={(e) => setEditJsonText(e.target.value)}
                    className="w-full rounded-lg border border-civic-300 bg-civic-50/50 p-2.5 font-mono text-xs text-civic-800 focus:border-civic-800 focus:outline-none focus:ring-1 focus:ring-civic-800"
                  />
                  {jsonParseError && (
                    <p className="mt-1 text-xs font-semibold text-red-600">
                      {jsonParseError}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-bold text-civic-700 mb-1">
                      Reviewer Name:
                    </label>
                    <input
                      type="text"
                      value={reviewerName}
                      onChange={(e) => setReviewerName(e.target.value)}
                      className="w-full rounded-lg border border-civic-300 px-3 py-1.5 text-xs text-civic-800 focus:border-civic-800 focus:outline-none focus:ring-1 focus:ring-civic-800"
                      placeholder="e.g. Senior Auditor"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-civic-700 mb-1">
                      Audit Review Note:
                    </label>
                    <input
                      type="text"
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                      className="w-full rounded-lg border border-civic-300 px-3 py-1.5 text-xs text-civic-800 focus:border-civic-800 focus:outline-none focus:ring-1 focus:ring-civic-800"
                      placeholder="e.g. Bank balance verified against Schedule A"
                    />
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="border-t border-civic-100 pt-4 flex flex-wrap items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => handleAction("rejected")}
                  disabled={submitting}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3.5 py-2 text-xs font-bold text-rose-700 transition hover:bg-rose-50 disabled:opacity-50"
                >
                  <XCircle className="h-3.5 w-3.5 text-rose-600" />
                  <span>Reject</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleAction("needs_review")}
                  disabled={submitting}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3.5 py-2 text-xs font-bold text-amber-800 transition hover:bg-amber-100 disabled:opacity-50"
                >
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                  <span>Mark Needs Review</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleAction("verified")}
                  disabled={submitting}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-800 disabled:opacity-50"
                >
                  <CheckCircle2 className="h-4 w-4 text-emerald-200" />
                  <span>Verify &amp; Publish</span>
                </button>
              </div>

              {/* Audit Log (Review Events) */}
              <div className="border-t border-civic-100 pt-4 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-civic-800">
                  <History className="h-3.5 w-3.5 text-civic-600" />
                  <span>Audit History ({selectedDisclosure.review_events?.length || 0})</span>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {selectedDisclosure.review_events && selectedDisclosure.review_events.length > 0 ? (
                    selectedDisclosure.review_events.map((evt) => (
                      <div
                        key={evt.id}
                        className="rounded-lg border border-civic-200 bg-civic-50/70 p-2.5 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-[11px] text-civic-500">
                          <span className="font-bold text-civic-800">
                            {evt.reviewer_name} • {evt.action}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(evt.created_at).toLocaleString()}
                          </span>
                        </div>
                        {evt.review_note && (
                          <p className="text-civic-700 italic">"{evt.review_note}"</p>
                        )}
                        {evt.new_value && (
                          <div className="text-[10px] text-civic-500 font-mono">
                            Status: {evt.new_value.verification_status || "updated"}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-civic-400 italic">No audit events recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-2xl border border-civic-200 bg-white p-8 text-center text-xs text-civic-500">
              Select a disclosure from the queue above to open the verification editor.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
