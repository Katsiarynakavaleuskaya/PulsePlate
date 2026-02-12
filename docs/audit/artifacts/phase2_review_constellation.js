/* Review Constellation - algorithmic-art companion script.
 * Deterministic seeded particle field for review-quality visualization.
 */

const reviewDefaults = {
  seed: 71942,
  threadCount: 220,
  closureRatio: 0.72,
  confidence: 0.64,
  drift: 0.38,
  palette: ["#d97757", "#6a9bcc", "#788c5d"],
};

let reviewParams = { ...reviewDefaults };
let reviewNodes = [];
let reviewCenters = [];
let reviewTick = 0;

function reviewReset(seedValue) {
  const parsed = Number(seedValue);
  reviewParams.seed = Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : reviewParams.seed;
  randomSeed(reviewParams.seed);
  noiseSeed(reviewParams.seed);
  reviewNodes = [];
  reviewCenters = buildCenters(6);
  reviewTick = 0;
  for (let i = 0; i < reviewParams.threadCount; i += 1) {
    reviewNodes.push(buildNode(i));
  }
}

function buildCenters(count) {
  const centers = [];
  for (let i = 0; i < count; i += 1) {
    centers.push({
      x: width * random(0.16, 0.84),
      y: height * random(0.16, 0.84),
      weight: random(0.6, 1.4),
    });
  }
  return centers;
}

function buildNode(index) {
  const anchor = reviewCenters[index % reviewCenters.length];
  const angle = random(TWO_PI);
  const radius = random(10, 220) * (1.0 + (1.0 - reviewParams.closureRatio));
  return {
    x: anchor.x + cos(angle) * radius,
    y: anchor.y + sin(angle) * radius,
    vx: random(-0.4, 0.4),
    vy: random(-0.4, 0.4),
    mass: random(0.6, 1.3),
    hueIndex: index % reviewParams.palette.length,
    phase: random(TWO_PI),
  };
}

function reviewStep() {
  reviewTick += 1;
  const closurePull = map(reviewParams.closureRatio, 0, 1, 0.0009, 0.0034);
  const driftFactor = map(reviewParams.drift, 0, 1, 0.15, 0.95);
  const damping = map(reviewParams.confidence, 0, 1, 0.962, 0.992);

  for (const node of reviewNodes) {
    const nearest = nearestCenter(node);
    const dx = nearest.x - node.x;
    const dy = nearest.y - node.y;
    const distanceSq = max(25, dx * dx + dy * dy);
    const g = (closurePull * nearest.weight * node.mass) / distanceSq;

    node.vx += dx * g;
    node.vy += dy * g;

    const n = noise(node.x * 0.0021, node.y * 0.0021, reviewTick * 0.002);
    const swirl = (n - 0.5) * driftFactor * 0.38;
    node.vx += cos(node.phase) * swirl;
    node.vy += sin(node.phase) * swirl;

    node.vx *= damping;
    node.vy *= damping;
    node.x += node.vx;
    node.y += node.vy;

    node.phase += 0.004 + 0.005 * n;
  }
}

function nearestCenter(node) {
  let best = reviewCenters[0];
  let bestDist = Number.POSITIVE_INFINITY;
  for (const center of reviewCenters) {
    const dx = center.x - node.x;
    const dy = center.y - node.y;
    const d = dx * dx + dy * dy;
    if (d < bestDist) {
      bestDist = d;
      best = center;
    }
  }
  return best;
}

function reviewRender() {
  const trailAlpha = map(reviewParams.confidence, 0, 1, 12, 34);
  background(250, 249, 245, trailAlpha);

  noStroke();
  for (const node of reviewNodes) {
    const paletteHex = reviewParams.palette[node.hueIndex];
    const base = color(paletteHex);
    const speed = min(1.0, mag(node.vx, node.vy) * 8.5);
    const shade = lerpColor(base, color("#141413"), speed * 0.24);
    fill(red(shade), green(shade), blue(shade), 118);
    circle(node.x, node.y, 1.8 + node.mass * 1.7);
  }
}

function reviewUpdateParam(name, value) {
  if (name === "threadCount") {
    reviewParams.threadCount = Number(value);
    reviewReset(reviewParams.seed);
    return;
  }
  reviewParams[name] = Number(value);
}

function reviewUpdateColor(index, value) {
  reviewParams.palette[index] = value;
}

function reviewResetParams() {
  reviewParams = { ...reviewDefaults };
  reviewReset(reviewParams.seed);
}
