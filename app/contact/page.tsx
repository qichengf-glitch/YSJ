"use client";

import { FormEvent, useState } from "react";
import { Mail, Send } from "lucide-react";
import BrandMark from "@/components/BrandMark";
import { useLanguage } from "@/contexts/LanguageContext";

const CONTACT_EMAIL = "contact@ysjlab.com";

const content = {
  en: {
    eyebrow: "Contact",
    title: "Get in touch",
    subtitle:
      "Questions about research, partnerships, or private access? Send us a note and we will get back to you.",
    name: "Name",
    email: "Your email",
    subject: "Subject",
    message: "Message",
    namePlaceholder: "Your name",
    emailPlaceholder: "you@company.com",
    subjectPlaceholder: "How can we help?",
    messagePlaceholder: "Write your message…",
    send: "Open email draft",
    direct: "Or email us directly",
    required: "Please fill in email, subject, and message.",
  },
  zh: {
    eyebrow: "联系我们",
    title: "保持联系",
    subtitle: "研究合作、商务洽谈或 Private Access 相关问题，欢迎来信。",
    name: "姓名",
    email: "你的邮箱",
    subject: "主题",
    message: "留言",
    namePlaceholder: "你的姓名",
    emailPlaceholder: "you@company.com",
    subjectPlaceholder: "想咨询什么？",
    messagePlaceholder: "写下你的留言…",
    send: "打开邮件草稿",
    direct: "或直接发邮件",
    required: "请填写邮箱、主题和留言。",
  },
};

export default function ContactPage() {
  const { language } = useLanguage();
  const t = content[language];
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim() || !subject.trim() || !message.trim()) {
      setError(t.required);
      return;
    }

    setError("");
    const body = [
      name.trim() ? `Name: ${name.trim()}` : null,
      `From: ${email.trim()}`,
      "",
      message.trim(),
    ]
      .filter(Boolean)
      .join("\n");

    const mailto = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
      subject.trim()
    )}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
  };

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)] px-6 py-16 sm:px-8 lg:px-12">
      <div className="mx-auto grid max-w-5xl gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#4F63F6]">
            {t.eyebrow}
          </p>
          <h1 className="mt-3 text-4xl font-black tracking-tight text-[#18233A] sm:text-5xl">
            {t.title}
          </h1>
          <p className="mt-4 max-w-md text-lg leading-8 text-[#5B6780]">{t.subtitle}</p>

          <div className="mt-8 rounded-2xl border border-[#E7ECF5] bg-white p-6 shadow-[0_12px_30px_rgba(39,59,154,0.06)]">
            <BrandMark size="footer" />
            <p className="mt-4 text-sm font-semibold text-[#5B6780]">{t.direct}</p>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="mt-2 inline-flex items-center gap-2 text-base font-bold text-[#4F63F6] hover:underline"
            >
              <Mail className="h-4 w-4" />
              {CONTACT_EMAIL}
            </a>
          </div>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-[#E7ECF5] bg-white p-6 shadow-[0_18px_40px_rgba(39,59,154,0.07)] sm:p-8"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-semibold text-[#18233A]">
              {t.name}
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t.namePlaceholder}
                className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] px-3 text-sm outline-none transition focus:border-[#A8B2FF] focus:bg-white"
              />
            </label>
            <label className="block text-sm font-semibold text-[#18233A]">
              {t.email}
              <input
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder={t.emailPlaceholder}
                className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] px-3 text-sm outline-none transition focus:border-[#A8B2FF] focus:bg-white"
              />
            </label>
          </div>

          <label className="mt-4 block text-sm font-semibold text-[#18233A]">
            {t.subject}
            <input
              required
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              placeholder={t.subjectPlaceholder}
              className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] px-3 text-sm outline-none transition focus:border-[#A8B2FF] focus:bg-white"
            />
          </label>

          <label className="mt-4 block text-sm font-semibold text-[#18233A]">
            {t.message}
            <textarea
              required
              rows={6}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={t.messagePlaceholder}
              className="mt-2 w-full resize-y rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] px-3 py-3 text-sm outline-none transition focus:border-[#A8B2FF] focus:bg-white"
            />
          </label>

          {error ? <p className="mt-3 text-sm font-medium text-red-600">{error}</p> : null}

          <button
            type="submit"
            className="mt-6 inline-flex h-12 items-center justify-center rounded-full bg-[#4F63F6] px-6 text-sm font-bold text-white shadow-[0_14px_28px_rgba(79,99,246,0.24)] transition hover:bg-[#273B9A]"
          >
            {t.send}
            <Send className="ml-2 h-4 w-4" />
          </button>
        </form>
      </div>
    </main>
  );
}
