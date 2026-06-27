import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const sourceDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(sourceDir, "../..");
const outputDir = path.resolve(repoRoot, "dist/chrome-extension");

const webOrigin = requiredEnv("PUBLIC_WEB_ORIGIN");
const referralApiUrl = requiredEnv("NEXT_PUBLIC_REFERRAL_API_URL");

fs.rmSync(outputDir, { recursive: true, force: true });
fs.mkdirSync(outputDir, { recursive: true });

for (const file of ["manifest.json", "background.js", "web-bridge.js", "linkedin-content.js", "extension-utils.js"]) {
  const source = path.join(sourceDir, file);
  const destination = path.join(outputDir, file);
  const content = fs
    .readFileSync(source, "utf8")
    .replaceAll("https://app.yourdomain.com", webOrigin)
    .replaceAll("https://referrals.yourdomain.com", referralApiUrl);
  fs.writeFileSync(destination, content);
}

console.log(`Packaged Chrome extension to ${path.relative(repoRoot, outputDir)}`);

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    console.error(`Missing required env: ${name}`);
    process.exit(1);
  }
  return value.replace(/\/$/, "");
}
