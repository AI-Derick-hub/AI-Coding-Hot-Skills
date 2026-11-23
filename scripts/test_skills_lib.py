#!/usr/bin/env python3
"""Unit tests for catalog rules. No network and no database."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import skills_lib as lib


ROOT = Path(__file__).resolve().parents[1]


class RelevanceTests(unittest.TestCase):
    def test_official_skill_repo_is_relevant(self):
        ok, _reason = lib.relevance_reason(
            {
                "name": "skills",
                "description": "Public repository for Agent Skills",
                "topics": ["agent-skills"],
                "fork": False,
            }
        )
        self.assertTrue(ok)

    def test_red_team_bundle_is_excluded(self):
        ok, reason = lib.relevance_reason(
            {
                "name": "Claude-BugHunter",
                "description": "A skill bundle for external red-team work",
                "topics": ["claude-skills"],
                "fork": False,
            }
        )
        self.assertFalse(ok)
        self.assertIn("offensive", reason)

    def test_marketing_skill_is_excluded(self):
        ok, _reason = lib.relevance_reason(
            {
                "name": "marketingskills",
                "description": "Marketing skills for Claude Code and AI agents",
                "topics": ["agent-skills"],
                "fork": False,
            }
        )
        self.assertFalse(ok)

    def test_converter_tool_is_excluded(self):
        ok, _reason = lib.relevance_reason(
            {
                "name": "Skill_Seekers",
                "description": "Convert documentation websites into Claude AI skills",
                "topics": ["claude-skills"],
                "fork": False,
            }
        )
        self.assertFalse(ok)

    def test_boilerplate_and_trading_and_persona_are_excluded(self):
        saas = {
            "name": "open-saas",
            "description": "A SaaS boilerplate. AI-ready with tailored AGENTS.md, skills, and Claude Code plugin.",
            "topics": ["saas"],
            "fork": False,
        }
        trading = {
            "name": "claude-trading-skills",
            "description": "Claude Code skills for equity investors and traders.",
            "topics": [],
            "fork": False,
        }
        persona = {
            "name": "nuwa-skill",
            "description": "Distill how anyone thinks.",
            "topics": ["claude-skills", "claude-code"],
            "fork": False,
        }
        novel = {
            "name": "chinese-novelist-skill",
            "description": "AI " + lib._cp("5199 5c0f 8bf4") + " for a coding agent " + lib._cp("7f51 6587"),
            "topics": ["claude-code"],
            "fork": False,
        }
        self.assertFalse(lib.relevance_reason(saas)[0])
        self.assertFalse(lib.relevance_reason(trading)[0])
        self.assertFalse(lib.relevance_reason(persona)[0])
        self.assertFalse(lib.relevance_reason(novel)[0])
        persona_list = {
            "name": "awesome-persona-distill-skills",
            "description": "Curated list of Agent Skills centered on people and perspectives",
            "topics": ["agent-skills"],
            "fork": False,
        }
        self.assertFalse(lib.relevance_reason(persona_list)[0])

    def test_ui_and_official_skill_repos_stay(self):
        ui = {
            "name": "ui-ux-pro-max-skill",
            "description": "An AI skill that provides design intelligence for building professional UI/UX.",
            "topics": ["claude-code", "cursor-ai"],
            "fork": False,
        }
        official = {
            "name": "skills",
            "description": "Public repository for Agent Skills",
            "topics": ["agent-skills"],
            "fork": False,
        }
        slides = {
            "name": "Kami",
            "description": "Layout rules that let AI agents export editable PowerPoint.",
            "topics": ["agent-skills", "pptx"],
            "fork": False,
        }
        self.assertTrue(lib.relevance_reason(ui)[0])
        self.assertTrue(lib.relevance_reason(official)[0])
        self.assertTrue(lib.relevance_reason(slides)[0])

    def test_generic_coding_article_is_excluded(self):
        ok, _reason = lib.relevance_reason(
            {
                "name": "30-seconds-of-code",
                "description": "Coding articles to level up your development skills",
                "topics": [],
                "fork": False,
            }
        )
        self.assertFalse(ok)


class CategoryTests(unittest.TestCase):
    def test_readme_adds_ppt_and_testing_without_dropping_development(self):
        categories = lib.categorize(
            "skills",
            "Public repository for Agent Skills",
            ["agent-skills"],
            "Development and technical skills, testing web apps, and skills/pptx.",
        )
        self.assertIn("Development", categories)
        self.assertIn("Testing", categories)
        self.assertIn("Generate PPT", categories)

    def test_diagram_and_ppt_repo(self):
        categories = lib.categorize(
            "drawio-skill",
            "Agent skill that creates draw.io architecture diagrams and PPTX exports.",
            ["agent-skills", "diagram", "pptx"],
            "",
        )
        self.assertIn("Design diagrams", categories)
        self.assertIn("Generate PPT", categories)

    def test_planning_repo(self):
        categories = lib.categorize(
            "planning-with-files",
            "Persistent file-based planning for AI coding agents.",
            ["agent-skills", "planning", "coding-agent"],
            "",
        )
        self.assertEqual(categories[0], "Requirements")
        self.assertIn("Development", categories)

    def test_fingerprint_keeps_categories_stable_until_text_changes(self):
        first = lib.category_fingerprint("skills", "Agent Skills", ["agent-skills"])
        second = lib.category_fingerprint("skills", "Agent Skills", ["agent-skills"])
        changed = lib.category_fingerprint("skills", "Agent Skills plus planning", ["agent-skills"])
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_persona_skill_is_not_forced_into_development(self):
        categories = lib.categorize(
            "nuwa-skill",
            "Distill how anyone thinks.",
            ["agent-skills", "claude-code", "mental-models"],
            "",
        )
        self.assertEqual(categories, [])

    def test_battle_tested_is_not_a_testing_category(self):
        categories = lib.categorize(
            "agent-skills",
            "Production-grade engineering skills for AI coding agents. Battle-tested workflows.",
            ["agent-skills"],
            "",
        )
        self.assertIn("Development", categories)
        self.assertNotIn("Testing", categories)


class ScheduleTests(unittest.TestCase):
    def test_run_date_is_the_shanghai_day_for_a_2300_utc_run(self):
        moment = datetime(2026, 11, 22, 23, 0, tzinfo=timezone.utc)
        self.assertEqual(lib.shanghai_now(moment).hour, 7)
        self.assertEqual(lib.run_date(moment), "2026-11-23")


class GrowthTests(unittest.TestCase):
    def test_history_sums_calendar_days(self):
        # 2026-11-15 is a Sunday. days[0] is that date.
        week = datetime(2026, 11, 15, tzinfo=timezone.utc).timestamp()
        growth = lib.summarize_star_history(
            [{"week": int(week), "total": 28, "days": [1, 2, 3, 4, 5, 6, 7]}],
            today=date(2026, 11, 22),
        )
        self.assertTrue(growth["available"])
        self.assertTrue(growth["partial"])
        self.assertEqual(growth["history_through"], "2026-11-21")
        # 7-day window ends on Nov 22 and starts Nov 16, so Nov 15 is only in the 30-day sum.
        self.assertEqual(growth["stars_7d"], 27)
        self.assertEqual(growth["stars_30d"], 28)

    def test_growth_rule_accepts_fast_small_repo(self):
        growth = {
            "available": True,
            "partial": False,
            "stars_7d": 120,
            "stars_30d": 180,
        }
        ok, rule = lib.qualifies(800, growth)
        self.assertTrue(ok)
        self.assertEqual(rule, "growth")

    def test_growth_rule_rejects_slow_repo(self):
        growth = {
            "available": True,
            "partial": False,
            "stars_7d": 12,
            "stars_30d": 40,
        }
        ok, rule = lib.qualifies(900, growth)
        self.assertFalse(ok)
        self.assertNotEqual(rule, "growth")

    def test_star_threshold_wins_over_growth(self):
        ok, rule = lib.qualifies(2000, {"available": True, "stars_7d": 1, "stars_30d": 1})
        self.assertTrue(ok)
        self.assertEqual(rule, "stars")

    def test_partial_history_can_qualify_on_a_lower_bound(self):
        growth = {
            "available": True,
            "partial": True,
            "stars_7d": 150,
            "stars_30d": 400,
        }
        ok, rule = lib.qualifies(500, growth)
        self.assertTrue(ok)
        self.assertEqual(rule, "growth")

    def test_snapshots_need_age(self):
        points = [
            {"date": "2026-11-22", "stars": 100},
            {"date": "2026-11-21", "stars": 90},
        ]
        growth = lib.summarize_snapshots(points, date(2026, 11, 22), 100)
        self.assertFalse(growth["available"])
        older = [
            {"date": "2026-11-22", "stars": 100},
            {"date": "2026-11-15", "stars": 80},
            {"date": "2026-10-23", "stars": 10},
        ]
        matured = lib.summarize_snapshots(older, date(2026, 11, 22), 100)
        self.assertTrue(matured["available"])
        self.assertEqual(matured["stars_7d"], 20)
        self.assertEqual(matured["stars_30d"], 90)


class DownloadAndReportTests(unittest.TestCase):
    def test_documented_install_comes_from_a_fence(self):
        readme = "See this:\n\n```bash\nnpx skills add jimliu/baoyu-skills\n```\n"
        self.assertEqual(lib.extract_documented_install(readme), "npx skills add jimliu/baoyu-skills")

    def test_release_asset_prefers_zip(self):
        url = lib.choose_release_asset(
            [
                {"name": "pkg.tar.gz", "browser_download_url": "https://example.com/pkg.tar.gz"},
                {"name": "pkg.zip", "browser_download_url": "https://example.com/pkg.zip"},
            ]
        )
        self.assertEqual(url, "https://example.com/pkg.zip")

    def test_page_escapes_description(self):
        skill = sample_skill()
        skill["description"] = '<img src=x onerror="alert(1)">'
        page = lib.render_page(sample_payload([skill]))
        self.assertNotIn("<img", page)
        self.assertIn("&lt;img", page)
        self.assertIn("Source", page)
        self.assertIn("Download", page)

    def test_report_validation_requires_source_and_download_fields(self):
        skill = sample_skill()
        report = {
            "schema_version": 1,
            "timezone": "Asia/Shanghai",
            "run_at": "2026-11-22T08:00:00+08:00",
            "run_date": "2026-11-22",
            "total_skills": 1,
            "new_today": 1,
            "updated_today": 0,
            "removed_today": 0,
            "new_items": [
                {
                    "id": skill["id"],
                    "name": skill["name"],
                    "categories": skill["categories"],
                    "stars": skill["stars"],
                    "source": skill["source_url"],
                    "download": skill["download_url"],
                    "link": skill["source_url"],
                    "reason": skill["notable_zh"],
                }
            ],
            "updated_items": [],
            "removed_items": [],
        }
        self.assertEqual(lib.validate_report(report, [skill]), [])
        self.assertEqual(lib.validate_dataset(sample_payload([skill])), [])


def sample_skill() -> dict:
    return {
        "id": "anthropics/skills",
        "name": "skills",
        "full_name": "anthropics/skills",
        "description": "Public repository for Agent Skills",
        "categories": ["Development"],
        "source_url": "https://github.com/anthropics/skills",
        "download_url": "https://github.com/anthropics/skills/archive/refs/heads/main.zip",
        "download_available": True,
        "download_note": "Verified GitHub source archive.",
        "install_command": "git clone https://github.com/anthropics/skills.git",
        "stars": 2000,
        "forks": 10,
        "growth": {"stars_7d": 10, "stars_30d": 40, "history_through": "2026-11-21", "partial": True},
        "qualification": {"rule": "stars"},
        "notable_zh": "Public stars: 2,000, which meets the 2,000-star bar.",
        "pushed_date": "2026-11-16",
        "first_seen": "2026-11-22",
        "archived": False,
    }


def sample_payload(skills: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "generated_at": "2026-11-22T08:00:00+08:00",
        "run_date": "2026-11-22",
        "updated_today": 0,
        "criteria": lib.criteria_document(),
        "skills": skills,
    }


class FileTests(unittest.TestCase):
    def test_library_has_no_database_client(self):
        source = (ROOT / "scripts" / "skills_lib.py").read_text(encoding="utf-8")
        for banned in ("sqlite", "postgres", "mongodb", "redis", "sqlalchemy"):
            self.assertNotIn(banned, source.lower())


if __name__ == "__main__":
    unittest.main()
