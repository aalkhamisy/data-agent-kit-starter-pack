#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys
import yaml

def validate_skill(skill_md_path):
    print(f"Checking {skill_md_path}...")
    try:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {skill_md_path}: {e}")
        return False

    # Extract frontmatter
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        print(f"Error: No YAML frontmatter found in {skill_md_path}")
        return False

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except Exception as e:
        print(f"Error parsing YAML in {skill_md_path}: {e}")
        return False

    if not isinstance(frontmatter, dict):
        print(f"Error: Frontmatter in {skill_md_path} is not a dictionary")
        return False

    errors = []

    # Check license
    license = frontmatter.get("license")
    if license != "Apache-2.0":
        errors.append(f"Expected 'license: Apache-2.0', got '{license}'")

    # Check metadata
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("Missing or invalid 'metadata' block")
    else:
        # Check publisher
        publisher = metadata.get("publisher")
        if publisher != "google":
            errors.append(f"Expected 'metadata.publisher: google', got '{publisher}'")
        
        # Check version
        version = metadata.get("version")
        if not version:
            errors.append("Missing 'metadata.version'")
        elif not re.match(r"^v[0-9]+$", str(version)):
            errors.append(f"Invalid 'metadata.version' format '{version}'. Expected format like 'v1'")

    if errors:
        for err in errors:
            print(f"  FAILED: {err}")
        return False
    
    print("  PASSED")
    return True

def main():
    skills_dir = "skills"
    if not os.path.exists(skills_dir):
        print(f"Error: {skills_dir} directory not found")
        sys.exit(1)

    failed = False
    for root, _, files in os.walk(skills_dir):
        for file in files:
            if file == "SKILL.md":
                skill_md_path = os.path.join(root, file)
                if not validate_skill(skill_md_path):
                    failed = True

    if failed:
        sys.exit(1)
    else:
        print("All skills validated successfully.")

if __name__ == "__main__":
    main()
