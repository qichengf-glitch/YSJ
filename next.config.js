const tickStockPanelOrigin = (
  process.env.TICK_STOCK_PANEL_ORIGIN ||
  process.env.TICK_STOCK_PANEL_URL ||
  "http://35.77.76.249:3018"
).replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [
        {
          source: "/tick-panel",
          destination: `${tickStockPanelOrigin}/`,
        },
        {
          source: "/tick-panel/:path*",
          destination: `${tickStockPanelOrigin}/:path*`,
        },
        {
          source: "/assets/:path*",
          destination: `${tickStockPanelOrigin}/assets/:path*`,
        },
        {
          source: "/favicon.svg",
          destination: `${tickStockPanelOrigin}/favicon.svg`,
        },
      ],
    };
  },
};

module.exports = nextConfig;
