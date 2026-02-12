/* Review Constellation - algorithmic-art companion script.
 * Deterministic seeded particle field for review-quality visualization.
 */

/**
 * @typedef {Object} ReviewParams
 * @property {number} seed
 * @property {number} threadCount
 * @property {number} closureRatio
 * @property {number} confidence
 * @property {number} drift
 * @property {string[]} palette
 */

/**
 * @typedef {Object} ReviewCenter
 * @property {number} x
 * @property {number} y
 * @property {number} weight
 */

/**
 * @typedef {Object} ReviewNode
 * @property {number} x
 * @property {number} y
 * @property {number} vx
 * @property {number} vy
 * @property {number} mass
 * @property {number} hueIndex
 * @property {number} phase
 */

const reviewDefaults = {
  seed: 71942,
  threadCount: 220,
  closureRatio: 0.72,
  confidence: 0.64,
  drift: 0.38,
  palette: ["#d97757", "#6a9bcc", "#788c5d"],
};

/** @type {ReviewParams} */
let reviewParams = { ...reviewDefaults, palette: [...reviewDefaults.palette] };
/** @type {ReviewNode[]} */
let reviewNodes = [];
/** @type {ReviewCenter[]} */
let reviewCenters = [];
/** @type {number} */
let reviewTick = 0;

/**
 * Reset simulation with a new seed; rebuilds centers and nodes.
 * @param {number|string} seedValue - Seed for randomSeed/noiseSeed (positive integer).
 * @returns {void}
 */
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

/**
 * Build attraction centers used for particle dynamics (p5 width/height required).
 * @param {number} count - Number of centers to create.
 * @returns {ReviewCenter[]}
 */
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

/**
 * Create a single particle node around a center (uses reviewParams.closureRatio).
 * @param {number} index - Node index (used to pick anchor and hueIndex).
 * @returns {ReviewNode}
 */
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

/**
 * Advance simulation one tick: apply attraction, noise swirl, damping.
 * @returns {void}
 */
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

/**
 * Find the closest center to a node by squared distance.
 * @param {ReviewNode} node
 * @returns {ReviewCenter}
 */
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

/**
 * Draw one frame: trail background and colored circles for each node (p5 API).
 * @returns {void}
 */
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

/**
 * Update a numeric parameter; if name is "threadCount", rebuilds nodes via reviewReset.
 * @param {string} name - Parameter key (e.g. "threadCount", "closureRatio").
 * @param {number|string} value - New value.
 * @returns {void}
 */
function reviewUpdateParam(name, value) {
  if (name === "threadCount") {
    reviewParams.threadCount = Number(value);
    reviewReset(reviewParams.seed);
    return;
  }
  reviewParams[name] = Number(value);
}

/**
 * Set a palette color by index.
 * @param {number} index - Palette index (0..palette.length-1).
 * @param {string} value - Hex color (e.g. "#rrggbb").
 * @returns {void}
 */
function reviewUpdateColor(index, value) {
  reviewParams.palette[index] = value;
}

/**
 * Reset all parameters to defaults and re-run reviewReset with current seed.
 * @returns {void}
 */
function reviewResetParams() {
  reviewParams = { ...reviewDefaults, palette: [...reviewDefaults.palette] };
  reviewReset(reviewParams.seed);
}
