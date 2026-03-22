const fs = require("fs");
const path = require("path");

function readUtf8(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

function resolveRepoPath(...segments) {
  return path.resolve(__dirname, "..", "..", ...segments);
}

function flushParagraph(paragraphBuffer, blocks) {
  if (!paragraphBuffer.length) {
    return;
  }

  blocks.push({
    type: "paragraph",
    text: paragraphBuffer.join(" ").trim(),
  });
  paragraphBuffer.length = 0;
}

function parseMarkdownBlocks(markdown) {
  const lines = markdown.split(/\r?\n/);
  const blocks = [];
  const paragraphBuffer = [];
  let title = "Untitled";
  let inHtmlComment = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (inHtmlComment) {
      if (line.includes("-->")) {
        inHtmlComment = false;
      }
      continue;
    }

    if (!line) {
      flushParagraph(paragraphBuffer, blocks);
      continue;
    }

    if (line.startsWith("<!--")) {
      flushParagraph(paragraphBuffer, blocks);
      if (!line.includes("-->")) {
        inHtmlComment = true;
      }
      continue;
    }

    if (line.startsWith("# ")) {
      flushParagraph(paragraphBuffer, blocks);
      title = line.replace(/^#\s+/, "").trim();
      continue;
    }

    if (line.startsWith("## ")) {
      flushParagraph(paragraphBuffer, blocks);
      blocks.push({
        type: "heading1",
        text: line.replace(/^##\s+/, "").trim(),
      });
      continue;
    }

    if (line.startsWith("### ")) {
      flushParagraph(paragraphBuffer, blocks);
      blocks.push({
        type: "heading2",
        text: line.replace(/^###\s+/, "").trim(),
      });
      continue;
    }

    if (line.startsWith("- ")) {
      flushParagraph(paragraphBuffer, blocks);
      blocks.push({
        type: "bullet",
        text: line.replace(/^-\s+/, "").trim(),
      });
      continue;
    }

    paragraphBuffer.push(line);
  }

  flushParagraph(paragraphBuffer, blocks);
  return { title, blocks };
}

function parseProposalSpec() {
  const sourcePath = resolveRepoPath(
    "docs",
    "audience_pack",
    "B2B_PARTNERSHIP_PROPOSAL_SPEC.md",
  );
  const { title: fallbackTitle, blocks } = parseMarkdownBlocks(readUtf8(sourcePath));
  const proposalTitleIndex = blocks.findIndex(
    (block) => block.type === "heading1" && /^Proposal Title$/i.test(block.text),
  );
  const proposalTitleBlock = blocks[proposalTitleIndex + 1];
  const hasProposalTitle =
    proposalTitleIndex >= 0 &&
    proposalTitleBlock &&
    proposalTitleBlock.type === "paragraph" &&
    proposalTitleBlock.text;

  return {
    sourcePath,
    title: hasProposalTitle ? proposalTitleBlock.text : fallbackTitle,
    blocks: hasProposalTitle
      ? blocks.filter((_, index) => index !== proposalTitleIndex && index !== proposalTitleIndex + 1)
      : blocks,
  };
}

function parseDeckSpec() {
  const sourcePath = resolveRepoPath(
    "docs",
    "audience_pack",
    "B2B_PITCH_DECK_SPEC.md",
  );
  const { title, blocks } = parseMarkdownBlocks(readUtf8(sourcePath));
  const slides = [];
  let currentSlide = null;

  for (const block of blocks) {
    if (block.type === "heading1" && /^Slide\s+\d+/i.test(block.text)) {
      if (currentSlide) {
        slides.push(currentSlide);
      }

      currentSlide = {
        title: block.text.replace(/^Slide\s+\d+\s*-\s*/i, "").trim(),
        paragraphs: [],
        bullets: [],
      };
      continue;
    }

    if (!currentSlide) {
      continue;
    }

    if (block.type === "bullet") {
      currentSlide.bullets.push(block.text);
      continue;
    }

    if (block.type === "paragraph" || block.type === "heading2") {
      currentSlide.paragraphs.push(block.text);
    }
  }

  if (currentSlide) {
    slides.push(currentSlide);
  }

  return { sourcePath, title, slides };
}

module.exports = {
  parseDeckSpec,
  parseMarkdownBlocks,
  parseProposalSpec,
  resolveRepoPath,
};
