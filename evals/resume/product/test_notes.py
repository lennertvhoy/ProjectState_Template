import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import notes


class NotesTests(unittest.TestCase):
    def setUp(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        patcher = mock.patch.dict(os.environ, {"NOTES_HOME": home.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = notes.main(list(argv))
        return code, out.getvalue()

    def test_add_numbers_notes_from_one(self):
        self.assertEqual(notes.add("alpha"), {"id": 1, "text": "alpha"})
        self.assertEqual(notes.add("beta"), {"id": 2, "text": "beta"})

    def test_render_numbers_each_note(self):
        notes.add("alpha")
        notes.add("beta")
        self.assertEqual(notes.render(notes.load()), ["1. alpha", "2. beta"])

    def test_cli_add_then_list(self):
        self.assertEqual(self.run_cli("add", "alpha")[0], 0)
        self.assertEqual(self.run_cli("add", "beta")[0], 0)
        self.assertEqual(self.run_cli("list"), (0, "1. alpha\n2. beta\n"))

    def test_unknown_command_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(notes.main(["frobnicate"]), 2)

    def test_missing_notes_home_is_reported(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("NOTES_HOME")
            with self.assertRaises(SystemExit):
                notes.load()


if __name__ == "__main__":
    unittest.main()
