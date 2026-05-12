"""Rebuild the tree-sitter shared libraries with Java and Kotlin grammars.

Usage:
    1. Vendor the grammars (once):
        mkdir -p vendor
        git clone https://github.com/tree-sitter/tree-sitter-java vendor/tree-sitter-java
        git clone https://github.com/fwcd/tree-sitter-kotlin    vendor/tree-sitter-kotlin

    2. Build the .so files:
        python build_grammars.py

This produces ``parser/my-languages.so`` and ``call_graph/my-languages.so``,
each containing both grammars so the same Python process can switch between
``Language(..., 'java')`` and ``Language(..., 'kotlin')`` at runtime.
"""

from pathlib import Path

from tree_sitter import Language


VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
GRAMMARS = [
    str(VENDOR_DIR / "tree-sitter-java"),
    str(VENDOR_DIR / "tree-sitter-kotlin"),
]
TARGETS = [
    "parser/my-languages.so",
    "call_graph/my-languages.so",
]


def main() -> None:
    for grammar in GRAMMARS:
        if not Path(grammar).exists():
            raise SystemExit(
                f"missing grammar directory: {grammar}\n"
                "Vendor the grammars first (see this file's docstring)."
            )
    for target in TARGETS:
        print(f"building {target} ...")
        Language.build_library(target, GRAMMARS)
    print("done.")


if __name__ == "__main__":
    main()
