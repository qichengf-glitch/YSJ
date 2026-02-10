export type Sentiment = "Bullish" | "Bearish" | "Neutral";

export type AuthorBadge = "Contributor" | "Analyst" | "Verified";

export interface Author {
  id: string;
  username: string;
  badge: AuthorBadge;
}

export interface ThesisPost {
  id: string;
  title: string;
  excerpt: string;
  body: string;
  author: Author;
  createdAt: string;
  readingTime: string;
  tags: string[];
  tickers: string[];
  sentiment: Sentiment;
  score: number;
  commentsCount: number;
}

export interface Comment {
  id: string;
  postId: string;
  parentId?: string | null;
  author: Author;
  body: string;
  createdAt: string;
  score: number;
}

