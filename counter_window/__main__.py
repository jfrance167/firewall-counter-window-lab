"""CLI reads files only; output files are created exclusively."""
import argparse
from pathlib import Path
import sys
from .compare import compare
from .report import incomplete, render, visible
from .snapshot import InputError, load_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare offline counter snapshots; zero never proves unreachability.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--assume-continuity", action="store_true",
                        help="request explicitly conditional rates; matching non-null epoch assertions required")
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--output", type=Path, help="create a new file; refuse overwrite")
    args = parser.parse_args(argv)
    try:
        result = compare(load_snapshot(args.before), load_snapshot(args.after),
                         assume_continuity=args.assume_continuity)
        output = render(result, args.format)
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(output)
        else:
            sys.stdout.write(output)
    except (OSError, InputError, UnicodeError) as error:
        print("counter-window: " + visible(str(error)), file=sys.stderr)
        return 2
    return 3 if incomplete(result) else 0


if __name__ == "__main__":
    raise SystemExit(main())
