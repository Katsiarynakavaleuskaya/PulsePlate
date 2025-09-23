Fine-Tuning Options

This project uses provider-agnostic interfaces (see `llm.py`). Full fine-tuning
is not built into the service, but you can integrate tuned models via providers.

Recommended approaches:

- Local models (Ollama/transformers):
  - Train LoRA/QLoRA outside this repo (HF + PEFT), export weights, then serve
    via Ollama (custom Modelfile) or a local HTTP server compatible with the
    Ollama API. Point the app via `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=...`.

- Remote providers (x.ai Grok):
  - Full fine-tuning is not generally available. Prefer RAG and prompt control.

Validation & safety:
- Create a held-out eval set of prompts/answers.
- Measure exact-match and factuality, run safety filters.
- Version your model artifacts and roll out canary deployments.
