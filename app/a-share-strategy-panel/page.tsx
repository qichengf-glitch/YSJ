import { permanentRedirect } from "next/navigation";

export const metadata = {
  title: "Chanlun Panel | YSJ Lab",
  description: "Chanlun Panel",
};

export default function AShareStrategyPanelPage() {
  permanentRedirect("https://chanlun.ysjfund.com");
}
