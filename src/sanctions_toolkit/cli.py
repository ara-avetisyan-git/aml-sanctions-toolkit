"""Command-line interface: download, export, diff and screen UN sanctions data."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import __version__
from .diff import diff_lists, to_markdown, write_csv
from .screening import read_customers, screen_customers, summarize, write_results
from .un_loader import UN_CONSOLIDATED_URL, download, parse_file


def _cmd_download(args: argparse.Namespace) -> int:
    path = download(args.out_dir, url=args.url)
    parsed = parse_file(path)
    print(f"Saved {path}  (generated: {parsed.date_generated or 'n/a'}, records: {len(parsed.parties)})")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    parsed = parse_file(args.input)
    fields = ["reference_number", "data_id", "party_type", "name", "original_script_name", "aliases",
              "dates_of_birth", "nationalities", "list_type", "listed_on", "last_updated", "comments"]
    with open(args.output, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(fields)
        for p in parsed.parties:
            writer.writerow([" | ".join(v) if isinstance(v := getattr(p, f), tuple) else v for f in fields])
    print(f"Wrote {len(parsed.parties)} records to {args.output}")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    old, new = parse_file(args.old), parse_file(args.new)
    result = diff_lists(list(old.parties), list(new.parties))
    report = to_markdown(result, old_label=old.date_generated or Path(args.old).name,
                         new_label=new.date_generated or Path(args.new).name)
    if args.report_md:
        Path(args.report_md).write_text(report, encoding="utf-8")
    else:
        print(report)
    if args.report_csv:
        write_csv(result, args.report_csv)
    print(f"added={len(result.added)} removed={len(result.removed)} changed={len(result.changed)}", file=sys.stderr)
    return 0


def _cmd_screen(args: argparse.Namespace) -> int:
    parsed = parse_file(args.list)
    customers = read_customers(args.customers)
    rows = screen_customers(customers, parsed.parties, list_version=parsed.date_generated,
                            review_threshold=args.review, match_threshold=args.match, top_n=args.top)
    write_results(rows, args.output)
    counts = summarize(rows)
    print(f"Screened {len(customers)} customers against {len(parsed.parties)} listed parties "
          f"(list generated {parsed.date_generated or 'n/a'}).")
    for status in ("POTENTIAL MATCH", "REVIEW", "CLEAR"):
        print(f"  {status:<16} {counts.get(status, 0)}")
    print(f"Results: {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sanctions-toolkit", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("download", help="Download the UN consolidated list (XML)")
    p.add_argument("--out-dir", default="data/raw")
    p.add_argument("--url", default=UN_CONSOLIDATED_URL)
    p.set_defaults(func=_cmd_download)

    p = sub.add_parser("export", help="Flatten the XML list into a CSV")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_export)

    p = sub.add_parser("diff", help="Compare two versions of the list")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--report-md")
    p.add_argument("--report-csv")
    p.set_defaults(func=_cmd_diff)

    p = sub.add_parser("screen", help="Screen a customer CSV against the list")
    p.add_argument("--list", required=True, help="consolidated.xml file")
    p.add_argument("--customers", required=True, help="CSV: customer_id,name[,date_of_birth]")
    p.add_argument("--output", required=True)
    p.add_argument("--review", type=float, default=80.0, help="score from which a hit goes to review")
    p.add_argument("--match", type=float, default=90.0, help="score from which a hit is a potential match")
    p.add_argument("--top", type=int, default=3, help="max hits per customer")
    p.set_defaults(func=_cmd_screen)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
