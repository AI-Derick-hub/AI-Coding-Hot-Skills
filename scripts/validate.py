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
        print("缺少 data/skills.json、data/daily-report.json 或 site/index.html。请先运行 scripts/update.py。")
        return 1
    payload = json.loads(skills_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    page = page_path.read_text(encoding="utf-8")
    errors.extend(lib.validate_dataset(payload))
    errors.extend(lib.validate_report(report, payload["skills"]))
    for skill in payload["skills"]:
        if skill["name"] not in page:
            errors.append(f"页面缺少 {skill['name']}")
        if skill["source_url"] not in page:
            errors.append(f"页面缺少来源 {skill['id']}")
        if skill.get("download_available") and skill["download_url"] not in page:
            errors.append(f"页面缺少下载链接 {skill['id']}")
    for phrase in ("热门 AI 编程 Skills", "来源", "下载", "今日新增", "data/daily-report.json"):
        if phrase not in page:
            errors.append(f"页面缺少文案：{phrase}")
    latest = ROOT / "docs" / "latest-update.md"
    if not latest.exists():
        errors.append("缺少 docs/latest-update.md")
    elif report["run_at"] not in latest.read_text(encoding="utf-8"):
        errors.append("latest-update.md 与日报时间不一致")
    published_skills = ROOT / "site" / "data" / "skills.json"
    published_report = ROOT / "site" / "data" / "daily-report.json"
    if not published_skills.exists() or not published_report.exists():
        errors.append("站点副本缺少 data/skills.json 或 data/daily-report.json")
    if errors:
        print("校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"校验通过：{len(payload['skills'])} 个技能，日报 {report['run_date']}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
