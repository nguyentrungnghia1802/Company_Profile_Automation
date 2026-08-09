const apiProxyTarget = process.env.API_PROXY_TARGET || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
      {
        source: "/favicon.ico",
        destination: "/icon.svg",
      },
    ];
  },
};

module.exports = nextConfig;
