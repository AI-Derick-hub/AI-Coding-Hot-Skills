#!/usr/bin/env python3
"""Check the committed catalog, daily report, and generated page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import skills_lib as lib

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    skills_path = ROOT / "data" / "skills.json"
    report_path = ROOT / "data" / "daily-report.json"
    page_path = ROOT / "site" / "index.html"
    errors = []
    if not skills_path.exists() or not report_path.exists() or not page_path.exists():
        print("Missing data/skills.json, data/daily-report.json, or site/index.html. Run scripts/update.py first.")
        return 1
    payload = json.loads(skills_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    page = page_path.read_text(encoding="utf-8")
    errors.extend(lib.validate_dataset(payload))
    errors.extend(lib.validate_report(report, payload["skills"]))
    for skill in payload["skills"]:
        if skill["name"] not in page:
            errors.append(f"page is missing {skill['name']}")
        if skill["source_url"] not in page:
            errors.append(f"page is missing the source for {skill['id']}")
        if skill.get("download_available") and skill["download_url"] not in page:
            errors.append(f"page is missing the download for {skill['id']}")
    for phrase in ("Hot AI Coding Skills", "Source", "Download", "New today", "data/daily-report.json"):
        if phrase not in page:
            errors.append(f"page is missing copy: {phrase}")
    latest = ROOT / "docs" / "latest-update.md"
    if not latest.exists():
        errors.append("missing docs/latest-update.md")
    elif report["run_at"] not in latest.read_text(encoding="utf-8"):
        errors.append("latest-update.md does not match the report timestamp")
    published_skills = ROOT / "site" / "data" / "skills.json"
    published_report = ROOT / "site" / "data" / "daily-report.json"
    if not published_skills.exists() or not published_report.exists():
        errors.append("the published site is missing data/skills.json or data/daily-report.json")
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed: {len(payload['skills'])} skills, report {report['run_date']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
