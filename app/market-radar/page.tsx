import { redirect } from "next/navigation";

export const metadata = {
  title: "Prediction Market | YSJ Lab",
  description: "Polymarket macro probability dashboard.",
};

export default function MarketRadarPage() {
  redirect("/prediction-markets");
}
