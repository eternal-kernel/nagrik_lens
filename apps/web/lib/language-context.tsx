"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import enMessages from "@/messages/en.json";
import teMessages from "@/messages/te.json";
import hiMessages from "@/messages/hi.json";

export type SupportedLang = "en" | "te" | "hi";

const messagesMap: Record<SupportedLang, Record<string, string>> = {
  en: enMessages,
  te: teMessages,
  hi: hiMessages,
};

interface LanguageContextType {
  lang: SupportedLang;
  setLang: (lang: SupportedLang) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextType>({
  lang: "en",
  setLang: () => {},
  t: (key) => key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<SupportedLang>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("nagrik_lang") as SupportedLang | null;
    if (saved && (saved === "en" || saved === "te" || saved === "hi")) {
      setLangState(saved);
    }
  }, []);

  const setLang = (newLang: SupportedLang) => {
    setLangState(newLang);
    if (typeof window !== "undefined") {
      localStorage.setItem("nagrik_lang", newLang);
    }
  };

  const t = (key: string, params?: Record<string, string | number>): string => {
    const dict = messagesMap[lang] || messagesMap.en;
    let text = dict[key] || messagesMap.en[key] || key;
    if (params) {
      Object.entries(params).forEach(([pKey, pVal]) => {
        text = text.replace(new RegExp(`\\{${pKey}\\}`, "g"), String(pVal));
      });
    }
    return text;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
