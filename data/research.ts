/**
 * Single source of truth for academic research papers.
 * To add a new paper: drop the PDF in public/papers/ (URL-safe filename),
 * then add one entry here.
 */

export type ResearchPaper = {
  slug: string;
  title: string;
  pdfPath: string;
  category: string;
  authors: string;
  year: number;
  /** Display date e.g. "January 14, 2016" */
  publishedAt?: string;
  summary: string;
};

export const researchPapers: ResearchPaper[] = [
  {
    slug: "hierarchical-risk-parity",
    title: "Hierarchical Risk Parity",
    pdfPath: "/papers/hierarchical-risk-parity.pdf",
    category: "Portfolio Construction",
    authors: "Marc López de Prado",
    year: 2016,
    publishedAt: "March 2016",
    summary: "Hierarchical clustering approach to risk parity that improves diversification and reduces estimation error in covariance matrices.",
  },
  {
    slug: "time-series-momentum",
    title: "Time-Series Momentum",
    pdfPath: "/papers/time-series-momentum.pdf",
    category: "Trend Following",
    authors: "Moskowitz, Ooi, Pedersen",
    year: 2012,
    publishedAt: "November 2012",
    summary: "Evidence that trend-following strategies earn significant risk-adjusted returns across 58 liquid futures and forward markets.",
  },
  {
    slug: "leverage-and-tail-risk-bitcoin-sp500",
    title: "Leverage and Tail Risk in Bitcoin and the S&P 500",
    pdfPath: "/papers/leverage-and-tail-risk-in-bitcoin-and-sp500.pdf",
    category: "Crypto & Equities",
    authors: "Various",
    year: 2020,
    publishedAt: "August 2020",
    summary: "Comparative analysis of tail risk and leverage effects in Bitcoin versus traditional equity markets.",
  },
  {
    slug: "macro-investing-black-box-to-crystal-box",
    title: "Macro Investing: From Black Box to Crystal Box",
    pdfPath: "/papers/macro-investing-from-black-box-to-crystal-box.pdf",
    category: "Macro & Systematic",
    authors: "Various",
    year: 2018,
    publishedAt: "October 2018",
    summary: "Framework for making macro investing more transparent and systematic, moving from opaque discretionary processes to structured rules.",
  },
  {
    slug: "regime-based-portfolio-construction",
    title: "Regime-based Portfolio Construction",
    pdfPath: "/papers/regime-based-portfolio-construction.pdf",
    category: "Portfolio Construction",
    authors: "Various",
    year: 2019,
    publishedAt: "June 2019",
    summary: "Adaptive portfolio construction that adjusts allocations based on detected market regimes.",
  },
];
