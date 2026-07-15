import unittest
from utils.classifier import (
    classify_command,
    split_compound_command,
    contains_modifying_operator,
    is_part_read_only
)


class TestClassifier(unittest.TestCase):

    def test_split_compound_command(self):
        # Basic split on semicolon
        self.assertEqual(split_compound_command("ls; pwd"), ["ls", "pwd"])
        # Split on pipeline
        self.assertEqual(split_compound_command("ls | grep foo"), ["ls", "grep foo"])
        # Split on logical operators
        self.assertEqual(split_compound_command("cd dir && ls"), ["cd dir", "ls"])
        self.assertEqual(split_compound_command("dir || echo error"), ["dir", "echo error"])
        # Split on background operator
        self.assertEqual(split_compound_command("ls & pwd"), ["ls", "pwd"])

        # Delimiters inside quotes should be ignored
        self.assertEqual(
            split_compound_command('echo "hello; world" && ls'),
            ['echo "hello; world"', 'ls']
        )
        self.assertEqual(
            split_compound_command("echo 'hello | world' && ls"),
            ["echo 'hello | world'", "ls"]
        )

    def test_contains_modifying_operator(self):
        # Redirection outside quotes
        self.assertTrue(contains_modifying_operator("echo hello > file.txt"))
        self.assertTrue(contains_modifying_operator("ls >> logs.txt"))
        # No redirection
        self.assertFalse(contains_modifying_operator("ls -la"))
        # Redirection inside quotes
        self.assertFalse(contains_modifying_operator('echo "hello > world"'))
        self.assertFalse(contains_modifying_operator("echo 'a > b'"))

    def test_is_part_read_only(self):
        # Read-only cases
        self.assertTrue(is_part_read_only("ls"))
        self.assertTrue(is_part_read_only("ls -la"))
        self.assertTrue(is_part_read_only("dir"))
        self.assertTrue(is_part_read_only("dir/w"))
        self.assertTrue(is_part_read_only("cd .."))
        self.assertTrue(is_part_read_only("cd.."))
        self.assertTrue(is_part_read_only("pwd"))
        self.assertTrue(is_part_read_only("git status"))
        self.assertTrue(is_part_read_only("Get-ChildItem -Path C:\\"))

        # Modifying cases (recognized commands with modifying keywords/args)
        self.assertFalse(is_part_read_only("ls rm"))
        self.assertFalse(is_part_read_only("cd mkdir"))
        self.assertFalse(is_part_read_only("git clone https://github.com"))

        # Unrecognized cases
        self.assertFalse(is_part_read_only("grep foo"))
        self.assertFalse(is_part_read_only("python app.py"))

    def test_classify_command(self):
        # Standard read-only
        self.assertEqual(classify_command("ls -la", "bash"), "READ-ONLY")
        self.assertEqual(classify_command("Get-ChildItem", "powershell"), "READ-ONLY")
        self.assertEqual(classify_command("git status", "bash"), "READ-ONLY")

        # Standard modifying
        self.assertEqual(classify_command("mkdir new_folder", "bash"), "MODIFYING")
        self.assertEqual(classify_command("rm -rf files", "zsh"), "MODIFYING")
        self.assertEqual(classify_command("echo hello > out.txt", "bash"), "MODIFYING")

        # Compound command (entirely read-only)
        self.assertEqual(classify_command("cd dir && ls", "bash"), "READ-ONLY")
        self.assertEqual(classify_command("pwd; dir/w", "cmd.exe"), "READ-ONLY")

        # Compound command (mixed)
        self.assertEqual(classify_command("cd dir && mkdir test", "bash"), "MODIFYING")
        self.assertEqual(classify_command("ls | rm -rf", "bash"), "MODIFYING")

        # Unrecognized or empty fallback
        self.assertEqual(classify_command("custom_command arg1", "bash"), "MODIFYING")
        self.assertEqual(classify_command("", "bash"), "MODIFYING")


if __name__ == "__main__":
    unittest.main()
