"""
test_deploy_netlify.py: Unit tests for src/deploy_netlify.py and the
  menu.py option-5 integration.
Part of request R-20260421-0505 — Add Netlify deploy option to menu.
  Extended by request R-20260425-1304 — Secure Netlify deploy configuration.
Responsibilities: verify CLI-unavailability fallback, credential loading
  (env var, .env file, interactive prompt), auto-save behaviour,
  menu option presence, and invalid-choice error message.
"""
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path so both src and root modules can be
# imported without a package install step.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import src.deploy_netlify as deploy_netlify
import menu


class TestFindNetlifyCmd(unittest.TestCase):
    """Tests for the Netlify CLI detection helper."""

    def test_returns_netlify_list_when_found_on_path(self) -> None:
        """Returns ['netlify'] when the binary exists on PATH."""
        with patch("shutil.which", return_value="/usr/bin/netlify"):
            result = deploy_netlify.find_netlify_cmd()
        self.assertEqual(result, ["netlify"])

    def test_returns_none_when_not_on_path(self) -> None:
        """Returns None when the netlify binary is absent from PATH."""
        with patch("shutil.which", return_value=None):
            result = deploy_netlify.find_netlify_cmd()
        self.assertIsNone(result)


class TestPrintManualInstructions(unittest.TestCase):
    """Tests for the manual deploy instructions fallback output."""

    def test_output_contains_expected_heading(self) -> None:
        """Manual instructions output must contain the heading text."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            deploy_netlify.print_manual_instructions()
        output = captured.getvalue()
        self.assertIn("Manual Deploy Instructions", output)

    def test_output_contains_netlify_url(self) -> None:
        """Manual instructions must mention the Netlify dashboard URL."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            deploy_netlify.print_manual_instructions()
        output = captured.getvalue()
        self.assertIn("app.netlify.com", output)


class TestGetCredential(unittest.TestCase):
    """Tests for the interactive credential collection helper."""

    def test_returns_env_value_when_set(self) -> None:
        """Returns the env var value without prompting when it is set."""
        with patch.dict("os.environ", {"NETLIFY_AUTH_TOKEN": "tok123"}):
            with patch("builtins.input") as mock_input:
                result = deploy_netlify.get_credential(
                    "NETLIFY_AUTH_TOKEN", "Auth token", "instructions"
                )
        mock_input.assert_not_called()
        self.assertEqual(result, "tok123")

    def test_prompts_user_when_env_not_set(self) -> None:
        """Prompts the user and returns the entered value when env var absent."""
        with patch("os.environ.get", return_value=""):
            with patch("builtins.input", return_value="user-entered-token"):
                result = deploy_netlify.get_credential(
                    "NETLIFY_AUTH_TOKEN", "Auth token", "instructions"
                )
        self.assertEqual(result, "user-entered-token")

    def test_exits_when_user_enters_empty_value(self) -> None:
        """sys.exit(1) is raised when the user provides an empty credential."""
        with patch("os.environ.get", return_value=""):
            with patch("builtins.input", return_value=""):
                with self.assertRaises(SystemExit) as ctx:
                    deploy_netlify.get_credential(
                        "NETLIFY_AUTH_TOKEN", "Auth token", "instructions"
                    )
        self.assertEqual(ctx.exception.code, 1)

    def test_prompts_for_site_id_when_env_not_set(self) -> None:
        """Prompts the user and returns the entered value for NETLIFY_SITE_ID."""
        with patch("os.environ.get", return_value=""):
            with patch("builtins.input", return_value="site-uuid-example"):
                result = deploy_netlify.get_credential(
                    "NETLIFY_SITE_ID", "Site ID", "instructions"
                )
        self.assertEqual(result, "site-uuid-example")


class TestMainNoCliAvailable(unittest.TestCase):
    """Tests for the main() fallback path when CLI is not found."""

    def test_main_prints_manual_instructions_and_exits_0_when_no_cli(self) -> None:
        """main() prints manual instructions and exits 0 when CLI unavailable."""
        with patch.object(deploy_netlify, "find_netlify_cmd", return_value=None):
            with patch.object(
                deploy_netlify, "print_manual_instructions"
            ) as mock_instructions:
                with self.assertRaises(SystemExit) as ctx:
                    deploy_netlify.main()
        mock_instructions.assert_called_once()
        self.assertEqual(ctx.exception.code, 0)


