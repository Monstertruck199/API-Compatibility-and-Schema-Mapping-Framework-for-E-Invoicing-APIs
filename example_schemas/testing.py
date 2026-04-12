"""
Schema Compatibility Test Suite
================================
Compares all invoice JSON schemas against each other using the compatibility engine.

Usage (from the project folder):
    python test_suite.py                          # run all tests, print summary
    python test_suite.py --verbose                # include per-issue detail
    python test_suite.py --pair minimal complete  # compare two specific schemas

The suite uses only what is available in the current backend:
    • extract_JSON_schema.infer_schema   – build a schema from raw JSON data
    • compatibility_engine.compare_schemas – compare two schemas
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from itertools import combinations
from pprint import pformat
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
 
if not os.path.isdir(BACKEND_DIR):
    print(
        f"ERROR: Could not find the backend directory.\n"
        f"  Expected: {BACKEND_DIR}\n"
        f"  This script must live at <repo-root>/example_schemas/testing.py"
    )
    sys.exit(1)
 
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
 
# ---------------------------------------------------------------------------
# Imports – only use modules that exist in the current backend.
# Optional modules (mapping_engine, schema_transformer) are imported
# gracefully so the suite still runs if they are not yet implemented.
# ---------------------------------------------------------------------------
from extract_JSON_schema import infer_schema
from compatibility_engine import compare_schemas
 
try:
    from mapping_engine import build_mapping, build_transformer
    HAS_MAPPING = True
except ImportError:
    HAS_MAPPING = False
 
try:
    from schema_transformer import generate_transform_code, transform_to_xml
    HAS_TRANSFORMER = True
except ImportError:
    HAS_TRANSFORMER = False

# ---------------------------------------------------------------------------
# Locate every *.json file in the same directory as this script
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_FILES: Dict[str, str] = {
    os.path.splitext(f)[0]: os.path.join(SCRIPT_DIR, f)
    for f in sorted(os.listdir(SCRIPT_DIR))
    if f.endswith(".json")
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_schema(name: str) -> Dict[str, Any]:
    path = JSON_FILES[name]
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return infer_schema(data)


COMPAT_SYMBOL = {
    "directly_compatible":     "dc",
    "compatible_with_mapping": "cwm",
    "incompatible":            "i",
    "same_schema":             "ss",
}

COMPAT_ORDER = {
    "directly_compatible":     0,
    "compatible_with_mapping": 1,
    "incompatible":            2,
    "same_schema":             3,
}

def fmt_label(label: str) -> str:
    symbol = COMPAT_SYMBOL.get(label, "-")
    return f"{symbol} {label.replace('_', ' ').title()}"


# ---------------------------------------------------------------------------
# Core test runner
# ---------------------------------------------------------------------------

def run_pair(
    source_name: str,
    target_name: str,
    schemas: Dict[str, Dict[str, Any]],
    verbose: bool = False,
) -> Dict[str, Any]:
    """Compare one (source, target) pair and return the result dict."""
    result = compare_schemas(
        source_schema=schemas[source_name],
        target_schema=schemas[target_name],
        source_name=source_name,
        target_name=target_name,
    )
    return result


def run_all(
    names: List[str],
    schemas: Dict[str, Dict[str, Any]],
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Run every ordered pair (A→B) and return results."""
    results = []
    pairs = list(combinations(names, 2))          # unordered – we run both directions
    ordered_pairs: List[Tuple[str, str]] = []
    for a, b in pairs:
        ordered_pairs.append((a, b))
        ordered_pairs.append((b, a))

    total = len(ordered_pairs)
    for idx, (src, tgt) in enumerate(ordered_pairs, 1):
        print(f"  [{idx:>3}/{total}] {src} → {tgt} …", end="\r", flush=True)
        result = run_pair(src, tgt, schemas, verbose)
        results.append(result)

    print(" " * 80, end="\r")   # clear progress line
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(results: List[Dict[str, Any]], verbose: bool) -> None:
    # Counts
    counts: Dict[str, int] = {}
    for r in results:
        c = r.get("compatibility", "unknown")
        counts[c] = counts.get(c, 0) + 1

    total = len(results)
    print("\n" + "=" * 70)
    print("COMPATIBILITY TEST SUITE – SUMMARY")
    print("=" * 70)
    print(f"Total pairs tested : {total}")
    for label, count in sorted(counts.items(), key=lambda kv: COMPAT_ORDER.get(kv[0], 9)):
        bar = "█" * count
        print(f"  {fmt_label(label):<40} {count:>3}  {bar}")
    print()

    # Detailed table
    col_w = max(len(r["source"]) for r in results) + 2
    col_w2 = max(len(r["target"]) for r in results) + 2

    header = f"{'SOURCE':<{col_w}} {'TARGET':<{col_w2}} {'COMPAT':<30} BLOCK  MAP  INFO"
    print(header)
    print("-" * len(header))

    for r in sorted(results, key=lambda x: (COMPAT_ORDER.get(x["compatibility"], 9), x["source"], x["target"])):
        src = r["source"]
        tgt = r["target"]
        compat = r.get("compatibility", "unknown")
        summary = r.get("summary", {})
        blocking = summary.get("blocking_issues", 0)
        mapping  = summary.get("mapping_issues", 0)
        info     = summary.get("informational_issues", 0)

        symbol = COMPAT_SYMBOL.get(compat, "-")
        label = compat.replace("_", " ").title()
        compat_col = f"{symbol} {label}"

        print(f"{src:<{col_w}} {tgt:<{col_w2}} {compat_col:<30} {blocking:>5}  {mapping:>3}  {info:>4}")

        if verbose and r.get("issues"):
            for issue in r["issues"]:
                kind = issue.get("kind", "?")
                code = issue.get("code", "?")
                msg  = issue.get("message", "")
                src_path = issue.get("source_path", "")
                tgt_path = issue.get("target_path", "")
                print(f"    [{kind.upper():^8}] {code}")
                print(f"             src: {src_path}  →  tgt: {tgt_path}")
                print(f"             {msg}")
                suggestion = issue.get("suggestion", "")
                if suggestion:
                    print(f"             💡 {suggestion}")
            print()

    print("=" * 70)


