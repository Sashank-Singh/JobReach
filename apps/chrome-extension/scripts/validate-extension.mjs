import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const sourceDir = path.resolve(__dirname, "..");

const manifest = JSON.parse(fs.readFileSync(path.join(sourceDir, "manifest.json"), "utf8"));
const requiredFiles = [
  "background.js",
  "web-bridge.js",
  "linkedin-content.js",
  "extension-utils.js",
];

if (manifest.manifest_version !== 3) throw new Error("Expected Manifest V3");
for (const file of requiredFiles) {
  if (!fs.existsSync(path.join(sourceDir, file))) throw new Error(`Missing ${file}`);
}
if (!manifest.host_permissions?.some((p) => p.includes("linkedin.com"))) {
  throw new Error("Missing LinkedIn host permission");
}
