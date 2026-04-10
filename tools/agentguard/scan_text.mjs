#!/usr/bin/env node

/**
 * RU/EN: JSON stdin contract for the local scanner bridge.
 * @typedef {{ text?: string, filename?: string }} ScannerInput
 */

/**
 * RU/EN: Allowed severity levels emitted by the local heuristic scanner.
 * @typedef {"low" | "critical"} ScanRiskLevel
 */

/**
 * RU/EN: Stable JSON result shape consumed by the Python bridge.
 * @typedef {{ risk_level: ScanRiskLevel, risk_tags: string[], summary: string }} ScanResult
 */

const ZERO_WIDTH_OR_BIDI_RE = /[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/u;
const SUSPICIOUS_ASCII_FOLDS = ["curl", "wget", "bash", "powershell", "ignore previous instructions"];
const CYRILLIC_HOMOGLYPHS = new Map([
  ["А", "A"],
  ["В", "B"],
  ["Е", "E"],
  ["К", "K"],
  ["М", "M"],
  ["Н", "H"],
  ["О", "O"],
  ["Р", "P"],
  ["С", "C"],
  ["Т", "T"],
  ["Х", "X"],
  ["а", "a"],
  ["е", "e"],
  ["о", "o"],
  ["р", "p"],
  ["с", "c"],
  ["у", "y"],
  ["х", "x"],
  ["к", "k"],
  ["м", "m"],
  ["т", "t"],
  ["в", "b"],
  ["і", "i"],
  ["ј", "j"],
  ["ѕ", "s"],
]);

const RISK_RULES = [
  {
    tag: "PROMPT_INJECTION",
    patterns: [
      /\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b/i,
      /\breveal\s+(?:the\s+)?(?:system|hidden|developer)\s+prompt\b/i,
      /\boverride\s+(?:all\s+)?safety\s+(?:rules|checks)\b/i,
      /\byou\s+are\s+now\s+(?:in\s+)?developer\s+mode\b/i,
    ],
  },
  {
    tag: "SHELL_EXEC",
    patterns: [
      /\b(?:curl|wget)\b[\s\S]{0,80}\|\s*(?:ba?sh|sh|zsh|pwsh|powershell)\b/i,
      /\b(?:bash|sh|zsh|pwsh|powershell|cmd(?:\.exe)?)\s+-[ce]\b/i,
      /\brm\s+-rf\b/i,
    ],
  },
  {
    tag: "AUTO_UPDATE",
    patterns: [/\b(?:self-?update|auto-?update|download\s+latest\s+payload)\b/i],
  },
  {
    tag: "REMOTE_LOADER",
    patterns: [/\b(?:fetch|download|load)\s+(?:remote|external)\s+(?:payload|script|binary)\b/i],
  },
  {
    tag: "SOCIAL_ENGINEERING",
    patterns: [/\b(?:disable|bypass)\s+(?:security|safety)\s+(?:checks|guardrails)\b/i],
  },
  {
    tag: "SUSPICIOUS_PASTE_URL",
    patterns: [/\bhttps?:\/\/(?:pastebin\.com|gist\.githubusercontent\.com|paste\.rs)\//i],
  },
  {
    tag: "TROJAN_DISTRIBUTION",
    patterns: [/\b(?:trojan|dropper|payload)\b[\s\S]{0,40}\b(?:download|execute|install)\b/i],
  },
];

/**
 * RU/EN: Read JSON payload from stdin and keep the bridge input contract explicit.
 * @returns {Promise<ScannerInput>}
 */
async function readStdinJson() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return JSON.parse(raw);
}

/**
 * RU/EN: Reject malformed bridge payloads so the scanner fails closed on invalid stdin.
 * @param {unknown} payload
 * @returns {{ text: string, filename?: string }}
 */
function requireScannerInput(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("Scanner input must be a JSON object.");
  }

  if (typeof payload.text !== "string") {
    throw new Error("Scanner input field 'text' must be a string.");
  }

  if ("filename" in payload && payload.filename != null && typeof payload.filename !== "string") {
    throw new Error("Scanner input field 'filename' must be a string when provided.");
  }

  return payload;
}

/**
 * RU/EN: Normalize text before applying heuristic detection rules.
 * @param {string} text
 * @returns {string}
 */
function normalizeForDetection(text) {
  const normalized = text.normalize("NFKC");
  return [...normalized]
    .map((character) => CYRILLIC_HOMOGLYPHS.get(character) ?? character)
    .join("");
}

/**
 * RU/EN: Build the stable scanner result without changing the bridge JSON schema.
 * @param {string} text
 * @returns {ScanResult}
 */
function buildScanResult(text) {
  const normalizedText = normalizeForDetection(text);
  /** @type {Set<string>} */
  const riskTags = new Set();

  if (ZERO_WIDTH_OR_BIDI_RE.test(text)) {
    riskTags.add("OBFUSCATION");
  }

  for (const token of SUSPICIOUS_ASCII_FOLDS) {
    if (normalizedText.toLowerCase().includes(token)) {
      if (normalizedText !== text) {
        riskTags.add("OBFUSCATION");
      }
      break;
    }
  }

  for (const rule of RISK_RULES) {
    if (rule.patterns.some((pattern) => pattern.test(normalizedText))) {
      riskTags.add(rule.tag);
    }
  }

  if (riskTags.size === 0) {
    return {
      risk_level: "low",
      risk_tags: [],
      summary: "No high-risk patterns detected.",
    };
  }

  const orderedTags = Array.from(riskTags).sort();
  return {
    risk_level: "critical",
    risk_tags: orderedTags,
    summary: `Detected heuristic risk tags: ${orderedTags.join(", ")}`,
  };
}

async function main() {
  const payload = requireScannerInput(await readStdinJson());
  const { text } = payload;
  const result = buildScanResult(text);
  process.stdout.write(JSON.stringify(result));
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
