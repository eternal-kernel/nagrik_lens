"use client";

import { useState, useRef, useEffect, ChangeEvent, DragEvent } from "react";
import Link from "next/link";
import { useLanguage } from "@/lib/language-context";
import { scanPosterImage, PosterScanResponse, CandidateMatchItem } from "@/lib/api";
import {
  Camera,
  UploadCloud,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  RefreshCw,
  FileText,
  Search,
  Eye,
  ArrowLeft,
  X,
  Sparkles,
  Info,
  Scale,
  Video,
  Landmark,
} from "lucide-react";

export default function PosterScannerPage() {
  const { t } = useLanguage();

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [result, setResult] = useState<PosterScanResponse | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showRawOcr, setShowRawOcr] = useState(false);
  const [isCameraActive, setIsCameraActive] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Clean up media streams on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      setCameraError(null);
      setError(null);

      if (!navigator?.mediaDevices?.getUserMedia) {
        setCameraError(t("scan_camera_denied"));
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });

      streamRef.current = stream;
      setIsCameraActive(true);

      // Connect stream to video element once state re-renders
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch((playErr) => {
            console.warn("Video play error:", playErr);
          });
        }
      }, 50);
    } catch (err: any) {
      console.warn("Camera access denied or failed:", err);
      setIsCameraActive(false);
      setCameraError(t("scan_camera_denied"));
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
  };

  const captureFrame = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;

    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setError("Failed to initialize canvas for capture.");
      stopCamera();
      return;
    }

    ctx.drawImage(video, 0, 0, width, height);

    // Stop camera stream immediately upon capture
    stopCamera();

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          setError("Failed to create image file from camera capture.");
          return;
        }
        const capturedFile = new File([blob], `camera_scan_${Date.now()}.jpg`, {
          type: "image/jpeg",
        });
        await handleFileSelect(capturedFile);
      },
      "image/jpeg",
      0.92
    );
  };

  const handleFileSelect = async (selectedFile: File) => {
    // Basic client validation
    if (!selectedFile.type.startsWith("image/")) {
      setError("Please select a valid image file (JPEG, PNG, WebP).");
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("Image file exceeds maximum permitted size of 10 MB.");
      return;
    }

    // Stop camera if still running
    stopCamera();

    // Clean up previous preview URL
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setPreviewUrl(objectUrl);
    setError(null);
    setCameraError(null);
    setResult(null);

    // Automatically trigger scan for a smooth camera-to-result experience
    await performScan(selectedFile);
  };

  const performScan = async (targetFile: File) => {
    try {
      setScanning(true);
      setError(null);
      const scanResponse = await scanPosterImage(targetFile);
      setResult(scanResponse);
    } catch (err: any) {
      console.error("Poster scan failed:", err);
      setError(
        err.message ||
          "Failed to scan poster. Please ensure the backend API server is running and try again."
      );
    } finally {
      setScanning(false);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleClear = () => {
    stopCamera();
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setCameraError(null);
    setShowRawOcr(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  const formatConfidence = (val: number): string => {
    return `${Math.round(val * 100)}%`;
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Breadcrumb / Back Navigation */}
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-civic-600 transition hover:text-civic-900"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{t("back_to_candidates")}</span>
        </Link>
      </div>

      {/* Header Section */}
      <div className="mb-8 space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50/80 px-3.5 py-1 text-xs font-bold text-indigo-800 shadow-sm">
          <Camera className="h-3.5 w-3.5 text-indigo-600" />
          <span>{t("scan_title")}</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-civic-900 sm:text-4xl">
          {t("scan_title")}
        </h1>
        <p className="max-w-3xl text-sm leading-relaxed text-civic-600 sm:text-base">
          {t("scan_subtitle")}
        </p>
      </div>

      {/* Strict Civic Privacy & Neutrality Guarantee Notice */}
      <div className="mb-8 rounded-xl border border-emerald-200 bg-emerald-50/80 p-4 text-xs leading-relaxed text-emerald-900 sm:p-5 sm:text-sm">
        <div className="flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 shrink-0 text-emerald-600 sm:mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2 font-bold text-emerald-950">
              <span>{t("scan_privacy_badge")}</span>
              <span className="rounded bg-emerald-200/80 px-1.5 py-0.2 text-[10px] font-semibold text-emerald-800 uppercase">
                Privacy Guaranteed
              </span>
            </div>
            <p className="text-emerald-800">
              {t("scan_privacy_notice")}
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Upload & Preview on Left, Results on Right */}
      <div className="grid gap-8 lg:grid-cols-12">
        {/* Left Column: Image Dropzone & Preview (5 cols) */}
        <div className="space-y-6 lg:col-span-5">
          <div className="overflow-hidden rounded-2xl border border-civic-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 text-base font-bold text-civic-900">
              {t("scan_dropzone_title")}
            </h2>

            {/* Hidden file inputs */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleInputChange}
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
            />
            <input
              type="file"
              ref={cameraInputRef}
              onChange={handleInputChange}
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              className="hidden"
            />

            {/* Camera Permission Denied Warning */}
            {cameraError && !isCameraActive && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                  <div className="space-y-1">
                    <p className="font-semibold">{cameraError}</p>
                    <p className="text-[11px] text-amber-800">
                      You can select a photo directly from your library or files below.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* View 1: Active Live Camera Viewfinder */}
            {isCameraActive ? (
              <div className="space-y-4">
                <div className="relative overflow-hidden rounded-xl border border-civic-900 bg-black shadow-inner">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="max-h-96 w-full object-cover"
                  />

                  {/* Viewfinder Target Overlay */}
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
                    <div className="relative h-4/5 w-4/5 rounded-lg border-2 border-dashed border-white/60 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]">
                      <div className="absolute -top-1 -left-1 h-4 w-4 border-t-2 border-l-2 border-emerald-400" />
                      <div className="absolute -top-1 -right-1 h-4 w-4 border-t-2 border-r-2 border-emerald-400" />
                      <div className="absolute -bottom-1 -left-1 h-4 w-4 border-b-2 border-l-2 border-emerald-400" />
                      <div className="absolute -bottom-1 -right-1 h-4 w-4 border-b-2 border-r-2 border-emerald-400" />
                    </div>
                  </div>

                  {/* Blinking Live Indicator */}
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-[10px] font-bold tracking-wide text-white backdrop-blur-sm">
                    <span className="h-2 w-2 animate-ping rounded-full bg-emerald-400" />
                    <span>LIVE CAMERA</span>
                  </div>
                </div>

                {/* Camera Actions */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={captureFrame}
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-600 py-3 text-xs font-bold text-white shadow-md transition hover:bg-emerald-700"
                  >
                    <Camera className="h-4 w-4" />
                    <span>{t("scan_capture_btn")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={stopCamera}
                    className="flex items-center justify-center gap-1.5 rounded-xl border border-civic-300 bg-white px-4 py-3 text-xs font-semibold text-civic-700 transition hover:bg-civic-50"
                  >
                    <X className="h-4 w-4 text-civic-500" />
                    <span>{t("scan_cancel_camera")}</span>
                  </button>
                </div>
              </div>
            ) : !previewUrl ? (
              /* View 2: Drag & Drop Dropzone + Camera Button */
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all ${
                  isDragging
                    ? "border-indigo-500 bg-indigo-50/60"
                    : "border-civic-300 bg-civic-50/50 hover:border-civic-400 hover:bg-civic-50"
                }`}
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-civic-200">
                  <UploadCloud className="h-7 w-7 text-indigo-600" />
                </div>
                <h3 className="mt-4 text-sm font-bold text-civic-900">
                  {t("scan_dropzone_title")}
                </h3>
                <p className="mt-1.5 max-w-xs text-xs text-civic-500">
                  {t("scan_dropzone_desc")}
                </p>

                {/* Primary Camera & Upload Action Buttons */}
                <div className="mt-5 flex flex-wrap justify-center gap-2.5">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      startCamera();
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-indigo-800"
                  >
                    <Video className="h-3.5 w-3.5" />
                    <span>{t("scan_live_camera")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-civic-300 bg-white px-3.5 py-2 text-xs font-semibold text-civic-700 shadow-sm transition hover:bg-civic-50"
                  >
                    <UploadCloud className="h-3.5 w-3.5" />
                    <span>Browse Files</span>
                  </button>
                </div>
              </div>
            ) : (
              /* View 3: Image Preview with Clear / Scan Another */
              <div className="space-y-4">
                <div className="relative overflow-hidden rounded-xl border border-civic-200 bg-civic-900/5">
                  <img
                    src={previewUrl}
                    alt="Poster preview"
                    className="max-h-96 w-full object-contain"
                  />
                  {scanning && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-civic-900/60 p-4 text-white backdrop-blur-sm">
                      <RefreshCw className="h-8 w-8 animate-spin text-white" />
                      <p className="mt-3 text-center text-xs font-semibold tracking-wide">
                        {t("scan_scanning")}
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between gap-3 pt-1">
                  <div className="truncate text-xs text-civic-500">
                    <span className="font-semibold text-civic-700">{file?.name}</span>
                    {file?.size && ` (${(file.size / 1024).toFixed(1)} KB)`}
                  </div>
                  <button
                    type="button"
                    onClick={handleClear}
                    disabled={scanning}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-civic-300 bg-white px-3 py-1.5 text-xs font-semibold text-civic-700 transition hover:bg-civic-50 disabled:opacity-50"
                  >
                    <X className="h-3.5 w-3.5 text-civic-500" />
                    <span>{t("scan_clear")}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Results & Disambiguation Panel (7 cols) */}
        <div className="space-y-6 lg:col-span-7">
          {/* Scanning Skeleton / Loader */}
          {scanning && (
            <div className="rounded-2xl border border-civic-200 bg-white p-8 text-center shadow-sm">
              <RefreshCw className="mx-auto h-10 w-10 animate-spin text-indigo-600" />
              <h3 className="mt-4 text-lg font-bold text-civic-900">
                {t("scan_scanning")}
              </h3>
              <p className="mt-1 text-xs text-civic-500">
                Running in-memory OCR text extraction and fuzzy matching against verified candidates...
              </p>
            </div>
          )}

          {/* Error Banner */}
          {error && !scanning && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 shrink-0 text-rose-600" />
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-rose-900">{t("scan_error_title")}</h4>
                  <p className="text-xs text-rose-700">{error}</p>
                  <button
                    type="button"
                    onClick={() => file && performScan(file)}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-rose-900 underline hover:text-rose-950"
                  >
                    <RefreshCw className="h-3 w-3" />
                    <span>Retry Scanning</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Empty Prompt Before Upload / While Camera is Active */}
          {!scanning && !result && !error && (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-civic-300 bg-white p-12 text-center shadow-sm">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-civic-100 text-civic-500">
                <Search className="h-7 w-7 text-civic-600" />
              </div>
              <h3 className="mt-4 text-base font-bold text-civic-900">
                {isCameraActive ? "Point Camera at Street Poster" : "Ready to Scan Poster"}
              </h3>
              <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-civic-500">
                {isCameraActive
                  ? "Align the campaign flexi-banner within the viewfinder frame and tap 'Capture & Scan'."
                  : "Photograph or upload any campaign flexi-banner. We will extract text and match it against our database of verified Form 26 sworn affidavits."}
              </p>
            </div>
          )}

          {/* Results: Once Scanning is Complete */}
          {result && !scanning && (
            <div className="space-y-6">
              {/* CASE 1: Single High-Confidence Match */}
              {!result.requires_disambiguation && result.matches.length === 1 && (
                <div className="overflow-hidden rounded-2xl border border-emerald-200 bg-white shadow-sm">
                  {/* Status Banner */}
                  <div className="flex items-center justify-between border-b border-emerald-100 bg-emerald-50 px-5 py-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      <span className="text-xs font-bold text-emerald-900">
                        {t("scan_single_match_title")}
                      </span>
                    </div>
                    <span className="rounded-full bg-emerald-600 px-2.5 py-0.5 text-xs font-bold text-white shadow-sm">
                      {formatConfidence(result.matches[0].confidence)} Match
                    </span>
                  </div>

                  {/* Candidate Card Content */}
                  <div className="p-6">
                    <CandidateCard candidate={result.matches[0]} t={t} isPrimary />
                  </div>
                </div>
              )}

              {/* CASE 2: Multiple Candidates / Disambiguation Picker */}
              {result.requires_disambiguation && result.matches.length > 1 && (
                <div className="overflow-hidden rounded-2xl border border-amber-300 bg-white shadow-sm">
                  {/* Disambiguation Alert Header */}
                  <div className="border-b border-amber-200 bg-amber-50 px-5 py-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" />
                      <div className="space-y-1">
                        <h3 className="text-sm font-bold text-amber-950 sm:text-base">
                          {t("scan_multi_match_title")}
                        </h3>
                        <p className="text-xs text-amber-800 sm:text-sm">
                          {t("scan_multi_match_prompt")}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Multi-Candidate Grid */}
                  <div className="grid gap-4 p-5 sm:grid-cols-2">
                    {result.matches.map((cand) => (
                      <div
                        key={cand.candidate_id}
                        className="rounded-xl border border-civic-200 bg-civic-50/50 p-4 transition-all hover:border-civic-400 hover:bg-white hover:shadow-md"
                      >
                        <CandidateCard candidate={cand} t={t} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CASE 3: Single Match with Moderate Confidence (< 0.75) requiring confirmation */}
              {result.requires_disambiguation && result.matches.length === 1 && (
                <div className="overflow-hidden rounded-2xl border border-amber-300 bg-white shadow-sm">
                  <div className="border-b border-amber-200 bg-amber-50 px-5 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-600" />
                        <span className="text-xs font-bold text-amber-900">
                          Moderate Confidence Match
                        </span>
                      </div>
                      <span className="rounded-full bg-amber-600 px-2.5 py-0.5 text-xs font-bold text-white shadow-sm">
                        {formatConfidence(result.matches[0].confidence)} Match
                      </span>
                    </div>
                  </div>

                  <div className="p-6">
                    <p className="mb-4 text-xs text-amber-800">
                      We detected candidate signals with moderate similarity. Please verify if this matches your street poster:
                    </p>
                    <CandidateCard candidate={result.matches[0]} t={t} isPrimary />
                  </div>
                </div>
              )}

              {/* CASE 4: Zero Matches */}
              {result.matches.length === 0 && (
                <div className="rounded-2xl border border-civic-200 bg-white p-8 text-center shadow-sm">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-civic-100 text-civic-500">
                    <Search className="h-6 w-6 text-civic-600" />
                  </div>
                  <h3 className="mt-4 text-base font-bold text-civic-900">
                    {t("scan_no_match_title")}
                  </h3>
                  <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-civic-600">
                    {result.message || t("scan_no_match_desc")}
                  </p>

                  <div className="mt-6">
                    <Link
                      href="/"
                      className="inline-flex items-center gap-1.5 rounded-lg bg-civic-900 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-civic-800"
                    >
                      <Search className="h-3.5 w-3.5" />
                      <span>{t("scan_manual_search_btn")}</span>
                    </Link>
                  </div>
                </div>
              )}

              {/* Detected Context Summary Pills */}
              {(result.detected_party || result.detected_constituency) && (
                <div className="flex flex-wrap items-center gap-2 rounded-xl border border-civic-200 bg-white p-3 text-xs text-civic-600 shadow-sm">
                  <span className="font-semibold text-civic-800">Detected Signals:</span>
                  {result.detected_constituency && (
                    <span className="rounded-md bg-civic-100 px-2 py-0.5 font-medium text-civic-800">
                      Constituency: {result.detected_constituency}
                    </span>
                  )}
                  {result.detected_party && (
                    <span className="rounded-md bg-indigo-50 px-2 py-0.5 font-medium text-indigo-800">
                      Party: {result.detected_party}
                    </span>
                  )}
                </div>
              )}

              {/* Transparency Accordion: Inspect Raw OCR Text */}
              <div className="rounded-xl border border-civic-200 bg-white shadow-sm">
                <button
                  type="button"
                  onClick={() => setShowRawOcr(!showRawOcr)}
                  className="flex w-full items-center justify-between p-4 text-left text-xs font-bold text-civic-800 transition hover:bg-civic-50"
                >
                  <div className="flex items-center gap-2">
                    <Eye className="h-4 w-4 text-civic-600" />
                    <span>{t("scan_raw_ocr_title")}</span>
                  </div>
                  <span className="text-civic-400">
                    {showRawOcr ? "Hide ▲" : "Inspect ▼"}
                  </span>
                </button>

                {showRawOcr && (
                  <div className="border-t border-civic-100 p-4 text-xs text-civic-700">
                    <p className="mb-2 text-[11px] text-civic-500">
                      {t("scan_raw_ocr_desc")}
                    </p>
                    <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-lg border border-civic-200 bg-civic-50 p-3 font-mono text-[11px] leading-relaxed text-civic-800">
                      {result.ocr_text || "(No text recognized)"}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Reusable Candidate Card for single and multi-candidate match views.
 */
function CandidateCard({
  candidate,
  t,
  isPrimary = false,
}: {
  candidate: CandidateMatchItem;
  t: (key: string, params?: Record<string, string | number>) => string;
  isPrimary?: boolean;
}) {
  return (
    <div className="flex h-full flex-col justify-between space-y-4">
      <div className="space-y-2.5">
        {/* Header badges */}
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          <span className="inline-block rounded bg-civic-100 px-2 py-0.5 text-[11px] font-semibold text-civic-700 uppercase">
            {candidate.party_name}
          </span>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 ring-1 ring-emerald-200">
            {Math.round(candidate.confidence * 100)}% match
          </span>
        </div>

        {/* Candidate Name */}
        <div>
          <h4 className="text-base font-bold text-civic-900 sm:text-lg">
            {candidate.display_name}
          </h4>
          <p className="text-xs text-civic-500">
            Constituency:{" "}
            <span className="font-semibold text-civic-700">
              {candidate.constituency_name}
              {candidate.constituency_code ? ` (${candidate.constituency_code})` : ""}
            </span>
          </p>
        </div>

        {/* Matched Signal Tags */}
        {candidate.matched_terms && candidate.matched_terms.length > 0 && (
          <div className="space-y-1 pt-1 text-[11px]">
            <span className="text-civic-400 font-medium">Matched Signals:</span>
            <div className="flex flex-wrap gap-1">
              {candidate.matched_terms.map((term, idx) => (
                <span
                  key={idx}
                  className="rounded bg-civic-100/80 px-1.5 py-0.5 text-[10px] font-mono text-civic-700"
                >
                  {term}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 5-Year Public Record Preview Strip */}
        {candidate.five_year_preview && (
          <div className="pt-2">
            {candidate.five_year_preview.is_incumbent ? (
              <div className="space-y-2 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-1.5">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-950">
                    <Landmark className="h-3.5 w-3.5 text-emerald-700" />
                    <span>{t("label_incumbent")}</span>
                  </div>
                  {candidate.five_year_preview.prior_office_held && (
                    <span className="text-[11px] font-medium text-emerald-800">
                      {candidate.five_year_preview.prior_office_held}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-0.5 text-[11px]">
                  {candidate.five_year_preview.works_completed != null &&
                    candidate.five_year_preview.works_recommended != null && (
                      <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-civic-800 shadow-xs ring-1 ring-civic-200/80">
                        <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                        <span className="font-bold">
                          {candidate.five_year_preview.works_completed}/
                          {candidate.five_year_preview.works_recommended}
                        </span>{" "}
                        {t("label_works_completed")}
                      </span>
                    )}

                  {candidate.five_year_preview.attendance_pct != null && (
                    <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-civic-800 shadow-xs ring-1 ring-civic-200/80">
                      <span className="font-bold">
                        {candidate.five_year_preview.attendance_pct}%
                      </span>{" "}
                      {t("label_attendance")}
                    </span>
                  )}
                </div>

                <div className="pt-1">
                  <Link
                    href={`/candidates/${candidate.candidate_id}?tab=record`}
                    className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-800 hover:text-emerald-950 underline underline-offset-2 transition"
                  >
                    <span>{t("btn_view_five_year_record")}</span>
                  </Link>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-[11px] font-medium text-slate-600">
                <Info className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                <span>{t("label_first_time_contestant")}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Button */}
      <div className="pt-2">
        <Link
          href={`/candidates/${candidate.candidate_id}`}
          className={`flex w-full items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-semibold text-white transition-all shadow-sm ${
            isPrimary
              ? "bg-civic-900 hover:bg-civic-800 text-sm py-3"
              : "bg-civic-800 hover:bg-civic-900"
          }`}
        >
          <span>{t("view_affidavit")}</span>
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
