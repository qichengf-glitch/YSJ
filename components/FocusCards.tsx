import Image from "next/image";
import Link from "next/link";

const items = [
  {
    title: "Research",
    description:
      "Independent macro research and structured analysis for long-term capital allocation.",
    href: "/research",
    image:
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
    alt: "Hands pointing at financial report with charts",
  },
  {
    title: "Strategy",
    description:
      "Systematic strategies across equities, commodities, options, and global markets.",
    href: "/strategy",
    image:
      "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
    alt: "Hand with stylus on candlestick charts display",
  },
  {
    title: "Prediction Markets",
    description:
      "Data-driven positioning in event-driven markets with disciplined risk control.",
    href: "/prediction-markets",
    image:
      "https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1200&q=80",
    alt: "Person holding tablet with financial dashboard",
  },
  {
    title: "Ongoing Thesis",
    description:
      "Current research projects and investment theses under development with community-driven frameworks.",
    href: "/research/ongoing-thesis",
    image:
      "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1200&q=80",
    alt: "Analyst reviewing ongoing thesis notes and market data",
  },
];

export default function FocusCards() {
  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-7">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-label={`${item.title} - Explore`}
          className="group relative flex flex-col overflow-hidden rounded-2xl bg-[#f7fbff] border border-slate-200 shadow-[0_10px_30px_rgba(15,23,42,0.06)] transition-all duration-300 ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary hover:-translate-y-1 hover:shadow-[0_18px_40px_rgba(15,23,42,0.12)]"
        >
          <div className="relative aspect-[16/9] w-full overflow-hidden">
            <Image
              src={item.image}
              alt={item.alt}
              fill
              sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
              className="object-cover transition-transform duration-300 ease-out group-hover:scale-105"
              priority
            />
          </div>

          <div className="flex min-h-[200px] flex-1 flex-col gap-3 px-7 py-6">
            <h3 className="text-2xl font-semibold text-slate-900">{item.title}</h3>
            <p className="line-clamp-2 text-base text-slate-600 leading-relaxed">
              {item.description}
            </p>
            <span className="mt-auto text-sm font-medium text-primary inline-flex items-center gap-1">
              Explore <span aria-hidden="true">→</span>
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
