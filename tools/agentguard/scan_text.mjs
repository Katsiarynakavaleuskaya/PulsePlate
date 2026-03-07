#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { SkillScanner } from "@goplus/agentguard";

function sanitizeFilename(filename) {
  const fallback = "payload.py";
  if (typeof filename !== "string" || filename.trim() === "") {
    return fallback;
  }
  return filename.replace(/[^a-zA-Z0-9._-]/g, "_") || fallback;
}

function normalizeScanResult(result) {
  const nested = result?.goPlus ?? result?.scanSummary ?? result ?? {};
  const riskLevel =
    typeof nested?.risk_level === "string"
      ? nested.risk_level
      : typeof nested?.riskLevel === "string"
        ? nested.riskLevel
        : "safe";
  const riskTags = Array.isArray(nested?.risk_tags)
    ? nested.risk_tags.filter((tag) => typeof tag === "string")
    : Array.isArray(nested?.riskTags)
      ? nested.riskTags.filter((tag) => typeof tag === "string")
      : [];
  const summary =
    typeof nested?.summary === "string"
      ? nested.summary
      : typeof nested?.message === "string"
        ? nested.message
        : "";

  return {
    risk_level: riskLevel,
    risk_tags: riskTags,
    summary,
  };
}

async function readStdinJson() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return JSON.parse(raw);
}

async function main() {
  const payload = await readStdinJson();
  const text = typeof payload?.text === "string" ? payload.text : "";
  const filename = sanitizeFilename(payload?.filename);
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "pulseplate-agentguard-"));
  const targetFile = path.join(tmpDir, filename);

  try {
    await fs.writeFile(targetFile, text, "utf8");

    const scanner = new SkillScanner({
      useExternalScanner: false,
      deep: false,
    });
    const result = await scanner.quickScan(tmpDir);
    process.stdout.write(JSON.stringify(normalizeScanResult(result)));
  } finally {
    await fs.rm(tmpDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
