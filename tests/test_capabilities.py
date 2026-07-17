import unittest
from unittest.mock import patch

from utils.capabilities import detect_installed_tools, format_tool_context


class TestCapabilities(unittest.TestCase):

    @patch("utils.capabilities.shutil.which")
    def test_detect_installed_tools_groups_found_tools(self, mock_which):
        mock_which.side_effect = lambda tool_name: (
            f"/usr/bin/{tool_name}" if tool_name in {"python3", "npm", "git"} else None
        )

        installed = detect_installed_tools()

        self.assertIn("python3", installed["Languages/Runtimes"])
        self.assertIn("npm", installed["Package Managers"])
        self.assertIn("git", installed["Developer CLIs"])
        self.assertNotIn("node", installed["Languages/Runtimes"])

    def test_format_tool_context_lists_detected_and_missing_categories(self):
        context = format_tool_context({
            "Languages/Runtimes": ["python3", "node"],
            "Package Managers": [],
        })

        self.assertIn("- Languages/Runtimes: python3, node", context)
        self.assertIn("- Package Managers: none detected", context)


if __name__ == "__main__":
    unittest.main()
