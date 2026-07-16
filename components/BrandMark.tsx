import Link from "next/link";

type BrandMarkProps = {
  href?: string;
  className?: string;
  size?: "nav" | "footer" | "page";
};

const sizeClass = {
  nav: "text-[1.4rem] leading-none",
  footer: "text-[1.55rem] leading-none",
  page: "text-4xl leading-none sm:text-5xl",
};

export default function BrandMark({
  href = "/",
  className = "",
  size = "nav",
}: BrandMarkProps) {
  const mark = (
    <span
      className={`inline-flex items-baseline font-brand font-extrabold tracking-[-0.045em] text-[#18233A] ${sizeClass[size]} ${className}`}
    >
      <span>YSJ</span>
      <span className="bg-[linear-gradient(120deg,#4F63F6_0%,#273B9A_100%)] bg-clip-text text-transparent">
        Lab
      </span>
    </span>
  );

  if (!href) {
    return mark;
  }

  return (
    <Link href={href} className="inline-flex items-center transition hover:opacity-85">
      {mark}
    </Link>
  );
}
