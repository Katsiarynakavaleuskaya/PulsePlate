#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");
const { parseDeckSpec, resolveRepoPath } = require("./content_loader");

function resolveOutputPath() {
  const outputFlagIndex = process.argv.indexOf("--output");
  if (outputFlagIndex >= 0 && process.argv[outputFlagIndex + 1]) {
    return path.resolve(process.argv[outputFlagIndex + 1]);
  }

  return resolveRepoPath(
    "tmp",
    "business_collateral",
    "deck",
    "PulsePlate_B2B_Pitch_Deck.pptx",
  );
}

async function main() {
  const outputPath = resolveOutputPath();
  const outputDir = path.dirname(outputPath);
  const deck = parseDeckSpec();
  const presentation = new PptxGenJS();

  presentation.layout = "LAYOUT_WIDE";
  presentation.author = "Codex";
  presentation.company = "PulsePlate";
  presentation.subject = deck.title;
  presentation.title = deck.title;
  presentation.lang = "en-US";

  for (const [index, slideSpec] of deck.slides.entries()) {
    const slide = presentation.addSlide();
    slide.background = { color: "F6F3EC" };
    slide.addShape(presentation.ShapeType.rect, {
      x: 0,
      y: 0,
      w: 13.333,
      h: 0.35,
      fill: { color: "2E5E4E" },
      line: { color: "2E5E4E" },
    });

    slide.addText(slideSpec.title, {
      x: 0.7,
      y: 0.6,
      w: 11.5,
      h: 0.6,
      fontFace: "Aptos Display",
      fontSize: 24,
      bold: true,
      color: "21332B",
    });

    if (slideSpec.paragraphs.length) {
      slide.addText(slideSpec.paragraphs[0], {
        x: 0.7,
        y: 1.35,
        w: 11.3,
        h: 0.7,
        fontFace: "Aptos",
        fontSize: 14,
        color: "42574E",
      });
    }

    let bulletY = slideSpec.paragraphs.length ? 2.2 : 1.6;
    for (const bullet of slideSpec.bullets) {
      slide.addText(`• ${bullet}`, {
        x: 0.95,
        y: bulletY,
        w: 11.0,
        h: 0.42,
        fontFace: "Aptos",
        fontSize: 18,
        color: "21332B",
      });
      bulletY += 0.5;
    }

    slide.addText(`PulsePlate B2B Deck | ${String(index + 1).padStart(2, "0")}`, {
      x: 9.9,
      y: 7.05,
      w: 2.3,
      h: 0.2,
      fontFace: "Aptos",
      fontSize: 9,
      color: "6D7C75",
      align: "right",
    });
  }

  fs.mkdirSync(outputDir, { recursive: true });
  await presentation.writeFile({ fileName: outputPath });
  process.stdout.write(`${outputPath}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exit(1);
});
