import { createHash } from "node:crypto";
import { lstat, readdir, readFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import postcss from "postcss";

const cssDirectoryPath = fileURLToPath(new URL("../dist/assets/", import.meta.url));
const indexPath = fileURLToPath(new URL("../dist/index.html", import.meta.url));

// A finite presence check; browser consumers own cascade and visual semantics.
const requiredUtilityWitnesses = [
  [".grid"],
  [".min-h-screen"],
  [".rounded-2xl"],
  [".rounded-xl"],
  [".shadow-sm"],
  [
    ".space-y-4",
    ".space-y-4>:not([hidden])~:not([hidden])",
    ":where(.space-y-4>:not(:last-child))",
  ],
  [".md\\:grid-cols-2"],
  [".bg-\\[var\\(--color-primary\\)\\]"],
  [".focus-visible\\:outline-2", ".focus-visible\\:outline-2:focus-visible"],
];

export function assertTailwindUtilities(css) {
  const selectors = new Set();
  postcss.parse(css).walkRules((rule) => {
    for (const selector of postcss.list.comma(rule.selector)) {
      selectors.add(selector.trim());
    }
  });
  const missing = requiredUtilityWitnesses
    .filter((alternatives) => !alternatives.some((selector) => selectors.has(selector)))
    .map(([selector]) => selector);
  if (missing.length > 0) {
    throw new Error(`Built CSS bundle is missing Tailwind selectors: ${missing.join(", ")}`);
  }
}

async function findBuiltCssFile() {
  const files = await readdir(cssDirectoryPath);
  const cssFiles = files.filter((fileName) => /^index-[A-Za-z0-9_-]+\.css$/.test(fileName));
  if (cssFiles.length !== 1) {
    throw new Error(`Expected one built frontend index CSS bundle; found ${cssFiles.length}.`);
  }
  const cssFile = join(cssDirectoryPath, cssFiles[0]);
  const [cssStat, indexStat] = await Promise.all([lstat(cssFile), lstat(indexPath)]);
  if (!cssStat.isFile() || cssStat.isSymbolicLink() || !indexStat.isFile() || indexStat.isSymbolicLink()) {
    throw new Error("Built frontend index and CSS must be regular files.");
  }
  const index = await readFile(indexPath);
  const indexText = index.toString("utf8");
  // Bind the exact existing Vite entry-link format, not a general HTML grammar.
  const entryStyles = [...indexText.matchAll(/<link\b[^>]*\shref="(\/assets\/index-[A-Za-z0-9_-]+\.css)"[^>]*>/g)]
    .map((match) => ({ href: match[1], relations: [...match[0].matchAll(/\srel="([^"]*)"/g)] }));
  if (entryStyles.length !== 1 || entryStyles[0].href !== `/assets/${cssFiles[0]}` ||
      entryStyles[0].relations.length !== 1 || entryStyles[0].relations[0][1] !== "stylesheet") {
    throw new Error("Built frontend index must reference the unique current index CSS bundle.");
  }
  return { cssFile, index };
}

async function main() {
  const { cssFile, index } = await findBuiltCssFile();
  const css = await readFile(cssFile);
  assertTailwindUtilities(css.toString("utf8"));
  const sha256 = (value) => createHash("sha256").update(value).digest("hex");
  console.log(`PASS: finite exact Tailwind selectors in ${cssFile}; CSS sha256:${sha256(css)}; index sha256:${sha256(index)}`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
