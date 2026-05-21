## UAT Scenarios

- UAT-01 — Interactive preview launch flow
  - Preconditions: Node dependencies installed for react-app; terminal session has project root as working directory.
  - Steps:
    1. Run menu launcher (python menu.py or menu.sh/menu.bat).
    2. Select the local preview action number.
    3. Observe terminal output until local server URL is displayed.
  - Expected result: preview server starts, URL is visible in terminal, and operator can proceed without errors.

- UAT-02 — Browser-open fallback behavior
  - Preconditions: Same as UAT-01, but run in an environment where browser auto-open is unavailable or blocked (for example, headless shell).
  - Steps:
    1. Trigger local preview action from the menu.
    2. Observe behavior when browser open attempt fails.
  - Expected result: workflow continues, URL is still printed, and menu/script does not crash because auto-open failed.
