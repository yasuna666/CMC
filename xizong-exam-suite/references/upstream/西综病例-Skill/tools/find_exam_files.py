#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def find_exam_files(search_root: Path, start_year: int, end_year: int):
    exam_files = []

    for path in search_root.rglob("*"):
        if not path.is_file():
            continue

        matched_year = next(
            (year for year in range(start_year, end_year + 1) if str(year) in path.name),
            None,
        )
        if matched_year is not None:
            exam_files.append((matched_year, path.name, path))

    return sorted(exam_files, key=lambda item: (item[0], str(item[2]).lower()))


def main():
    parser = argparse.ArgumentParser(description="搜索包含年份的真题文件。")
    parser.add_argument(
        "search_root",
        nargs="?",
        default=".",
        help="要搜索的根目录，默认是当前目录。",
    )
    parser.add_argument("--start-year", type=int, default=2005, help="起始年份。")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份。")
    parser.add_argument("--limit", type=int, default=20, help="最多显示多少条结果。")
    args = parser.parse_args()

    search_root = Path(args.search_root).resolve()
    exam_files = find_exam_files(search_root, args.start_year, args.end_year)

    print(f"Searching for exam files in: {search_root}")
    print("=" * 60)

    if exam_files:
        print(
            f"Found {len(exam_files)} files with years "
            f"{args.start_year}-{args.end_year}:\n"
        )
        for year, name, path in exam_files[: args.limit]:
            print(f"{year}: {name}")
            print(f"  {path}")
    else:
        print("No matching files found.")


if __name__ == "__main__":
    main()
