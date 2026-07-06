"""Unit tests for Copybara Starlark helper functions in copybara_helpers.bara.sky."""

import unittest


class MockObject:

  def __init__(self, *args, **kwargs):
    pass

  def __getattr__(self, name):
    return MockObject()

  def __call__(self, *args, **kwargs):
    return MockObject()

  def __add__(self, other):
    return MockObject()

  def __radd__(self, other):
    return MockObject()


class MockFile:

  def __init__(self, path):
    self.path = path


class MockCtx:

  def __init__(self, files_dict):
    # files_dict is a mapping of string paths to string contents
    self.files = [MockFile(path) for path in files_dict.keys()]
    self.files_dict = files_dict
    self.written = {}

  def run(self, glob_result):
    # pylint: disable=unused-argument
    return self.files

  def read_path(self, f):
    return self.files_dict[f.path]

  def write_path(self, f, content):
    self.written[f.path] = content


class CopybaraHelpersTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    # Read copybara_helpers.bara.sky and extract helper functions using exec()
    with open(
        "third_party/data_agent_kit/data_agent_common/skill_sync/copybara_helpers.bara.sky",
        "r",
        encoding="utf-8",
    ) as f:
      content = f.read()

    # Mock out Copybara specific globals to allow python to parse the file
    mock = MockObject()
    globals_dict = {
        "load": lambda *args, **kwargs: None,
        "glob": lambda *args, **kwargs: mock,
        "core": mock,
        "metadata": mock,
        "git": mock,
        "service": mock,
        "piper": mock,
        "authoring": mock,
    }
    # pylint: disable=exec-used
    exec(content, globals_dict)

    # Extract the helper functions for testing
    cls._define_skill_sync = staticmethod(
        globals_dict["define_skill_sync"]
    )
    cls._add_license_headers_impl = staticmethod(
        globals_dict["_add_license_headers_impl"]
    )
    cls._clean_skill_metadata_impl = staticmethod(
        globals_dict["_clean_skill_metadata_impl"]
    )
    cls._check_allowed_files = staticmethod(
        globals_dict["_check_allowed_files"]
    )
    cls._check_no_google3_imports = staticmethod(
        globals_dict["_check_no_google3_imports"]
    )
    cls.BUILD_LICENSE_HEADER = globals_dict["BUILD_LICENSE_HEADER"]

  def test_add_license_headers_prepends_when_missing(self):
    # File has no license header
    ctx = MockCtx({"scripts/test.py": "def hello():\n    print('hello')\n"})
    self._add_license_headers_impl(ctx)

    self.assertIn("scripts/test.py", ctx.written)
    self.assertEqual(
        ctx.written["scripts/test.py"],
        self.BUILD_LICENSE_HEADER + "def hello():\n    print('hello')\n",
    )

  def test_add_license_headers_does_nothing_if_header_exists(self):
    # File already has Copyright notice
    content = "# Copyright 2026 Google LLC\ndef hello():\n    print('hello')\n"
    ctx = MockCtx({"scripts/test.py": content})
    self._add_license_headers_impl(ctx)

    self.assertEqual(ctx.written, {})

  def test_add_license_headers_preserves_shebang(self):
    # File has shebang at the top
    ctx = MockCtx({
        "scripts/test.py": (
            "#!/usr/bin/env python3\ndef hello():\n    print('hello')\n"
        )
    })
    self._add_license_headers_impl(ctx)

    self.assertIn("scripts/test.py", ctx.written)
    self.assertEqual(
        ctx.written["scripts/test.py"],
        "#!/usr/bin/env python3\n"
        + self.BUILD_LICENSE_HEADER
        + "def hello():\n    print('hello')\n",
    )

  def test_clean_skill_metadata_adds_missing_license_and_metadata(self):
    # SKILL.md without license or metadata blocks
    input_content = """---
name: my_skill
description: simple skill
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "description: simple skill\n"
        "license: Apache-2.0\n"
        "metadata:\n"
        "  version: v1\n"
        "  publisher: google\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].endswith("Some body text\n")
    )

  def test_clean_skill_metadata_standardizes_and_preserves_custom_fields(self):
    # SKILL.md with custom fields in metadata and old values
    input_content = """---