class TestMenuOption5(unittest.TestCase):
    """Tests for the menu.py option-5 integration."""

    def test_print_menu_contains_option_5(self) -> None:
        """print_menu() output includes the '5)' option entry."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            menu.print_menu()
        output = captured.getvalue()
        self.assertIn("5)", output)

    def test_print_menu_contains_netlify_label(self) -> None:
        """print_menu() output mentions Netlify in option 5."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            menu.print_menu()
        output = captured.getvalue()
        self.assertIn("Netlify", output)

    def test_invalid_choice_message_includes_6(self) -> None:
        """The invalid-choice error message references the range up to 6."""
        # Drive the main loop with invalid input then '0' to exit.
        inputs = iter(["9", "0"])
        captured = io.StringIO()
        with patch("builtins.input", side_effect=inputs):
            with patch("sys.stdout", captured):
                # Patch stats/menu helpers so they do not hit the filesystem.
                with patch.object(menu, "print_stats"):
                    with patch.object(menu, "print_menu"):
                        menu.main()
        output = captured.getvalue()
        self.assertIn("6", output)

    def test_choice_5_dispatches_to_action_deploy_netlify(self) -> None:
        """Entering '5' at the main loop calls action_deploy_netlify()."""
        inputs = iter(["5", "0"])
        with patch("builtins.input", side_effect=inputs):
            with patch("sys.stdout", io.StringIO()):
                with patch.object(menu, "print_stats"):
                    with patch.object(menu, "print_menu"):
                        with patch.object(
                            menu, "action_deploy_netlify"
                        ) as mock_deploy:
                            menu.main()
        mock_deploy.assert_called_once()


class TestMenuOption6(unittest.TestCase):
    """Tests for the menu.py option-6 local preview integration (R-20260425-2155)."""

    def test_print_menu_contains_option_6(self) -> None:
        """print_menu() output includes the '6)' option entry."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            menu.print_menu()
        output = captured.getvalue()
        self.assertIn("6)", output)

    def test_print_menu_contains_preview_label(self) -> None:
        """print_menu() output mentions 'Preview' in option 6."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            menu.print_menu()
        output = captured.getvalue()
        self.assertIn("Preview", output)

    def test_choice_6_dispatches_to_action_local_preview(self) -> None:
        """Entering '6' at the main loop calls action_local_preview()."""
        inputs = iter(["6", "0"])
        with patch("builtins.input", side_effect=inputs):
            with patch("sys.stdout", io.StringIO()):
                with patch.object(menu, "print_stats"):
                    with patch.object(menu, "print_menu"):
                        with patch.object(
                            menu, "action_local_preview"
                        ) as mock_preview:
                            menu.main()
        mock_preview.assert_called_once()


class TestEnvFileCredentialLoading(unittest.TestCase):
    """Tests for .env-file-based credential loading (R-20260425-1304)."""

    def test_credential_from_env_file_returned_without_prompt(self) -> None:
        """Credential present via patch.dict (simulating .env load) is returned without prompting."""
        with patch.dict("os.environ", {deploy_netlify.ENV_AUTH_TOKEN: "dotenv-token"}):
            with patch("builtins.input") as mock_input:
                result = deploy_netlify.get_credential(
                    deploy_netlify.ENV_AUTH_TOKEN, "Auth token", "instructions"
                )
        mock_input.assert_not_called()
        self.assertEqual(result, "dotenv-token")

    def test_site_id_from_env_file_returned_without_prompt(self) -> None:
        """Site ID present via patch.dict (simulating .env load) is returned without prompting."""
        with patch.dict("os.environ", {deploy_netlify.ENV_SITE_ID: "site-uuid-dotenv"}):
            with patch("builtins.input") as mock_input:
                result = deploy_netlify.get_credential(
                    deploy_netlify.ENV_SITE_ID, "Site ID", "instructions"
                )
        mock_input.assert_not_called()
        self.assertEqual(result, "site-uuid-dotenv")

    def test_env_file_path_is_project_root_dot_env(self) -> None:
        """_ENV_FILE_PATH resolves to the project-root .env file."""
        self.assertEqual(deploy_netlify._ENV_FILE_PATH.name, ".env")
        # Parent of _ENV_FILE_PATH should be the same as BASE_DIR.
        self.assertEqual(deploy_netlify._ENV_FILE_PATH.parent, deploy_netlify.BASE_DIR)


