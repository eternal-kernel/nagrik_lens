"use client";

import React, { useEffect, useState } from "react";
import { Volume2, VolumeX, AlertCircle } from "lucide-react";
import { SupportedLang, useLanguage } from "@/lib/language-context";

interface VoiceButtonProps {
  text: string;
  lang: SupportedLang;
}

export default function VoiceButton({ text, lang }: VoiceButtonProps) {
  const { t } = useLanguage();
  const [isPlaying, setIsPlaying] = useState(false);
  const [showNotice, setShowNotice] = useState(false);

  useEffect(() => {
    // Stop speech if lang or component changes
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [lang]);

  const handleTogglePlay = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setShowNotice(true);
      setTimeout(() => setShowNotice(false), 4000);
      return;
    }

    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // BCP 47 language tag
    const langTag = lang === "te" ? "te-IN" : lang === "hi" ? "hi-IN" : "en-IN";
    utterance.lang = langTag;
    utterance.rate = 0.95; // Clear civic speaking rate

    // Look for matching voice
    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find(
      (v) =>
        v.lang === langTag ||
        v.lang.replace("_", "-").startsWith(lang) ||
        (lang === "en" && v.lang.startsWith("en"))
    );

    if (matchedVoice) {
      utterance.voice = matchedVoice;
    } else if (lang !== "en" && !voices.some((v) => v.lang.startsWith(lang))) {
      // Browser does not have a native voice for te or hi
      setShowNotice(true);
      setTimeout(() => setShowNotice(false), 4500);
    }

    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);

    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  };

  return (
    <div className="relative inline-flex items-center">
      <button
        onClick={handleTogglePlay}
        className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
          isPlaying
            ? "border border-red-300 bg-red-50 text-red-700 hover:bg-red-100"
            : "border border-civic-300 bg-white text-civic-700 hover:border-civic-400 hover:bg-civic-50"
        }`}
        title={isPlaying ? t("btn_stop") : t("btn_listen")}
        aria-label={isPlaying ? t("btn_stop") : t("btn_listen")}
      >
        {isPlaying ? (
          <>
            <VolumeX className="h-3.5 w-3.5 text-red-600 animate-pulse" />
            <span>{t("btn_stop")}</span>
          </>
        ) : (
          <>
            <Volume2 className="h-3.5 w-3.5 text-civic-600" />
            <span>{t("btn_listen")}</span>
          </>
        )}
      </button>

      {showNotice && (
        <div className="absolute bottom-full left-0 z-50 mb-1.5 w-60 rounded-md border border-amber-200 bg-amber-50 p-2 text-[11px] leading-tight text-amber-900 shadow-md animate-fadeIn">
          <div className="flex items-start gap-1.5">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 text-amber-600 mt-0.5" />
            <span>{t("voice_fallback")}</span>
          </div>
        </div>
      )}
    </div>
  );
}
