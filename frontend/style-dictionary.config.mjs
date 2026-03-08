import path from "node:path";
import { fileURLToPath } from "node:url";
import StyleDictionary from "style-dictionary";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");

export function createTokenDictionary() {
  return new StyleDictionary({
    source: [path.join(repoRoot, "tokens", "**", "*.json")],
  });
}

export { repoRoot };
