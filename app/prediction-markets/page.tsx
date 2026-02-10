"use client";

import Section from "@/components/Section";
import { useLanguage } from "@/contexts/LanguageContext";

const content = {
  en: {
    title: "Prediction Markets",
    text: "Prediction Markets – Coming Soon. We are exploring structured approaches to probabilistic forecasting.",
  },
  zh: {
    title: "预测市场",
    text: "预测市场 – 即将推出。我们正在探索基于概率的结构化预测方法。",
  },
};

export default function PredictionMarkets() {
  const { language } = useLanguage();
  const t = content[language as "en" | "zh"];

  return (
    <main className="min-h-screen pt-16">
      <Section className="pt-8">
        <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 mb-8">
          {t.title}
        </h1>
        <p className="text-xl sm:text-2xl text-gray-600 leading-relaxed max-w-3xl">
          {t.text}
        </p>
      </Section>
    </main>
  );
}
