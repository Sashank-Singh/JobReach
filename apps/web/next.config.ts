import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";
import path from "path";

const nextConfig = (phase: string): NextConfig => {
  const isDev = phase === PHASE_DEVELOPMENT_SERVER;

  return {
    ...(!isDev && {
      output: "standalone" as const,
      // Monorepo local builds only; omitted in Docker so standalone lands at .next/standalone.
      ...(process.env.DOCKER_BUILD !== "1" && {
        outputFileTracingRoot: path.join(__dirname, "../.."),
      }),
    }),
  };
};

export default nextConfig;
