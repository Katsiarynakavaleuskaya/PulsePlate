# GraphMap (dev-only tooling)

Deterministic builder + static viewer per `docs/graph/GRAPHMAP_SPEC.md`.

## Build

```bash
python tools/graphmap/build_graph.py --out docs/graph/graph.json
```

## Determinism check

```bash
python tools/graphmap/build_graph.py --out docs/graph/graph.json
python tools/graphmap/build_graph.py --out /tmp/graph.json
python - << 'PY'
import hashlib
import pathlib

a = pathlib.Path("docs/graph/graph.json").read_bytes()
b = pathlib.Path("/tmp/graph.json").read_bytes()
print("same:", hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest())
PY
```

## View locally

```bash
python -m http.server 8000
# open:
# http://localhost:8000/docs/graph/viewer/?repo=Katsiarynakavaleuskaya/PulsePlate&ref=main
```
