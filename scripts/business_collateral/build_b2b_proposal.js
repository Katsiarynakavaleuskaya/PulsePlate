#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { Document, HeadingLevel, Packer, Paragraph } = require("docx");
const { parseProposalSpec, resolveRepoPath } = require("./content_loader");

function resolveOutputPath() {
  const outputFlagIndex = process.argv.indexOf("--output");
  if (outputFlagIndex >= 0 && process.argv[outputFlagIndex + 1]) {
    return path.resolve(process.argv[outputFlagIndex + 1]);
  }

  return resolveRepoPath(
    "tmp",
    "business_collateral",
    "proposal",
    "PulsePlate_B2B_Partnership_Proposal.docx",
  );
}

function blockToParagraph(block) {
  if (block.type === "heading1") {
    return new Paragraph({
      heading: HeadingLevel.HEADING_1,
      text: block.text,
    });
  }

  if (block.type === "heading2") {
    return new Paragraph({
      heading: HeadingLevel.HEADING_2,
      text: block.text,
    });
  }

  if (block.type === "bullet") {
    return new Paragraph({
      bullet: { level: 0 },
      text: block.text,
    });
  }

  return new Paragraph({ text: block.text });
}

async function main() {
  const outputPath = resolveOutputPath();
  const outputDir = path.dirname(outputPath);
  const proposal = parseProposalSpec();

  // RU: Сохраняем генерацию производной и предсказуемой. EN: Keep generation derived and predictable.
  const children = [
    new Paragraph({
      heading: HeadingLevel.TITLE,
      text: proposal.title,
    }),
    ...proposal.blocks.map(blockToParagraph),
  ];

  const document = new Document({
    creator: "Codex",
    description: `Derived from ${proposal.sourcePath}`,
    title: proposal.title,
    sections: [{ children }],
  });

  fs.mkdirSync(outputDir, { recursive: true });
  const buffer = await Packer.toBuffer(document);
  fs.writeFileSync(outputPath, buffer);
  process.stdout.write(`${outputPath}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exit(1);
});
