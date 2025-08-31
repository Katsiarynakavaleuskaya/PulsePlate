import pathlib
import sys

# Корень репозитория = родитель папки tests
ROOT = pathlib.Path(__file__).resolve().parent.parent
p = str(ROOT)
if p not in sys.path:
    sys.path.insert(0, p)


import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _neutral_llm_env():
    for k in ("LLM_PROVIDER","GROK_ENDPOINT","GROK_MODEL","OPENAI_API_KEY","XAI_API_KEY"):
        os.environ.pop(k, None)
