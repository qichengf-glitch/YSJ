import React from "react";

interface SectionProps {
  children: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
}

export default function Section({
  children,
  className = "",
  fullWidth = false,
}: SectionProps) {
  return (
    <section className={`py-16 sm:py-20 lg:py-24 ${className}`}>
      <div
        className={`${
          fullWidth ? "w-full" : "max-w-7xl mx-auto"
        } px-6 sm:px-8 lg:px-12`}
      >
        {children}
      </div>
    </section>
  );
}
