#!/usr/bin/env python3
"""Refresh the in-repo skill catalog and rebuild the static site.

All state is written to JSON and Markdown files. This script does not open a
database connection and does not require SMTP.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import skills_lib as lib

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "site"
DOCS = ROOT / "docs"

SEARCH_QUERIES = [
    "topic:agent-skills stars:>=2000",
    "skill in:name stars:>=2000",
    "skills in:name stars:>=2000",
    "SKILL.md in:name,description stars:>=2000",
    "topic:agent-skills pptx OR powerpoint OR diagram in:description stars:>=2000",
]
GROWTH_QUERIES = [
    "topic:agent-skills stars:80..1999",
    "skill in:name stars:80..1999",
    "pptx OR powerpoint OR diagram skill in:description stars:80..1999",
]
# Repos confirmed during development as skill packs. They still have to pass
# the same relevance, category, and star-or-growth rules as search results.
SEEDS = [
    "anthropics/skills",
    "openai/skills",
    "obra/superpowers",
    "github/awesome-copilot",
    "addyosmani/agent-skills",
    "mattpocock/skills",
    "vercel-labs/agent-skills",
    "microsoft/skills",
    "VoltAgent/awesome-agent-skills",
    "ComposioHQ/awesome-claude-skills",
    "sickn33/agentic-awesome-skills",
    "travisvn/awesome-claude-skills",
    "wshobson/agents",
    "alirezarezvani/claude-skills",
    "Jeffallan/claude-skills",
    "nextlevelbuilder/ui-ux-pro-max-skill",
    "emilkowalski/skills",
    "Leonxlnx/taste-skill",
    "deanpeters/Product-Manager-Skills",
    "OthmanAdi/planning-with-files",
    "tt-a1i/archify",
    "cathrynlavery/diagram-design",
    "pbakaus/impeccable",
    "alchaincyf/huashu-design",
    "bergside/awesome-design-skills",
    "anthropics/defending-code-reference-harness",
    "Agents365-ai/drawio-skill",
    "ningzimu/codex-ppt-skill",
    "tw93/Kami",
    "tw93/Waza",
    "jnMetaCode/superpowers-zh",
    "rohitg00/awesome-claude-code-toolkit",
    "BehiSecc/awesome-claude-skills",
    "heilcheng/awesome-agent-skills",
]
MAX_GROWTH_CHECKS = 80
USER_AGENT = "ai-coding-hot-skills"


class GitHub:
    def __init__(self, token: str | None):
        self.token = token
        self.warnings: list[str] = []

    def request(self, url: str, accept: str | None = None, timeout: int = 40) -> tuple[int, dict, bytes]:
        headers = {
            "Accept": accept or "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        last_error = None
        for attempt in range(4):
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    body = response.read()
                    return response.status, dict(response.headers), body
            except urllib.error.HTTPError as error:
                last_error = error
                retry_after = error.headers.get("Retry-After") if error.headers else None
                if error.code in {403, 429} and attempt < 3:
                    delay = int(retry_after) if retry_after and retry_after.isdigit() else 15 * (attempt + 1)
                    if delay > 90:
                        break
                    time.sleep(delay)
                    continue
                if error.code in {502, 503, 504} and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                detail = error.read().decode("utf-8", "replace")[:300]
                raise RuntimeError(f"GitHub HTTP {error.code} for {url}: {detail}") from error
            except urllib.error.URLError as error:
                last_error = error
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"GitHub request failed for {url}: {error}") from error
        raise RuntimeError(f"GitHub request failed for {url}: {last_error}")

    def get_json(self, url: str, accept: str | None = None):
        _status, _headers, body = self.request(url, accept=accept)
        if not body:
            return None
        return json.loads(body.decode("utf-8"))

    def search_repos(self, query: str, pages: int = 1, per_page: int = 50, sort: str | None = None) -> list[dict]:
        found = []
        full_query = f"fork:false archived:false {query}"
        for page in range(1, pages + 1):
            params = {"q": full_query, "per_page": str(per_page), "page": str(page)}
            if sort:
                params["sort"] = sort
                params["order"] = "desc"
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(params)
            try:
                payload = self.get_json(url)
            except RuntimeError as error:
                self.warnings.append(f"搜索失败 {query}: {error}")
                break
            items = payload.get("items") or []
            found.extend(items)
            if len(items) < per_page:
                break
            time.sleep(2.5)
        time.sleep(2.5)
        return found


def github_token() -> str | None:
    for key in ("SKILL_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(key)
        if value:
            return value
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_from_api(item: dict) -> dict:
    license_info = item.get("license") or {}
    homepage = (item.get("homepage") or "").strip()
    return {
        "full_name": item["full_name"],
        "name": item.get("name") or item["full_name"].split("/")[-1],
        "description": item.get("description") or "",
        "stars": int(item.get("stargazers_count") or 0),
        "forks": int(item.get("forks_count") or 0),
        "topics": item.get("topics") or [],
        "html_url": item.get("html_url") or f"https://github.com/{item['full_name']}",
        "clone_url": item.get("clone_url") or f"https://github.com/{item['full_name']}.git",
        "default_branch": item.get("default_branch") or "main",
        "pushed_at": item.get("pushed_at"),
        "updated_at": item.get("updated_at"),
        "created_at": item.get("created_at"),
        "archived": bool(item.get("archived")),
        "fork": bool(item.get("fork")),
        "mirror": bool(item.get("mirror_url")),
        "language": item.get("language"),
        "license": license_info.get("spdx_id") if isinstance(license_info, dict) else None,
        "homepage": homepage if homepage.startswith("http") else "",
    }


def shanghai_date_from_iso(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return parsed.astimezone(lib.SHANGHAI).date().isoformat()


def fetch_history(client: GitHub, full_name: str) -> list[dict]:
    weeks: list[dict] = []
    today = datetime.now(timezone.utc).date()
    for page in range(1, 4):
        url = f"https://api.github.com/repos/{full_name}/stargazers/history?per_page=100&page={page}"
        try:
            payload = client.get_json(url)
        except RuntimeError as error:
            client.warnings.append(f"{full_name} 的 Star 历史不可用：{error}")
            return weeks
        if not isinstance(payload, list) or not payload:
            break
        weeks.extend(payload)
        week_stamps = [int(item["week"]) for item in payload if isinstance(item.get("week"), int)]
        if not week_stamps:
            break
        oldest_day = datetime.fromtimestamp(min(week_stamps), timezone.utc).date()
        if oldest_day <= today - timedelta(days=32) or len(payload) < 30:
            break
    return weeks


def fetch_readme(client: GitHub, full_name: str) -> str:
    url = f"https://api.github.com/repos/{full_name}/readme"
    try:
        _status, _headers, body = client.request(url, accept="application/vnd.github.raw")
    except RuntimeError:
        return ""
    return body.decode("utf-8", "replace")[:20000]


def fetch_release_asset(client: GitHub, full_name: str) -> str | None:
    url = f"https://api.github.com/repos/{full_name}/releases/latest"
    try:
        payload = client.get_json(url)
    except RuntimeError:
        return None
    if not isinstance(payload, dict):
        return None
    return lib.choose_release_asset(payload.get("assets") or [])


def url_is_live(url: str) -> bool:
    class HeadRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return urllib.request.Request(newurl, method="HEAD", headers={"User-Agent": USER_AGENT})

    opener = urllib.request.build_opener(HeadRedirect)
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(request, timeout=25) as response:
            return 200 <= response.status < 400
    except urllib.error.HTTPError as error:
        return error.code in {200, 206}
    except urllib.error.URLError:
        return False


def resolve_download(client: GitHub, repo: dict) -> dict:
    release_url = fetch_release_asset(client, repo["full_name"])
    archive_url = lib.archive_zip_url(repo["full_name"], repo["default_branch"])
    if release_url and url_is_live(release_url):
        return {
            "download_url": release_url,
            "download_available": True,
            "download_kind": "release_asset",
            "download_note": "已核验的 GitHub Release 资源。",
        }
    if url_is_live(archive_url):
        return {
            "download_url": archive_url,
            "download_available": True,
            "download_kind": "github_archive",
            "download_note": f"已核验的 GitHub 源码归档（{repo['default_branch']} 分支 zip）。",
        }
    return {
        "download_url": None,
        "download_available": False,
        "download_kind": None,
        "download_note": "本次未能核验 Release 资源或源码归档，页面只保留已核验的仓库来源和克隆命令。",
    }


def overrides_map() -> dict:
    raw = load_json(DATA / "category-overrides.json", {})
    if not isinstance(raw, dict):
        raise SystemExit("data/category-overrides.json 必须是对象")
    for repo_id, categories in raw.items():
        if not isinstance(categories, list) or any(category not in lib.CATEGORIES for category in categories):
            raise SystemExit(f"分类覆盖无效：{repo_id}")
    return {lib.skill_id(key): value for key, value in raw.items()}


def render_existing() -> int:
    payload = load_json(DATA / "skills.json", {})
    report = load_json(DATA / "daily-report.json", {})
    history = load_json(DATA / "report-history.json", [])
    if not payload.get("skills") or not report:
        print("没有可渲染的数据。请先不带参数运行一次。", file=sys.stderr)
        return 1
    errors = lib.validate_dataset(payload) + lib.validate_report(report, payload["skills"])
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "latest-update.md").write_text(lib.render_latest_update(report), encoding="utf-8")
    (ROOT / "CHANGELOG.md").write_text(lib.render_changelog(history or [report]), encoding="utf-8")
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(lib.render_page(payload), encoding="utf-8")
    print(f"已根据现有数据重绘页面，共 {len(payload['skills'])} 个技能。")
    return 0


def main() -> int:
    if "--render-only" in sys.argv:
        return render_existing()
    token = github_token()
    if not token:
        print("缺少 GitHub token。请设置 GITHUB_TOKEN，或在本机登录 gh。", file=sys.stderr)
        return 1
    client = GitHub(token)
    now = datetime.now(timezone.utc)
    today = lib.run_date(now)
    generated_at = lib.shanghai_now(now).isoformat(timespec="seconds")

    previous_payload = load_json(DATA / "skills.json", {})
    previous_skills = {
        lib.skill_id(skill["id"]): skill for skill in previous_payload.get("skills") or []
    }
    snapshots = load_json(DATA / "star-snapshots.json", {}).get("repos") or {}
    history = load_json(DATA / "report-history.json", [])
    category_overrides = overrides_map()

    discovered: dict[str, dict] = {}
    for query in SEARCH_QUERIES:
        print(f"搜索：{query}")
        for item in client.search_repos(query, pages=3, per_page=50, sort="stars"):
            repo = repo_from_api(item)
            discovered[lib.skill_id(repo["full_name"])] = repo
    growth_candidates: dict[str, dict] = {}
    for query in GROWTH_QUERIES:
        print(f"搜索增长候选：{query}")
        for item in client.search_repos(query, pages=1, per_page=30, sort="stars"):
            repo = repo_from_api(item)
            growth_candidates.setdefault(lib.skill_id(repo["full_name"]), repo)
    for full_name in SEEDS:
        sid = lib.skill_id(full_name)
        if sid in discovered or sid in growth_candidates:
            continue
        try:
            item = client.get_json(f"https://api.github.com/repos/{full_name}")
        except RuntimeError as error:
            client.warnings.append(f"种子仓库 {full_name} 读取失败：{error}")
            continue
        if isinstance(item, dict) and item.get("full_name"):
            repo = repo_from_api(item)
            if repo["stars"] >= lib.STAR_THRESHOLD:
                discovered[sid] = repo
            else:
                growth_candidates[sid] = repo

    considered: dict[str, dict] = {}
    rejected = []
    for sid, repo in {**growth_candidates, **discovered}.items():
        ok, reason = lib.relevance_reason(repo)
        if not ok:
            rejected.append({"id": sid, "reason": reason, "stars": repo["stars"]})
            continue
        considered[sid] = repo

    star_qualified = {sid: repo for sid, repo in considered.items() if repo["stars"] >= lib.STAR_THRESHOLD}
    need_growth = sorted(
        ((sid, repo) for sid, repo in considered.items() if repo["stars"] < lib.STAR_THRESHOLD),
        key=lambda item: item[1]["stars"],
        reverse=True,
    )[:MAX_GROWTH_CHECKS]

    growth_by_id: dict[str, dict] = {}
    qualified_ids = set(star_qualified)
    print(f"相关候选 {len(considered)}，Star 达标 {len(star_qualified)}，待核验增长 {len(need_growth)}")
    for sid, repo in need_growth:
        weeks = fetch_history(client, repo["full_name"])
        growth = lib.summarize_star_history(weeks, datetime.now(timezone.utc).date())
        if not growth.get("available"):
            growth = lib.summarize_snapshots(
                (snapshots.get(sid) or {}).get("points") or [],
                date.fromisoformat(today),
                repo["stars"],
            )
        rule_name = None
        ok, rule = lib.qualifies(repo["stars"], growth)
        if ok and rule == "growth":
            qualified_ids.add(sid)
            rule_name = "growth"
        growth["qualified_by_growth"] = rule_name == "growth"
        growth_by_id[sid] = growth
        time.sleep(0.05)

    for sid in previous_skills:
        qualified_ids.add(sid)

    final_skills = []
    removed = []
    updated_items = []
    print(f"刷新 {len(qualified_ids)} 个仓库的最新数据")
    for index, sid in enumerate(sorted(qualified_ids)):
        previous = previous_skills.get(sid)
        source_repo = star_qualified.get(sid) or considered.get(sid)
        try:
            item = client.get_json(f"https://api.github.com/repos/{sid}")
            if not isinstance(item, dict) or not item.get("full_name"):
                raise RuntimeError("空响应")
            repo = repo_from_api(item)
        except RuntimeError as error:
            if previous:
                client.warnings.append(f"{sid} 刷新失败，沿用上次记录：{error}")
                final_skills.append(previous)
                continue
            client.warnings.append(f"{sid} 刷新失败，已跳过：{error}")
            continue

        relevant, relevance = lib.relevance_reason(repo)
        if sid not in growth_by_id and repo["stars"] < lib.STAR_THRESHOLD:
            weeks = fetch_history(client, repo["full_name"])
            growth_by_id[sid] = lib.summarize_star_history(weeks, datetime.now(timezone.utc).date())
        growth = growth_by_id.get(sid)
        if growth is None or (repo["stars"] >= lib.STAR_THRESHOLD and not growth.get("available")):
            weeks = fetch_history(client, repo["full_name"])
            growth = lib.summarize_star_history(weeks, datetime.now(timezone.utc).date())
        if not growth.get("available"):
            growth = lib.summarize_snapshots(
                (snapshots.get(sid) or {}).get("points") or [],
                date.fromisoformat(today),
                repo["stars"],
            )
        ok, rule = lib.qualifies(repo["stars"], growth)
        if not relevant or not ok:
            if previous:
                removed.append(
                    {
                        "id": sid,
                        "name": previous.get("name") or sid,
                        "reason": relevance if not relevant else "不再满足 Star 或快速增长门槛",
                    }
                )
            continue
        growth["qualified_by_growth"] = rule == "growth"
        growth_by_id[sid] = growth

        fingerprint = lib.category_fingerprint(repo["name"], repo["description"], repo["topics"])
        readme = ""
        if sid in category_overrides:
            categories = category_overrides[sid]
        elif previous and previous.get("category_fingerprint") == fingerprint and previous.get("categories"):
            categories = previous["categories"]
        else:
            readme = fetch_readme(client, repo["full_name"])
            categories = lib.categorize(
                repo["name"],
                repo["description"],
                repo["topics"],
                lib.readme_category_excerpt(readme),
            )
        if not categories:
            if previous:
                removed.append({"id": sid, "name": previous.get("name") or sid, "reason": "不再对应软件交付分类"})
            continue
        if not readme and (not previous or previous.get("category_fingerprint") != fingerprint):
            readme = fetch_readme(client, repo["full_name"])
        documented = previous.get("documented_install") if previous and previous.get("category_fingerprint") == fingerprint else None
        if readme:
            documented = lib.extract_documented_install(readme)
        download = resolve_download(client, repo)
        notable = lib.notable_text(repo, growth, rule)
        record = {
            "id": sid,
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo["description"],
            "categories": categories,
            "category_fingerprint": fingerprint,
            "source_url": repo["html_url"],
            "source_label": "GitHub 仓库",
            "download_url": download["download_url"],
            "download_available": download["download_available"],
            "download_kind": download["download_kind"],
            "download_note": download["download_note"],
            "install_command": lib.install_command(repo["clone_url"]),
            "documented_install": documented,
            "stars": repo["stars"],
            "forks": repo["forks"],
            "growth": {
                "stars_7d": growth.get("stars_7d"),
                "stars_30d": growth.get("stars_30d"),
                "source": growth.get("source"),
                "history_through": growth.get("history_through"),
                "window_end": growth.get("window_end"),
                "partial": bool(growth.get("partial")),
                "available": bool(growth.get("available")),
                "qualified_by_growth": rule == "growth",
            },
            "qualification": {"rule": rule, "reason_zh": notable},
            "notable_zh": notable,
            "pushed_at": repo["pushed_at"],
            "pushed_date": shanghai_date_from_iso(repo["pushed_at"], today),
            "created_at": repo["created_at"],
            "first_seen": (previous or {}).get("first_seen") or today,
            "last_seen": today,
            "license": repo["license"],
            "topics": repo["topics"],
            "default_branch": repo["default_branch"],
            "archived": repo["archived"],
            "language": repo["language"],
            "homepage": repo["homepage"],
        }
        if previous and previous.get("first_seen") != today:
            changed = any(
                previous.get(field) != record.get(field)
                for field in ("stars", "description", "categories", "download_url", "pushed_at")
            )
            if changed:
                updated_items.append(
                    {
                        "id": sid,
                        "name": record["name"],
                        "stars_before": previous.get("stars"),
                        "stars_after": record["stars"],
                        "source": record["source_url"],
                        "download": record["download_url"],
                    }
                )
        snapshots[sid] = lib.snapshot_record(snapshots.get(sid), sid, today, repo["stars"])
        final_skills.append(record)
        if index % 10 == 0:
            print(f"  已处理 {index + 1}/{len(qualified_ids)} {sid}")
        time.sleep(0.05)

    final_skills.sort(key=lambda skill: (-skill["stars"], skill["id"]))
    if not final_skills:
        print("没有收录任何技能，拒绝覆盖已有数据。", file=sys.stderr)
        for warning in client.warnings:
            print(warning, file=sys.stderr)
        return 1

    new_items = []
    for skill in final_skills:
        if skill.get("first_seen") != today:
            continue
        new_items.append(
            {
                "id": skill["id"],
                "name": skill["name"],
                "categories": skill["categories"],
                "stars": skill["stars"],
                "source": skill["source_url"],
                "download": skill["download_url"],
                "link": skill["source_url"],
                "install_command": skill["install_command"],
                "reason": skill["notable_zh"],
            }
        )
    new_items.sort(key=lambda item: item["stars"], reverse=True)
    report = {
        "schema_version": lib.SCHEMA_VERSION,
        "timezone": "Asia/Shanghai",
        "run_at": generated_at,
        "run_date": today,
        "total_skills": len(final_skills),
        "new_today": len(new_items),
        "updated_today": len(updated_items),
        "removed_today": len(removed),
        "new_items": new_items,
        "updated_items": updated_items,
        "removed_items": removed,
        "warnings": client.warnings,
        "criteria": lib.criteria_document(),
        "discovery": {
            "search_queries": SEARCH_QUERIES,
            "growth_queries": GROWTH_QUERIES,
            "considered": len(considered),
            "rejected": len(rejected),
            "growth_checks": len(need_growth),
        },
    }
    payload = {
        "schema_version": lib.SCHEMA_VERSION,
        "timezone": "Asia/Shanghai",
        "generated_at": generated_at,
        "run_date": today,
        "updated_today": len(updated_items),
        "storage": "仓库内 JSON / Markdown 文件，无数据库",
        "criteria": lib.criteria_document(),
        "skills": final_skills,
    }
    errors = lib.validate_dataset(payload) + lib.validate_report(report, final_skills)
    if errors:
        print("生成结果未通过校验，未写入文件：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    history = [item for item in history if item.get("run_date") != today]
    history.insert(0, {key: report[key] for key in (
        "run_at", "run_date", "total_skills", "new_today", "updated_today", "removed_today", "new_items"
    )})
    history = history[:90]
    snapshots = lib.prune_snapshots(snapshots, today)

    dump_json(DATA / "skills.json", payload)
    dump_json(DATA / "daily-report.json", report)
    dump_json(DATA / "report-history.json", history)
    dump_json(DATA / "star-snapshots.json", {"schema_version": 1, "timezone": "Asia/Shanghai", "repos": snapshots})
    if not (DATA / "category-overrides.json").exists():
        dump_json(DATA / "category-overrides.json", {})
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "latest-update.md").write_text(lib.render_latest_update(report), encoding="utf-8")
    (ROOT / "CHANGELOG.md").write_text(lib.render_changelog(history), encoding="utf-8")
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(lib.render_page(payload), encoding="utf-8")
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    dump_json(SITE / "data" / "skills.json", payload)
    dump_json(SITE / "data" / "daily-report.json", report)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    print(
        f"完成：收录 {len(final_skills)}，新增 {len(new_items)}，更新 {len(updated_items)}，移出 {len(removed)}。"
    )
    print("增长收录：", ", ".join(skill["id"] for skill in final_skills if skill["qualification"]["rule"] == "growth") or "无")
    if client.warnings:
        print(f"警告 {len(client.warnings)} 条，已写入日报。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
