"""Diff parsing and filtering tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import diff as diff_mod  # noqa: E402

SAMPLE = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 line_one
-old_line
+new_line
+another_new
 line_three
diff --git a/package-lock.json b/package-lock.json
index 3333333..4444444 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,1 +1,1 @@
-old
+new
diff --git a/vendor/lib/util.py b/vendor/lib/util.py
index 5555555..6666666 100644
--- a/vendor/lib/util.py
+++ b/vendor/lib/util.py
@@ -1,1 +1,1 @@
-old
+new
"""


class TestDiff(unittest.TestCase):
    def test_parse_files_and_hunks(self):
        files = diff_mod.parse_diff(SAMPLE)
        self.assertEqual(len(files), 3)
        app = files[0]
        self.assertEqual(app.path, "src/app.py")
        self.assertEqual(app.added_text(), "new_line\nanother_new")
        self.assertEqual(app.removed_text(), "old_line")

    def test_filter_skips_lock_and_vendored(self):
        kept, skipped = diff_mod.prepare_diff(SAMPLE)
        self.assertEqual([f.path for f in kept], ["src/app.py"])
        self.assertIn("package-lock.json", skipped)
        self.assertIn("vendor/lib/util.py", skipped)

    def test_hunk_capping(self):
        big = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -0,0 +1,%d @@\n" % 50
        big += "\n".join("+line %d" % i for i in range(50)) + "\n"
        files = diff_mod.parse_diff(big)
        diff_mod.cap_hunks(files, max_lines=10)
        self.assertEqual(len(files[0].hunks[0].lines), 10)
        self.assertTrue(files[0].hunks[0].truncated)


if __name__ == "__main__":
    unittest.main()
