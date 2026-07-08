# Log Convention

**Scope:** Normative
**Applies to:** `.aib_memory/log_<request_id>.md` and `.aib_memory/log_general.md`
**Enforced by:** `.aib_brain/tools/log-entry.py`

---

## 1. Purpose

Per-request append-only audit log for prompt execution events. Each active request has its
own log file at `.aib_memory/log_<request_id>.md` while the request is open. A general log
at `.aib_memory/log_general.md` is used for non-request-scoped events (e.g., during
`aib-refresh-context.md` execution).

---

## 2. File Naming

- Request log: `log_<request_id>.md` (using an underscore separator, not a hyphen) located at
  `.aib_memory/` root while the request is active.
- General log: `log_general.md` located at `.aib_memory/` root.
- The request log file is moved to the request subfolder on request close alongside other
  artifacts (handled by `move-request-artifacts.py`).

---

## 3. Entry Format

Each log entry MUST follow the format:

```
YYYYMMDD-HHmmss: <message>
```

- The timestamp MUST be UTC in 24-hour format.
- The timestamp format is `YYYYMMDD-HHmmss` (no separators within the date or time components).
- The message follows the timestamp separated by `: ` (colon and space).
- Each entry occupies exactly one line terminated by a newline character.

Example:
```
20260630-143022: S01 Preflight started
```

---

## 4. Append Semantics

- Each invocation of `log-entry.py` appends exactly one line to the target log file.
- Log files are never truncated, overwritten, or cleared by `log-entry.py` or any prompt.
- If the log file does not exist it is created on first invocation.

---

## 5. Invocation

Normal mode (requires an active request in `input.md`):
```
python .aib_brain/tools/log-entry.py --workspace . --message "<message>"
```

General mode (no active-request check; writes to `log_general.md`):
```
python .aib_brain/tools/log-entry.py --workspace . --message "<message>" --general
```

---

## 6. Error Behavior

- Normal mode exits with code 1 and prints an error to stderr when no active request is
  found in `input.md` (i.e., `state.status == "idle"`).
- Use `--general` flag in prompts that may run without an active request (e.g.,
  `aib-refresh-context.md`).
- `log-entry.py` exits with code 0 on successful entry write.
