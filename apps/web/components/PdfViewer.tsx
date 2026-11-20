"use client";

import React, { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Loader2,
  FileCheck,
} from "lucide-react";

interface PdfViewerProps {
  pdfUrl: string;
  currentPage: number;
  onPageChange: (newPage: number) => void;
  inspectingBadgeText?: string | null;
}

export default function PdfViewer({
  pdfUrl,
  currentPage,
  onPageChange,
  inspectingBadgeText,
}: PdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(1.15);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const renderTaskRef = useRef<any>(null);

  // Set worker source once
  useEffect(() => {
    pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
  }, []);

  // Load PDF Document
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const loadingTask = pdfjsLib.getDocument(pdfUrl);
    loadingTask.promise
      .then((doc) => {
        if (!active) return;
        setPdfDoc(doc);
        setTotalPages(doc.numPages);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        console.error("Error loading PDF document:", err);
        setError("Failed to load PDF affidavit from server.");
        setLoading(false);
      });

    return () => {
      active = false;
      loadingTask.destroy();
    };
  }, [pdfUrl]);

  // Render Current Page
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;

    let isCancelled = false;

    // Cancel any ongoing rendering task
    if (renderTaskRef.current) {
      renderTaskRef.current.cancel();
      renderTaskRef.current = null;
    }

    const renderPage = async () => {
      try {
        const page = await pdfDoc.getPage(currentPage);
        if (isCancelled || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const context = canvas.getContext("2d");
        if (!context) return;

        const viewport = page.getViewport({ scale: zoom });

        // High DPI canvas support
        const pixelRatio = window.devicePixelRatio || 1;
        canvas.width = viewport.width * pixelRatio;
        canvas.height = viewport.height * pixelRatio;
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;

        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        const task = page.render(renderContext);
        renderTaskRef.current = task;
        await task.promise;
      } catch (err: any) {
        if (err?.name !== "RenderingCancelledException") {
          console.error("PDF rendering error:", err);
        }
      }
    };

    renderPage();

    return () => {
      isCancelled = true;
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
    };
  }, [pdfDoc, currentPage, zoom]);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.15, 2.0));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.15, 0.7));
  const handleZoomReset = () => setZoom(1.15);

  return (
    <div className="flex h-full flex-col rounded-xl border border-civic-200 bg-civic-100/50 shadow-sm">
      {/* Top Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-civic-200 bg-white px-4 py-2.5">
        {/* Page navigation */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1 || loading}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-civic-200 bg-white text-civic-700 transition hover:bg-civic-50 disabled:opacity-40"
            title="Previous Page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="min-w-[90px] text-center text-xs font-semibold text-civic-800">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= totalPages || loading}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-civic-200 bg-white text-civic-700 transition hover:bg-civic-50 disabled:opacity-40"
            title="Next Page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-civic-200 bg-white text-civic-700 transition hover:bg-civic-50"
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="min-w-[48px] text-center text-xs font-medium text-civic-600">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-civic-200 bg-white text-civic-700 transition hover:bg-civic-50"
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={handleZoomReset}
            className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded-md border border-civic-200 bg-white text-civic-700 transition hover:bg-civic-50"
            title="Reset Zoom"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Source Excerpt Inspecting Banner */}
      {inspectingBadgeText && (
        <div className="flex items-center gap-2 border-b border-indigo-100 bg-indigo-50/90 px-4 py-2 text-xs font-semibold text-indigo-900 animate-fadeIn">
          <FileCheck className="h-4 w-4 shrink-0 text-indigo-600" />
          <span className="truncate">{inspectingBadgeText}</span>
        </div>
      )}

      {/* PDF Canvas Viewport Container */}
      <div
        ref={containerRef}
        className="relative flex flex-1 items-center justify-center overflow-auto p-4 md:p-6"
        style={{ minHeight: "520px" }}
      >
        {loading && (
          <div className="flex flex-col items-center gap-2 text-civic-500">
            <Loader2 className="h-8 w-8 animate-spin text-civic-600" />
            <span className="text-xs font-medium">Rendering affidavit page {currentPage}...</span>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-xs text-red-700">
            {error}
          </div>
        )}

        <div className={`${loading || error ? "hidden" : "block"} transition-all`}>
          <canvas
            ref={canvasRef}
            className="rounded-lg border border-civic-300 bg-white shadow-md transition-all"
          />
        </div>
      </div>
    </div>
  );
}
