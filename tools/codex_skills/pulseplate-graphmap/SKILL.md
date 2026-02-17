---
name: pulseplate-graphmap
description: Build and inspect PulsePlate GraphMap artifacts for deterministic project-map updates.
---

# PulsePlate GraphMap

## When to use

- Updating architecture/project graph artifacts.
- Verifying deterministic graph generation.
- Producing map snapshots for docs and onboarding.

## Inputs required

- Target output path (default `docs/graph/graph.json`).
- Branch/ref for review context.
- Whether determinism check is required.

## Procedure (commands)

1. Build graph artifact:

   ```bash
   python tools/graphmap/build_graph.py --out docs/graph/graph.json
   ```

2. Optional determinism verification:

   ```bash
   python tools/graphmap/build_graph.py --out /tmp/graph_tmp.json
   shasum -a 256 docs/graph/graph.json /tmp/graph_tmp.json
   ```

3. Optional local viewer:

   ```bash
   python -m http.server 8000
   ```

   Then open `http://localhost:8000/docs/graph/viewer/?repo=<repo>&ref=<ref>`.

## Output format

- `Build status`: command and output path.
- `Determinism status`: hash comparison result.
- `Changed nodes/edges`: concise summary.
- `Follow-up`: docs or architecture notes to update.

## Guardrails

- Do not hand-edit generated graph JSON when builder is available.
- Keep graph output free from secrets and absolute local paths.
- Treat graph as dev artifact, not runtime behavior.

## SoT links

- `tools/graphmap/README.md`
- `tools/graphmap/build_graph.py`
- `docs/graph/GRAPHMAP_SPEC.md`
