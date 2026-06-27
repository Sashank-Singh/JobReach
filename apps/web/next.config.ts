import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  output: "standalone",
  // Monorepo local dev only — omitted in Docker (DOCKER_BUILD=1) so standalone lands at .next/standalone/
  ...(process.env.DOCKER_BUILD !== "1" && {
    outputFileTracingRoot: path.join(__dirname, "../.."),
  }),
};

export default nextConfig;
