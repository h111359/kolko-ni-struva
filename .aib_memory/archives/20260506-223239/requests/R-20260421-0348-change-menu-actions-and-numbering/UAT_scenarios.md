# UAT Scenarios — R-20260421-0348: Change menu actions and numbering

---

## UAT-01 — Visual menu rendering in terminal

**Description:** Launch the menu interactively and verify the rendered output matches the specified layout.

**Pre-conditions:** Python environment is active; `menu.py` is in the project root.

**Steps:**
1. Run `python menu.py` (or `./menu.sh` on Linux).
2. Observe the "Actions:" section printed to the terminal.

**Expected outcome:**
- Actions section shows exactly five lines in this order:
  - `1) Full refresh      (download + transform + update supabase)` (or close equivalent text)
  - `2) Download only     (python src/extract.py)`
  - `3) Transform only    (python src/transform.py)`
  - `4) Update Supabase DB  (python src/load_supabase.py)`
  - `0) Exit`
- Prompt reads `Enter choice [0-4]:`.
- No action numbered `5` is visible.

---

## UAT-02 — Exit on key `0`

**Description:** Verify that entering `0` at the prompt cleanly exits the menu without error.

**Pre-conditions:** Menu is running (UAT-01 step 1 completed).

**Steps:**
1. At the `Enter choice [0-4]:` prompt, type `0` and press Enter.

**Expected outcome:**
- Terminal prints "Exiting." (or equivalent message).
- Control returns to the shell prompt immediately; no traceback or error message.

---

## UAT-03 — Old key `4` no longer exits

**Description:** Verify that the old "Exit" key (`4`) now runs the Supabase sync instead.

**Pre-conditions:** Menu is running; Supabase `.env` may or may not be configured.

**Steps:**
1. At the `Enter choice [0-4]:` prompt, type `4` and press Enter.

**Expected outcome:**
- Terminal prints `Running: python src/load_supabase.py`.
- Menu does NOT exit; control returns to the action menu after the script completes (or reports an error if `.env` is not configured).
