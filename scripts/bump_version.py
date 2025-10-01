#!/usr/bin/env python3
"""
Version bump script for ts-topy.
Automatically updates version in pyproject.toml following semantic versioning.
"""
import argparse
import re
import sys
from pathlib import Path


def get_current_version(pyproject_path: Path) -> str:
    """Extract current version from pyproject.toml."""
    content = pyproject_path.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse semantic version string into major, minor, patch tuple."""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch)."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_version_in_file(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml file."""
    content = pyproject_path.read_text()
    updated_content = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content
    )
    pyproject_path.write_text(updated_content)


def main():
    """Main version bump function."""
    parser = argparse.ArgumentParser(
        description="Bump version in pyproject.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bump_version.py patch    # 0.2.1 -> 0.2.2
  python bump_version.py minor    # 0.2.1 -> 0.3.0
  python bump_version.py major    # 0.2.1 -> 1.0.0
  python bump_version.py --set 1.2.3  # Set specific version

Semantic versioning guide:
  - patch: Bug fixes, no API changes
  - minor: New features, backward compatible
  - major: Breaking changes, not backward compatible
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "bump_type",
        nargs="?",
        choices=["major", "minor", "patch"],
        help="Type of version bump"
    )
    group.add_argument(
        "--set",
        dest="set_version",
        help="Set specific version (e.g., 1.2.3)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )

    args = parser.parse_args()

    # Find pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found in current directory")
        sys.exit(1)

    try:
        current_version = get_current_version(pyproject_path)
        print(f"📦 Current version: {current_version}")

        if args.set_version:
            # Validate the set version format
            parse_version(args.set_version)
            new_version = args.set_version
        else:
            new_version = bump_version(current_version, args.bump_type)

        print(f"🚀 New version: {new_version}")

        if args.dry_run:
            print("🔍 Dry run - no changes made")
        else:
            update_version_in_file(pyproject_path, new_version)
            print("✅ Version updated in pyproject.toml")
            print()
            print("💡 Next steps:")
            print("   1. Review changes: git diff")
            print("   2. Commit changes: git add . && git commit -m 'bump version to {}'".format(new_version))
            print("   3. Tag release: git tag v{}".format(new_version))
            print("   4. Push changes: git push origin main --tags")

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