class TestSaveCredentialToEnv(unittest.TestCase):
    """Tests for the _save_credential_to_env helper (R-20260425-1304)."""

    def test_calls_set_key_with_correct_arguments(self) -> None:
        """set_key is invoked with the env file path, variable name, and value."""
        with patch("src.deploy_netlify.set_key") as mock_set_key:
            deploy_netlify._save_credential_to_env(
                deploy_netlify.ENV_AUTH_TOKEN, "test-token"
            )
        mock_set_key.assert_called_once_with(
            str(deploy_netlify._ENV_FILE_PATH),
            deploy_netlify.ENV_AUTH_TOKEN,
            "test-token",
        )

    def test_save_failure_is_non_fatal(self) -> None:
        """An OSError from set_key is caught; a warning is printed instead of raising."""
        with patch("src.deploy_netlify.set_key", side_effect=OSError("disk full")):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                # Must NOT raise.
                deploy_netlify._save_credential_to_env(deploy_netlify.ENV_AUTH_TOKEN, "x")
        self.assertIn("Warning", captured.getvalue())

    def test_confirmation_message_printed_on_success(self) -> None:
        """A confirmation message is printed when the credential is saved successfully."""
        with patch("src.deploy_netlify.set_key"):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                deploy_netlify._save_credential_to_env(deploy_netlify.ENV_AUTH_TOKEN, "x")
        self.assertIn(deploy_netlify.ENV_AUTH_TOKEN, captured.getvalue())


class TestAutoSaveOnInteractiveEntry(unittest.TestCase):
    """Tests for the auto-save-to-.env behaviour when credentials are entered interactively."""

    def test_credential_saved_to_env_when_not_preloaded(self) -> None:
        """_save_credential_to_env is called for a credential absent from env before prompting."""
        # Simulate both credentials absent so auto-save triggers.
        clean_env = {
            k: v for k, v in os.environ.items()
            if k not in (deploy_netlify.ENV_AUTH_TOKEN, deploy_netlify.ENV_SITE_ID)
        }
        with patch.dict("os.environ", clean_env, clear=True):
            with patch.object(deploy_netlify, "find_netlify_cmd", return_value=["netlify"]):
                with patch.object(deploy_netlify, "get_credential", side_effect=["tok", "sid"]):
                    with patch.object(deploy_netlify, "_save_credential_to_env") as mock_save:
                        with patch.object(deploy_netlify, "build_react_app", return_value=True):
                            with patch.object(
                                deploy_netlify, "deploy_to_netlify", return_value=True
                            ):
                                with patch("sys.stdout", io.StringIO()):
                                    deploy_netlify.main()
        # Both credentials absent → save called twice.
        self.assertEqual(mock_save.call_count, 2)

    def test_credential_not_saved_when_already_in_env(self) -> None:
        """_save_credential_to_env is not called when credentials are already in os.environ."""
        present_env = {
            deploy_netlify.ENV_AUTH_TOKEN: "preloaded-tok",
            deploy_netlify.ENV_SITE_ID: "preloaded-sid",
        }
        with patch.dict("os.environ", present_env):
            with patch.object(deploy_netlify, "find_netlify_cmd", return_value=["netlify"]):
                with patch.object(
                    deploy_netlify, "get_credential", side_effect=["preloaded-tok", "preloaded-sid"]
                ):
                    with patch.object(deploy_netlify, "_save_credential_to_env") as mock_save:
                        with patch.object(deploy_netlify, "build_react_app", return_value=True):
                            with patch.object(
                                deploy_netlify, "deploy_to_netlify", return_value=True
                            ):
                                with patch("sys.stdout", io.StringIO()):
                                    deploy_netlify.main()
        mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
