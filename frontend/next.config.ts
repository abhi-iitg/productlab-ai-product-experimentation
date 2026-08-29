import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Playwright drives the dev server via 127.0.0.1 (see playwright.config.ts);
  // without this, Next.js blocks its own HMR requests as cross-origin.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
