#!/usr/bin/env python3
"""
Script to automatically add setup_method with FEATURE_PREMIUM_NUTRITION to test files
"""

import os
import re


def add_setup_method_to_file(file_path: str) -> bool:
    """Add setup_method to all test classes in a file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all class definitions that start with "class Test"
    class_pattern = r'(class Test[^:]*:)\s*\n(\s*)"""[^"]*"""\s*\n'

    def replacement(match: re.Match[str]) -> str:
        class_line = match.group(1)
        indent = match.group(2)

        # Add setup_method after the class declaration and docstring
        setup_method = f'''
{indent}def setup_method(self):
{indent}    """Setup test environment"""
{indent}    os.environ["API_KEY"] = "test_key"
{indent}    os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

'''
        return (
            class_line
            + "\n"
            + match.group(2)
            + '"""'
            + match.group(0).split('"""', 2)[1]
            + '"""'
            + setup_method
        )

    # Check if file needs import os
    if "import os" not in content:
        # Add import os at the top after existing imports
        import_pattern = r"(import [^\n]*\nfrom [^\n]*\n)"
        if re.search(import_pattern, content):
            content = re.sub(import_pattern, r"\1import os\n", content, count=1)
        else:
            # Add at the very beginning
            content = "import os\n" + content

    # Apply the class pattern replacement
    new_content = re.sub(class_pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

    # Simple pattern for classes without proper docstrings
    simple_pattern = r"(class Test[^:]*:)\s*\n(\s*)(def test_[^(]*\()"

    def simple_replacement(match: re.Match[str]) -> str:
        class_line = match.group(1)
        indent = match.group(2)
        def_line = match.group(3)

        setup_method = f'''
{indent}def setup_method(self):
{indent}    """Setup test environment"""
{indent}    os.environ["API_KEY"] = "test_key"
{indent}    os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

{indent}{def_line}'''
        return class_line + setup_method

    new_content = re.sub(simple_pattern, simple_replacement, new_content, flags=re.MULTILINE)

    # Only write if content changed
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ Updated {file_path}")
        return True
    else:
        print(f"⏭️  Skipped {file_path} (no changes needed)")
        return False


def main() -> None:
    """Main function to process all coverage test files"""
    test_dir = "/Users/katsiarynakavaleuskaya/BMI-App_2025_clean/tests"

    # Find all test files with "coverage" in the name
    coverage_files = []
    for file in os.listdir(test_dir):
        if file.startswith("test_") and "coverage" in file and file.endswith(".py"):
            coverage_files.append(os.path.join(test_dir, file))

    print(f"Found {len(coverage_files)} coverage test files")

    updated_count = 0
    for file_path in sorted(coverage_files):
        if add_setup_method_to_file(file_path):
            updated_count += 1

    print(f"\n🎉 Updated {updated_count} out of {len(coverage_files)} files")


if __name__ == "__main__":
    main()
