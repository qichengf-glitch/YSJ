import React from "react";
import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/contexts/LanguageContext";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  metadataBase: new URL("https://www.ysjlab.com"),
  title: "YSJ Lab - Financial Research & Strategy",
  description: "Independent financial research and strategy studio",
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
    <html lang="en">
      <body
        className="font-sans"
        style={
          {
            "--font-playfair": "'Playfair Display', Georgia, serif",
          } as React.CSSProperties
        }
      >
        <LanguageProvider>
          <Navbar />
          {children}
        </LanguageProvider>
      </body>
    </html>
  );
}
