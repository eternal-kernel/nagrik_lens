import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/lib/language-context";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Nagrik Lens — Neutral ECI Form 26 Affidavit Explanations",
  description:
    "Plain-language, source-linked explanations of Indian election candidate ECI Form 26 affidavits in English, Telugu, and Hindi.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col font-sans antialiased">
        <LanguageProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-civic-200 bg-white py-6 text-center text-xs text-civic-500">
            <div className="mx-auto max-w-7xl px-4">
              <p className="font-medium text-civic-600">
                Nagrik Lens — Civic Information Initiative
              </p>
              <p className="mt-1">
                Data strictly sourced from sworn Form 26 candidate affidavits filed with the Election Commission of India (ECI).
              </p>
            </div>
          </footer>
        </LanguageProvider>
      </body>
    </html>
  );
}
