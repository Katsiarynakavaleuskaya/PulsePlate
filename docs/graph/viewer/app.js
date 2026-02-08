function qs(name) {
  return new URLSearchParams(window.location.search).get(name);
}

const GITHUB_REPO = qs("repo") || "Katsiarynakavaleuskaya/PulsePlate";
const GITHUB_REF = qs("ref") || "main";
const GRAPH_URL = "../graph.json";

const LEVELS = ["theme", "project", "architecture", "module", "safety", "execution"];

function unique(arr) {
  return Array.from(new Set(arr)).sort();
}

function selectedValues(selectEl) {
  return Array.from(selectEl.selectedOptions).map((o) => o.value);
}

function buildGitHubUrlForNode(node, graph) {
  const path = node.data("path");
  if (!path) return null;

  // Spec: open anchored location if evidence contains path:line.
  let bestLine = null;
  for (const e of graph.edges) {
    if (e.source !== node.id() && e.target !== node.id()) continue;
    if (!Array.isArray(e.evidence)) continue;

    for (const ev of e.evidence) {
      const idx = ev.lastIndexOf(":");
      if (idx <= 0) continue;
      const evPath = ev.slice(0, idx);
      const evLine = Number(ev.slice(idx + 1));
      if (!Number.isInteger(evLine) || evLine <= 0) continue;
      if (evPath !== path) continue;

      if (bestLine === null || evLine < bestLine) {
        bestLine = evLine;
      }
    }
  }

  const base = `https://github.com/${GITHUB_REPO}/blob/${GITHUB_REF}/${path}`;
  return bestLine ? `${base}#L${bestLine}` : base;
}

function setDetails(node) {
  const payload = node ? node.data() : { hint: "(click a node)" };
  document.getElementById("details").textContent = JSON.stringify(payload, null, 2);
}

async function loadGraph() {
  const res = await fetch(GRAPH_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${GRAPH_URL}: ${res.status}`);
  return res.json();
}

function makeElements(graph) {
  const nodes = graph.nodes.map((n) => ({ data: n }));
  // Note: graph.json schema does not include edge IDs. Let Cytoscape generate unique IDs
  // so parallel edges (same source/target/type but different evidence) never collide.
  const edges = graph.edges.map((e) => ({ data: { ...e, evidence: e.evidence || null } }));
  return nodes.concat(edges);
}

function applyFilters(cy) {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const types = selectedValues(document.getElementById("typeFilter"));
  const levels = selectedValues(document.getElementById("levelFilter"));

  cy.nodes().forEach((n) => {
    const label = (n.data("label") || "").toLowerCase();
    const t = n.data("type");
    const tags = Array.isArray(n.data("tags")) ? n.data("tags") : [];

    const okSearch = q === "" || label.includes(q);
    const okType = types.length === 0 || types.includes(t);
    const okLevel = levels.length === 0 || levels.some((lvl) => tags.includes(lvl));

    n.style("display", okSearch && okType && okLevel ? "element" : "none");
  });

  // Hide edges if either endpoint is hidden
  cy.edges().forEach((e) => {
    const s = e.source();
    const t = e.target();
    const ok = s.style("display") !== "none" && t.style("display") !== "none";
    e.style("display", ok ? "element" : "none");
  });
}

function fillFilters(graph) {
  const typeFilter = document.getElementById("typeFilter");
  const levelFilter = document.getElementById("levelFilter");

  const types = unique(graph.nodes.map((n) => n.type));

  typeFilter.innerHTML = "";
  for (const t of types) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    typeFilter.appendChild(opt);
  }

  levelFilter.innerHTML = "";
  for (const l of LEVELS) {
    const opt = document.createElement("option");
    opt.value = l;
    opt.textContent = l;
    levelFilter.appendChild(opt);
  }
}

function wireUI(cy) {
  const search = document.getElementById("search");
  const typeFilter = document.getElementById("typeFilter");
  const levelFilter = document.getElementById("levelFilter");
  const reset = document.getElementById("reset");

  const onChange = () => applyFilters(cy);

  search.addEventListener("input", onChange);
  typeFilter.addEventListener("change", onChange);
  levelFilter.addEventListener("change", onChange);

  reset.addEventListener("click", () => {
    search.value = "";
    typeFilter.selectedIndex = -1;
    levelFilter.selectedIndex = -1;
    applyFilters(cy);
    cy.fit();
    setDetails(null);
  });
}

function initCy(elements) {
  const cy = cytoscape({
    container: document.getElementById("cy"),
    elements,
    layout: { name: "cose", animate: false },
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "font-size": 10,
          "text-wrap": "wrap",
          "text-max-width": 160,
          "background-color": "#2d6cdf",
          color: "#e6edf3",
          "border-width": 1,
          "border-color": "#243244",
        },
      },
      { selector: 'node[type = "module"]', style: { "background-color": "#6c2ddf" } },
      { selector: 'node[type = "agent"]', style: { "background-color": "#df9a2d" } },
      { selector: 'node[type = "test"]', style: { "background-color": "#df2d6c" } },
      {
        selector: "edge",
        style: {
          width: 1,
          "line-color": "#243244",
          "target-arrow-color": "#243244",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(type)",
          "font-size": 8,
          color: "#9aa4b2",
        },
      },
    ],
  });

  return cy;
}

(async function main() {
  try {
    const graph = await loadGraph();
    fillFilters(graph);

    const cy = initCy(makeElements(graph));
    wireUI(cy);
    applyFilters(cy);
    cy.fit();

    cy.on("tap", "node", (evt) => {
      const n = evt.target;
      setDetails(n);
      const url = buildGitHubUrlForNode(n, graph);
      if (!url) return;
      window.open(url, "_blank", "noopener,noreferrer");
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) setDetails(null);
    });
  } catch (e) {
    document.getElementById("details").textContent = String(e);
  }
})();