name: my_skill
license: old-license
metadata:
  custom_field: custom-value
  publisher: old-publisher
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "metadata:\n"
        "  custom_field: custom-value\n"
        "  publisher: google\n"
        "  version: v1\n"
        "license: Apache-2.0\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].endswith("Some body text\n")
    )

  def test_clean_skill_metadata_empty_metadata_block(self):
    # metadata: block exists but is empty
    input_content = """---
name: my_skill
metadata:
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "metadata:\n"
        "  version: v1\n"
        "  publisher: google\n"
        "license: Apache-2.0\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )

  def test_clean_skill_metadata_partially_filled_metadata_version_only(self):
    # metadata block has version: v1 but lacks publisher
    input_content = """---
name: my_skill
metadata:
  version: v1
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "metadata:\n"
        "  version: v1\n"
        "  publisher: google\n"
        "license: Apache-2.0\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )

  def test_clean_skill_metadata_partially_filled_metadata_publisher_only(self):
    # metadata block has publisher but lacks version
    input_content = """---
name: my_skill
metadata:
  publisher: old-pub
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "metadata:\n"
        "  publisher: google\n"
        "  version: v1\n"
        "license: Apache-2.0\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )

  def test_clean_skill_metadata_preserves_multiple_custom_metadata_fields(self):
    # metadata has multiple custom fields that must be preserved
    input_content = """---
name: my_skill
metadata:
  category: database
  publisher: old-pub
  tags:
    - spanner
    - sql
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "metadata:\n"
        "  category: database\n"
        "  publisher: google\n"
        "  tags:\n"
        "    - spanner\n"
        "    - sql\n"
        "  version: v1\n"
        "license: Apache-2.0\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )

  def test_clean_skill_metadata_no_frontmatter_boundaries_does_nothing(self):
    # File has no --- yaml boundaries
    input_content = (
        "Some plain text skill description without yaml frontmatter.\n"
    )
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    # Should not write to file
    self.assertEqual(ctx.written, {})

  def test_clean_skill_metadata_strips_top_level_publisher_and_version(self):
    # publisher and version keys misplaced at the top level
    input_content = """---
name: my_skill
publisher: misplaced-pub
version: v2
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "name: my_skill\n"
        "license: Apache-2.0\n"
        "metadata:\n"
        "  version: v1\n"
        "  publisher: google\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )

  def test_clean_skill_metadata_empty_frontmatter_block(self):
    # A mostly empty frontmatter block
    input_content = """---
---
Some body text
"""
    ctx = MockCtx({"my_skill/SKILL.md": input_content})
    self._clean_skill_metadata_impl(ctx)

    self.assertIn("my_skill/SKILL.md", ctx.written)
    expected_frontmatter = (
        "---\n"
        "license: Apache-2.0\n"
        "metadata:\n"
        "  version: v1\n"
        "  publisher: google\n"
        "---\n"
    )
    self.assertTrue(
        ctx.written["my_skill/SKILL.md"].startswith(expected_frontmatter)
    )

  def test_check_allowed_files_returns_transformation(self):
    # Verify that calling _check_allowed_files parses without error and
    # returns a list containing the validation core.verify_match mock.
    result = self._check_allowed_files()
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 1)

  def test_check_no_google3_imports_returns_transformation(self):
    # Verify that calling _check_no_google3_imports parses without error and
    # returns a list containing the validation core.verify_match mock.
    result = self._check_no_google3_imports()
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 1)

  def test_define_skill_sync_registers_workflow_without_error(self):
    # Verify that calling define_skill_sync registers both core.workflow and
    # service.migration objects correctly without throwing any errors.
    mock_glob = MockObject()
    self._define_skill_sync(
        origin_files=mock_glob,
        source_path=(
            "google3/blobstore2/storage_management/gemini/"
            "si_agent/skills/gcs_security_assessment"
        ),
        skill_name="gcs_security_assessment",
        team_name="GCS",
        owner_mdb="gcs-eng",
        contact_email="gcs-eng@google.com",
    )


if __name__ == "__main__":
  unittest.main()
