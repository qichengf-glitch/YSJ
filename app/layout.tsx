import React from "react";
import type { Metadata } from "next";
import { Syne } from "next/font/google";
import "./globals.css";
import { LanguageProvider } from "@/contexts/LanguageContext";
import Navbar from "@/components/Navbar";

const brandFont = Syne({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-brand",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.ysjlab.com"),
  title: "YSJLab - Quantitative Market Monitoring",
  description: "Internal market intelligence workspace for quantitative research and monitoring",
  openGraph: {
    url: "https://www.ysjlab.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={brandFont.variable}>
      <body className="font-sans">
        <LanguageProvider>
          <Navbar />
          {children}
        </LanguageProvider>
      </body>
    </html>
  );
}