def print_pair_detail(result: Dict[str, Any]) -> None:
    """Pretty-print a single pair result."""
    src   = result["source"]
    tgt   = result["target"]
    compat = result.get("compatibility", "unknown")
    summary = result.get("summary", {})

    print(f"\n{'─'*60}")
    print(f"  {src}  →  {tgt}")
    print(f"  {fmt_label(compat)}")
    print(f"  Blocking: {summary.get('blocking_issues',0)}  "
          f"Mapping: {summary.get('mapping_issues',0)}  "
          f"Info: {summary.get('informational_issues',0)}")
    print(f"{'─'*60}")

    for issue in result.get("issues", []):
        kind = issue.get("kind", "?").upper()
        code = issue.get("code", "?")
        msg  = issue.get("message", "")
        src_path = issue.get("source_path", "")
        tgt_path = issue.get("target_path", "")
        suggestion = issue.get("suggestion", "")

        tag = {"BLOCKING": "i", "MAPPING": "cwm", "INFO": "info"}.get(kind, "•")
        print(f"\n  {tag} [{kind}] {code}")
        print(f"     src : {src_path}")
        print(f"     tgt : {tgt_path}")
        print(f"     msg : {msg}")
        if suggestion:
            print(f"suggestion:  {suggestion}")

    if not result.get("issues"):
        print("  No issues found – schemas are directly compatible.")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Schema compatibility test suite for all invoice JSON examples."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-issue detail in the summary table.",
    )
    parser.add_argument(
        "--pair", "-p",
        nargs=2,
        metavar=("SOURCE", "TARGET"),
        help="Compare only these two schemas by name (without .json extension).",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available schema names and exit.",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Write full JSON results to FILE.",
    )
    args = parser.parse_args()

    if args.list:
        print("Available schemas:")
        for name in JSON_FILES:
            print(f"  {name}")
        return

    print(f"Loading {len(JSON_FILES)} schemas …")
    schemas: Dict[str, Dict[str, Any]] = {}
    for name in JSON_FILES:
        schemas[name] = load_schema(name)
        print(f"  ✓ {name}")

    names = list(JSON_FILES.keys())

    if args.pair:
        src_name, tgt_name = args.pair
        for n in (src_name, tgt_name):
            if n not in schemas:
                print(f"ERROR: '{n}' not found. Use --list to see available schemas.")
                sys.exit(1)
        print(f"\nComparing {src_name} → {tgt_name} …\n")
        result = run_pair(src_name, tgt_name, schemas, verbose=args.verbose)
        print_pair_detail(result)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            print(f"Results written to {args.output}")
        return

    print(f"\nRunning all {len(names) * (len(names) - 1)} ordered pairs …\n")
    results = run_all(names, schemas, verbose=args.verbose)

    print_summary(results, verbose=args.verbose)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nFull results written to {args.output}")


if __name__ == "__main__":
    main()