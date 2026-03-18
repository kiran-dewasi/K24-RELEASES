import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Only use static export for production builds, not dev mode
  ...(process.env.NODE_ENV === 'production' && { output: 'export' }),
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
