import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const cssDirectory = new URL("../dist/assets/", import.meta.url);
const requiredSelectors = [".grid", ".min-h-screen", ".rounded-2xl"];

async function findBuiltCssFile() {
  const files = await readdir(cssDirectory);
  const cssFiles = files.filter((fileName) => /^index-.*\.css$/.test(fileName)).sort();

  if (cssFiles.length === 0) {
    throw new Error("No built frontend CSS bundle found in dist/assets.");
  }

  return join(cssDirectory.pathname, cssFiles[cssFiles.length - 1]);
}

const cssFile = await findBuiltCssFile();
const css = await readFile(cssFile, "utf8");
const missingSelectors = requiredSelectors.filter((selector) => {
  return !css.includes(selector);
});

if (missingSelectors.length > 0) {
  throw new Error(
    `Built CSS bundle is missing Tailwind selectors: ${missingSelectors.join(", ")}`
  );
}

console.log(`PASS: Tailwind utility selectors found in ${cssFile}`);
