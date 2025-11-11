import json
import sys
import re
from pathlib import Path

REQUIRED_FIELDS = [
    "title",
    "subtitle",
    "author",
    "tags",
    "thumbnail",
    "license",
    "copyright",
]

def extract_frontmatter(md_text: str):
    """
    Extract YAML frontmatter block from a markdown string.
    Requires a leading '---' and a closing '---'.
    Returns the YAML block as text or None.
    """
    pattern = r"^---\s*(.*?)\s*---\s*"
    match = re.search(pattern, md_text, re.DOTALL)
    if not match:
        return None
    return match.group(1)


def field_exists(field: str, yaml_text: str) -> bool:
    """
    Simple check: tests whether a given field is present
    in the YAML text.
    """
    pattern = rf"^{field}:"     # field must start at beginning of a line
    return re.search(pattern, yaml_text, re.MULTILINE) is not None


def validate_notebook(path: Path):
    print(f"Validating {path} ...")

    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    if not nb.get("cells"):
        raise ValueError(f"{path}: Notebook contains no cells.")

    first_cell = nb["cells"][0]
    if first_cell.get("cell_type") != "markdown":
        raise ValueError(
            f"{path}: First cell must be a markdown cell containing YAML frontmatter."
        )

    md_source = "".join(first_cell.get("source", []))

    # Extract YAML block
    yaml_text = extract_frontmatter(md_source)
    if yaml_text is None:
        raise ValueError(
            f"{path}: Missing YAML frontmatter block ('--- ... ---') in first markdown cell."
        )

    # Check each required field
    missing = []
    for field in REQUIRED_FIELDS:
        if not field_exists(field, yaml_text):
            missing.append(field)

    if missing:
        raise ValueError(
            f"{path}: Missing required frontmatter fields: {', '.join(missing)}"
        )

    print(f"{path}: OK\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_notebook.py <notebook.ipynb> [...]", file=sys.stderr)
        sys.exit(1)

    errors = 0
    for nb_path in sys.argv[1:]:
        try:
            validate_notebook(Path(nb_path))
        except Exception as e:
            errors += 1
            print(f"ERROR: {e}", file=sys.stderr)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()