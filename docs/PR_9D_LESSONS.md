# PR-9d Lessons: AST-based Policy Guards & Route Patching

## Critical Lessons from PR-9d Implementation

### 1. AST-based static analysis vs regex (CRITICAL)

**Problem:**
- Regex-based detection (`r"\bdel\s+sys\.modules\s*\["`) triggers false positives on:
  - Comments: `# del sys.modules['x']`
  - String literals: `s = "sys.modules.pop('x')"`
  - Documentation strings

**Solution:**
- Use `ast.parse()` + `ast.NodeVisitor` for semantic analysis
- Only flags actual runtime mutations, not text mentions
- More accurate and maintainable

**Implementation pattern:**
```python
def _find_violations(text: str) -> list[tuple[int, str]]:
    tree = ast.parse(text)
    class Visitor(ast.NodeVisitor):
        def visit_Delete(self, node: ast.Delete) -> None:
            # Check actual AST nodes, not text
    Visitor().visit(tree)
```

**Lesson:** For policy guards that need semantic understanding, AST is mandatory. Regex is too brittle.

---

### 2. Import aliases must be tracked in AST visitors

**Problem:**
- Simple AST check for `sys.modules` misses:
  - `import sys as s; s.modules['x'] = ...`
  - `from sys import modules as m; m['x'] = ...`

**Solution:**
- Track import aliases in Visitor state:
  - `self.sys_module_names: set[str] = {"sys"}` (tracks `sys`, `s`, etc.)
  - `self.modules_names: set[str] = set()` (tracks `modules`, `m`, etc.)
- Override `visit_Import` and `visit_ImportFrom` to build alias maps
- Use alias-aware checks: `node.value.id in self.sys_module_names`

**Implementation pattern:**
```python
class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.sys_module_names: set[str] = {"sys"}
        self.modules_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "sys":
                self.sys_module_names.add(alias.asname or alias.name)
```

**Lesson:** AST visitors for policy guards must track import aliases, not just literal names.

---

### 3. Comprehensive mutation method detection

**Problem:**
- Only checking `sys.modules.pop()` misses other mutation methods:
  - `sys.modules.update(...)`
  - `sys.modules.clear()`
  - `sys.modules.setdefault(...)`
  - `sys.modules.popitem()`
  - `sys.modules.__setitem__(...)`
  - `sys.modules.__delitem__(...)`

**Solution:**
- Use dictionary mapping of method names to error messages
- Check `node.func.attr` against known mutation methods
- Extensible pattern for adding new methods

**Implementation pattern:**
```python
messages_by_method = {
    "pop": "Forbidden: `sys.modules.pop(...)` in tests.",
    "update": "Forbidden: `sys.modules.update(...)` in tests.",
    "clear": "Forbidden: `sys.modules.clear()` in tests.",
    # ... etc
}
msg = messages_by_method.get(node.func.attr)
if msg is not None:
    violations.append((node.lineno, msg))
```

**Lesson:** Policy guards must cover all mutation methods, not just the most common ones.

---

### 4. Gradual policy enforcement (scope limitation)

**Problem:**
- Enforcing policy on all `tests/**` immediately breaks legacy tests
- Creates massive technical debt and blocks PR merge

**Solution:**
- Start with limited scope: `ENFORCED_GLOBS = ("vip/**/*.py",)`
- Add explicit comment explaining rationale
- Document expansion path: "Expand scope only as legacy tests are cleaned up"

**Implementation pattern:**
```python
ENFORCED_GLOBS: tuple[str, ...] = (
    # VIP tests were explicitly stabilized for import hygiene in PR-8c/8b.
    # Keep these files free of sys.modules mutation to avoid regressions.
    # NOTE: Scope is intentionally limited to `tests/vip/**` to avoid breaking legacy tests.
    # Expand scope only as legacy tests are cleaned up.
    "vip/**/*.py",
)
```

**Lesson:** Policy guards should be introduced gradually with explicit scope limitations. Document the expansion path.

---

### 5. Test helper functions must be module-level for `__globals__` patching

**Problem:**
- `patch_endpoint_global(..., name="dep")` fails if `dep()` is defined inside test function
- `endpoint.__globals__` only contains module-level symbols

**Solution:**
- Define helper functions at module level (not inside test)
- Test can reference module-level function in route handler
- `patch_endpoint_global` can find symbol in `endpoint.__globals__`

**Implementation pattern:**
```python
# Module level (correct)
def dep() -> str:
    return "ok"

def test_route(monkeypatch: pytest.MonkeyPatch) -> None:
    @app.get("/x")
    def handler():
        return {"v": dep()}  # References module-level dep()

    endpoint = find_route_endpoint(...)
    patch_endpoint_global(..., name="dep", ...)  # Finds dep in __globals__
```

**Lesson:** For `patch_endpoint_global` to work, patched symbols must be module-level, not function-local.

---

### 6. Test policy behavior explicitly (not just implementation)

**Problem:**
- Policy behavior (e.g., "doesn't flag comments") was implicit
- No way to verify behavior doesn't regress

**Solution:**
- Add explicit tests for policy behavior:
  - `test_policy_does_not_flag_comments_or_strings()`
  - `test_policy_flags_runtime_mutations()`
  - `test_policy_flags_sys_import_aliases()`
  - `test_policy_flags_from_sys_import_modules_alias()`

**Implementation pattern:**
```python
def test_policy_does_not_flag_comments_or_strings() -> None:
    content = "# del sys.modules['x']\n" "s = \"sys.modules.pop('x')\"\n"
    assert _find_violations(content) == []  # Explicit contract
```

**Lesson:** Policy guards need explicit behavior tests, not just implementation tests. Lock the contract.

---

### 7. SyntaxError handling in AST parsing

**Problem:**
- `ast.parse()` raises `SyntaxError` on invalid Python
- Policy guard should not break CI on temporarily invalid files

**Solution:**
- Wrap `ast.parse()` in try/except
- Return empty violations list on SyntaxError
- Add comment explaining rationale

**Implementation pattern:**
```python
try:
    tree = ast.parse(text)
except SyntaxError:
    # Ignore syntactically invalid files (shouldn't happen for committed tests).
    # Policy checks should stay non-blocking even if a file is temporarily invalid.
    return []
```

**Lesson:** AST-based policy guards must gracefully handle SyntaxError to avoid blocking CI.

---

## Summary: Key Takeaways

1. **AST > regex** for semantic policy guards
2. **Track import aliases** in AST visitors
3. **Cover all mutation methods**, not just common ones
4. **Gradual enforcement** with explicit scope and expansion path
5. **Module-level helpers** for `__globals__` patching
6. **Explicit behavior tests** lock policy contract
7. **Graceful SyntaxError handling** keeps CI non-blocking

---

## Related Files

- `tests/test_repo_policy_sys_modules.py` - Implementation
- `tests/_route_patch.py` - Route patching helper
- `tests/test_route_patch_helper.py` - Helper tests
- `docs/ENGINEERING_LESSONS.md` - General PR-8b lessons
