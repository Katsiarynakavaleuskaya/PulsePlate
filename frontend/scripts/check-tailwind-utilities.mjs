import { createHash } from "node:crypto";
import { lstat, readdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import postcss from "postcss";

// jsdom is a declared direct dependency; use its public parse5 dependency edge.
// Do not import jsdom itself or assume its transitive dependency is hoisted.
const jsdomRequire = createRequire(createRequire(import.meta.url).resolve("jsdom"));
const { parse, ErrorCodes } = await import(pathToFileURL(jsdomRequire.resolve("parse5")).href);
if (typeof parse !== "function" || ErrorCodes?.duplicateAttribute !== "duplicate-attribute") {
  throw new Error("Required public parse5 HTML parser API is unavailable.");
}

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

// Document-tree membership only; no resource loading, script execution or CSS application.
export function assertBuiltCssEntry(indexText, cssFileName) {
  const message = "Built frontend index must reference the unique current index CSS bundle.";
  const duplicates = [];
  const document = parse(indexText, {
    scriptingEnabled: true,
    sourceCodeLocationInfo: true,
    onParseError: (error) => {
      if (error.code === ErrorCodes.duplicateAttribute) duplicates.push(error);
    },
  });
  const links = [];
  function visit(node) {
    if (node.namespaceURI === "http://www.w3.org/1999/xhtml" && node.tagName === "link") {
      links.push(node);
    }
    // Template content is a separate inert fragment, never a document child.
    for (const child of node.childNodes ?? []) visit(child);
  }
  visit(document);
  const inRange = (location, emptyAllowed = false) =>
    Number.isInteger(location?.startOffset) && Number.isInteger(location?.endOffset) &&
    location.startOffset >= 0 && location.endOffset <= indexText.length &&
    (emptyAllowed ? location.endOffset >= location.startOffset : location.endOffset > location.startOffset);
  const ranges = [];
  for (const link of links) {
    const location = link.sourceCodeLocation;
    // Public parse5 locations for void elements may omit optional startTag.
    const startTag = location?.startTag === undefined ? location : location.startTag;
    if (!inRange(location) || !inRange(startTag) || location.endTag !== undefined ||
        startTag.startOffset !== location.startOffset || startTag.endOffset > location.endOffset) {
      throw new Error(`${message} HTML link source location is unavailable or ambiguous.`);
    }
    ranges.push(startTag);
  }
  // Attribute normalization discards duplicates, so bind diagnostics before attrs projection.
  for (const error of duplicates) {
    if (!inRange(error, true)) {
      throw new Error(`${message} Duplicate-attribute source location is unavailable.`);
    }
    const owners = ranges.filter((range) => error.startOffset >= range.startOffset &&
      error.startOffset < range.endOffset && error.endOffset <= range.endOffset);
    if (owners.length > 0) {
      throw new Error(`${message} Duplicate attributes on an HTML link are ambiguous.`);
    }
  }
  // Count actual current-index candidates before selecting only perfect witnesses.
  const candidates = links.filter((link) => link.attrs.some((attribute) =>
    attribute.name === "href" && attribute.namespace === undefined &&
    /^\/assets\/index-[A-Za-z0-9_-]+\.css$/.test(attribute.value)));
  if (candidates.length !== 1) throw new Error(message);
  const attributes = candidates[0].attrs;
  const href = attributes.find((attribute) => attribute.name === "href" && attribute.namespace === undefined);
  const rel = attributes.find((attribute) => attribute.name === "rel" && attribute.namespace === undefined);
  if (href?.value !== `/assets/${cssFileName}` || rel?.value !== "stylesheet") {
    throw new Error(message);
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
  assertBuiltCssEntry(index.toString("utf8"), cssFiles[0]);
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
