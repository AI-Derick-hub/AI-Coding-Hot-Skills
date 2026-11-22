"""Pure rules for the AI coding skills catalog.

The daily job stores everything in JSON and Markdown files in this repository.
This module does not talk to the network and does not use a database.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")

SCHEMA_VERSION = 1
STAR_THRESHOLD = 2000
GROWTH_7D_MIN = 100
GROWTH_7D_RATIO = 0.10
GROWTH_30D_MIN = 250
GROWTH_30D_RATIO = 0.25
HISTORY_LAG_DAYS = 3

CATEGORIES = ["需求", "开发", "测试", "绘制设计图", "生成 PPT"]

OFFICIAL_OWNERS = {"anthropics", "openai", "github", "microsoft", "vercel-labs", "google"}

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "需求": [
        r"planning",
        r"product management",
        r"product-manager",
        r"\bprd\b",
        r"user stor(?:y|ies)",
        r"brainstorm",
        r"需求",
        r"产品经理",
        r"路线图",
        r"roadmap",
    ],
    "开发": [
        r"coding",
        r"developer",
        r"programming",
        r"refactor",
        r"full[- ]stack",
        r"software development",
        r"\bengineering\b",
        r"\bdevelopment\b",
        r"编程",
        r"开发",
        r"工程师",
        r"pair programmer",
        r"frontend",
        r"ui/ux",
        r"界面",
        r"landing page",
        r"落地页",
    ],
    "测试": [
        r"\btesting\b",
        r"test-driven",
        r"\btests\b",
        r"\btdd\b",
        r"\bqa\b",
        r"code review",
        r"threat model",
        r"\btriage\b",
        r"测试",
        r"质量保障",
    ],
    "绘制设计图": [
        r"diagram",
        r"flowchart",
        r"mermaid",
        r"draw\.?io",
        r"wireframe",
        r"architecture diagram",
        r"信息图",
        r"infographic",
        r"架构图",
        r"设计图",
        r"流程图",
        r"\buml\b",
        r"c4-model",
        r"c4 model",
    ],
    "生成 PPT": [
        r"pptx",
        r"powerpoint",
        r"\bppt\b",
        r"slide deck",
        r"\bslides\b",
        r"幻灯片",
        r"演示文稿",
    ],
}

TOPIC_CATEGORY = {
    "planning": "需求",
    "product-management": "需求",
    "brainstorming": "需求",
    "tdd": "测试",
    "testing": "测试",
    "code-review": "测试",
    "diagrams": "绘制设计图",
    "diagram": "绘制设计图",
    "mermaid": "绘制设计图",
    "drawio": "绘制设计图",
    "flowchart": "绘制设计图",
    "architecture-diagram": "绘制设计图",
    "infographic": "绘制设计图",
    "uml": "绘制设计图",
    "c4-model": "绘制设计图",
    "pptx": "生成 PPT",
    "slides": "生成 PPT",
    "powerpoint": "生成 PPT",
    "ppt-skill": "生成 PPT",
    "ai-ppt": "生成 PPT",
    "coding": "开发",
    "coding-agent": "开发",
    "coding-agents": "开发",
    "ai-coding": "开发",
    "developer-tools": "开发",
    "sdlc": "开发",
    "frontend": "开发",
}

SKILL_TOPICS = {
    "agent-skills",
    "claude-skills",
    "claude-code-skills",
    "cursor-skills",
    "codex-skills",
    "skill-md",
    "ai-skills",
}

HOST_PATTERN = re.compile(
    r"claude|cursor|codex|copilot|windsurf|opencode|gemini[- ]cli|"
    r"coding agents?|ai agents?|agentic|agent skills?|\.agents\b|智能体|编码代理",
    re.I,
)

OFFENSIVE_PATTERN = re.compile(
    r"red[- ]team|offensive security|pentest|penetration testing|\bexploit\b|"
    r"\bmalware\b|\bphishing\b|\bransomware\b|漏洞利用",
    re.I,
)

# Name-level or lead-in signals that the repo is not a software-delivery skill.
NON_SDLC_PATTERN = re.compile(
    r"trading|equity investor|\bstocks?\b|期权|金融|finance|financial|"
    r"\bvideo\b|b-roll|short[- ]drama|短剧|漫剧|stickman|motion graphics|\bffmpeg\b|"
    r"xiaohongshu|小红书|公众号|instagram|linkedin|"
        r"academic research|学术|论文|empirical research|\bads\b|"
    r"\bmedical\b|临床|医疗|\bnsfw\b|"
    r"\bctf\b|reverse engineering|\bpwn\b|"
    r"humanizer|ai-generated writing|防御性写作|"
    r"distill how anyone|思维方式|心智模型|"
    r"\bobsidian\b|numerolog|占卜|八字|"
    r"supply-chain|automotive|\bbooking\b|\bblender\b|"
    r"turns books into|book-to-skill|marketing|copywriting|\bseo\b|"
    r"ai scientist|bioinformatics|drug discovery|job search|网文|fanfic",
    re.I,
)
SDLC_PATTERN = re.compile(
    r"coding|developer|engineer|software|programming|refactor|frontend|backend|"
    r"full[- ]stack|code review|\btdd\b|\btesting\b|\bqa\b|diagram|architecture|"
    r"pptx|powerpoint|\bslides?\b|planning|\bprd\b|\bsdlc\b|debug|"
    r"编程|开发|测试|架构图|需求|设计图|幻灯片|"
    r"claude code|cursor|codex|copilot|swift|react|typescript|python|"
    r"ui/ux|ui-ux|product management|product manager|"
    r"agent skills|skills catalog|skills framework|"
    r"specification and documentation for agent skills|macos",
    re.I,
)
CODING_TOPICS = {
    "coding",
    "coding-agent",
    "coding-agents",
    "ai-coding",
    "developer-tools",
    "sdlc",
    "tdd",
    "code-review",
    "diagrams",
    "diagram",
    "pptx",
    "claude-skills",
    "cursor-skills",
    "codex-skills",
    "claude-code-skills",
}

CONVERTER_PATTERN = re.compile(r"^(convert|scrape|a scraper)\b", re.I)
HARD_BLOCK_PATTERN = re.compile(
    r"小说|网文|novelist|fanfic|高考|考研|中医|紫微|八字|占卜|"
    r"\bresume\b|job application|求职|paper writing|论文写作|"
    r"reverse engineering|逆向|"
        r"persona[- ]distill|人格蒸馏|de-ai writing|去 ?ai ?味|"
        r"distill high-value|高价值内容蒸馏|logo[- ]design|"
    r"social media research",
    re.I,
)
PRODUCT_NOT_SKILL_PATTERN = re.compile(
    r"skills tool|scanner for ai agent skills|evaluating ai agent skills|"
    r"desktop app to manage|agent skills builder",
    re.I,
)

INSTALL_LINE = re.compile(
    r"^(?:npx skills add \S+|git clone https://github\.com/\S+|"
    r"clawhub install \S+|/plugin marketplace add \S+|/plugin install \S+)$"
)

FENCE_RE = re.compile(r"```(?:bash|sh|shell|text|console)?\n(.*?)```", re.I | re.S)


def shanghai_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(SHANGHAI)


def run_date(now: datetime | None = None) -> str:
    return shanghai_now(now).date().isoformat()


def skill_id(full_name: str) -> str:
    return full_name.strip().lower()


def criteria_document() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "storage": "仓库内的 JSON 与 Markdown 文件，不使用数据库或外部数据服务",
        "unit": "一个公开 GitHub 仓库（技能包、技能合集或官方技能目录）",
        "star_threshold": STAR_THRESHOLD,
        "growth": {
            "source": "GET /repos/{owner}/{repo}/stargazers/history 的按日计数；接口不可用时改用本仓库 data/star-snapshots.json 的每日快照",
            "stars_7d_min": GROWTH_7D_MIN,
            "stars_7d_ratio_min": GROWTH_7D_RATIO,
            "stars_30d_min": GROWTH_30D_MIN,
            "stars_30d_ratio_min": GROWTH_30D_RATIO,
            "window": "以运行日的 UTC 日历日为结束日（含当日；若 GitHub 周统计尚未写入当日，则已入账天数作为下限）",
            "logic": "Star 低于门槛时，近 7 日新增达到绝对值和占比，或近 30 日新增达到绝对值和占比，二者满足其一即可",
        },
        "categories": CATEGORIES,
    }


def category_fingerprint(name: str, description: str, topics: list[str]) -> str:
    payload = {
        "name": name or "",
        "description": description or "",
        "topics": sorted(topics or []),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _search_text(name: str, description: str, topics: list[str], readme: str) -> str:
    topic_text = " ".join(topics or [])
    return "\n".join([name or "", description or "", topic_text, readme or ""])


def categorize(name: str, description: str, topics: list[str], readme: str = "") -> list[str]:
    text = _search_text(name, description, topics, readme)
    found: list[str] = []
    for category in CATEGORIES:
        if any(re.search(pattern, text, re.I) for pattern in CATEGORY_PATTERNS[category]):
            found.append(category)
    for topic in topics or []:
        category = TOPIC_CATEGORY.get(topic.lower())
        if category and category not in found:
            found.append(category)
    short = f"{name or ''}\n{description or ''}"
    if "开发" not in found and re.search(r"skill", short, re.I) and re.search(
        r"curated|collection of|catalog of|awesome|技能库|技能包", short, re.I
    ):
        found.append("开发")
    if not found and (
        _is_general_coding_pack(name, description)
        or re.search(r"agent skills|skills catalog|skills framework|技能包|技能库", short, re.I)
    ):
        found.append("开发")
    return [category for category in CATEGORIES if category in found]


def _is_general_coding_pack(name: str, description: str) -> bool:
    if not re.search(r"skill", name or "", re.I):
        return False
    return bool(
        re.search(
            r"engineer|coding|developer|编程|开发|软件",
            f"{name or ''}\n{description or ''}",
            re.I,
        )
    )


def readme_category_excerpt(readme: str) -> str:
    """Keep headings and skill paths so prose like "test the install" does not recategorize."""
    if not readme:
        return ""
    kept = []
    for line in readme.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or "SKILL.md" in stripped or "/skills/" in stripped or stripped.startswith("skills/"):
            kept.append(stripped)
    return "\n".join(kept)[:8000]


def _outside_software_delivery(name: str, description: str) -> bool:
    """Block off-scope repos without dropping a design pack that also mentions one social format."""
    if HARD_BLOCK_PATTERN.search(f"{name or ''}\n{description or ''}"):
        return True
    if NON_SDLC_PATTERN.search(name or ""):
        return True
    head = (description or "")[:140]
    if not NON_SDLC_PATTERN.search(head):
        return False
    return not bool(re.search(r"pptx|powerpoint|\bdiagram\b|架构图|编程|软件开发", description or "", re.I))


def _skill_is_the_product(name: str, description: str) -> bool:
    if re.search(r"boilerplate|starter template|command-line tool|one command-line", description or "", re.I):
        return False
    if re.search(r"\bplatform\b", description or "", re.I) and re.search(
        r"marketplace|package manager|harness", description or "", re.I
    ):
        return False
    if re.search(r"skill", name or "", re.I):
        return True
    if re.search(r"\bincludes\b.{0,80}\bskills?\b", description or "", re.I):
        return False
    return bool(re.search(r"\bskills?\b|SKILL\.md", description or "", re.I))


def _software_delivery_focus(name: str, description: str, topics: list[str]) -> bool:
    blob = f"{name or ''}\n{description or ''}"
    if SDLC_PATTERN.search(blob):
        return True
    topic_set = {topic.lower() for topic in topics or []}
    if topic_set & CODING_TOPICS:
        return True
    if re.search(r"awesome", name or "", re.I) and re.search(r"skill", name or "", re.I):
        return bool(re.search(r"claude|cursor|codex|copilot|agent", blob, re.I))
    return False


def relevance_reason(repo: dict) -> tuple[bool, str]:
    """Decide whether a repository is a reusable coding-agent skill pack."""
    if repo.get("fork") or repo.get("mirror"):
        return False, "fork 或镜像，不重复收录"
    name = repo.get("name") or ""
    description = repo.get("description") or ""
    topics = [str(topic).lower() for topic in repo.get("topics") or []]
    blob = f"{name}\n{description}\n{' '.join(topics)}"
    if OFFENSIVE_PATTERN.search(blob):
        return False, "进攻性安全或漏洞利用技能，不纳入本目录"
    if _outside_software_delivery(name, description):
        return False, "主题不是软件交付技能（需求、开发、测试、设计图或 PPT）"
    if CONVERTER_PATTERN.search(description.strip()) or PRODUCT_NOT_SKILL_PATTERN.search(description):
        return False, "仓库是工具、扫描器或构建器，不是可安装的技能包"
    if not _skill_is_the_product(name, description):
        skill_topic = any(topic in SKILL_TOPICS for topic in topics)
        diagram_or_ppt = bool(re.search(r"pptx|powerpoint|\bdiagram\b", description, re.I))
        if not (skill_topic and diagram_or_ppt):
            return False, "技能不是这个仓库的主体，或简介没有说明它是 Skill"
    elif not (
        re.search(r"skill", name, re.I)
        or re.search(r"\bskills?\b|SKILL\.md", description, re.I)
        or any(topic in SKILL_TOPICS for topic in topics)
    ):
        return False, "名称、简介和 topic 都没有表明这是 Skill 仓库"
    if not HOST_PATTERN.search(blob) and not any(topic in SKILL_TOPICS for topic in topics):
        return False, "未指向 Claude、Cursor、Codex、Copilot 或其他编码代理"
    if not _software_delivery_focus(name, description, topics):
        return False, "没有落到需求、开发、测试、设计图或 PPT"
    return True, "名称或简介表明这是编码代理可复用的 Skill / 技能合集"


def qualifies(stars: int, growth: dict | None) -> tuple[bool, str]:
    if stars >= STAR_THRESHOLD:
        return True, "stars"
    if not growth or not growth.get("available"):
        return False, "below-threshold-growth-unverified"
    if growth.get("partial") and not _growth_lower_bound_passes(stars, growth):
        return False, "below-threshold-growth-partial"
    if _growth_rule(stars, growth):
        return True, "growth"
    return False, "below-threshold"


def _growth_rule(stars: int, growth: dict) -> str | None:
    stars_7d = growth.get("stars_7d")
    stars_30d = growth.get("stars_30d")
    if stars <= 0:
        return None
    if isinstance(stars_7d, int) and stars_7d >= GROWTH_7D_MIN and stars_7d / stars >= GROWTH_7D_RATIO:
        return "7d"
    if isinstance(stars_30d, int) and stars_30d >= GROWTH_30D_MIN and stars_30d / stars >= GROWTH_30D_RATIO:
        return "30d"
    return None


def _growth_lower_bound_passes(stars: int, growth: dict) -> bool:
    return _growth_rule(stars, growth) is not None


def summarize_star_history(weeks: list[dict], today: date) -> dict:
    """Sum daily star counts from GitHub's weekly stargazers/history payload."""
    parsed: list[tuple[date, int]] = []
    for week in weeks or []:
        start_raw = week.get("week")
        days = week.get("days") or []
        if not isinstance(start_raw, (int, float)) or not isinstance(days, list):
            continue
        start = datetime.fromtimestamp(int(start_raw), timezone.utc).date()
        for offset, count in enumerate(days[:7]):
            if isinstance(count, int) and count >= 0:
                parsed.append((start + timedelta(days=offset), count))
    if not parsed:
        return {
            "available": False,
            "source": "github_stargazers_history",
            "reason": "empty-history",
        }
    parsed.sort(key=lambda item: item[0])
    history_through = parsed[-1][0]
    start_7 = today - timedelta(days=6)
    start_30 = today - timedelta(days=29)
    stars_7d = sum(count for day, count in parsed if start_7 <= day <= today)
    stars_30d = sum(count for day, count in parsed if start_30 <= day <= today)
    partial = history_through < today
    lag_days = (today - history_through).days
    available = lag_days <= HISTORY_LAG_DAYS
    return {
        "available": available,
        "partial": partial,
        "source": "github_stargazers_history",
        "stars_7d": stars_7d,
        "stars_30d": stars_30d,
        "history_through": history_through.isoformat(),
        "window_start_7d": start_7.isoformat(),
        "window_start_30d": start_30.isoformat(),
        "window_end": today.isoformat(),
        "lag_days": lag_days,
        "qualified_by_growth": False,
    }


def summarize_snapshots(points: list[dict], today: date, stars: int) -> dict:
    """Fallback growth from daily star snapshots stored in the repository."""
    cleaned: list[tuple[date, int]] = []
    for point in points or []:
        try:
            cleaned.append((date.fromisoformat(point["date"]), int(point["stars"])))
        except (KeyError, TypeError, ValueError):
            continue
    cleaned.sort(key=lambda item: item[0])
    if not cleaned:
        return {"available": False, "source": "repo_snapshots", "reason": "no-snapshots"}

    def delta(days: int, minimum_age: int, maximum_age: int) -> int | None:
        target = today - timedelta(days=days)
        prior = [item for item in cleaned if item[0] <= target]
        if not prior:
            return None
        chosen_day, chosen_stars = prior[-1]
        age = (today - chosen_day).days
        if age < minimum_age or age > maximum_age:
            return None
        return max(0, stars - chosen_stars)

    stars_7d = delta(7, 6, 10)
    stars_30d = delta(30, 27, 36)
    available = stars_7d is not None or stars_30d is not None
    return {
        "available": available,
        "partial": False,
        "source": "repo_snapshots",
        "stars_7d": stars_7d,
        "stars_30d": stars_30d,
        "history_through": cleaned[-1][0].isoformat(),
        "window_end": today.isoformat(),
        "qualified_by_growth": False,
        "reason": None if available else "snapshots-not-old-enough",
    }


def growth_phrase(growth: dict | None) -> str:
    if not growth or growth.get("stars_7d") is None and growth.get("stars_30d") is None:
        return "增长数字尚不可用"
    prefix = "至少" if growth.get("partial") else ""
    parts = []
    if isinstance(growth.get("stars_7d"), int):
        parts.append(f"近 7 日{prefix}新增 {growth['stars_7d']:,} Star")
    if isinstance(growth.get("stars_30d"), int):
        parts.append(f"近 30 日{prefix}新增 {growth['stars_30d']:,} Star")
    through = growth.get("history_through")
    suffix = f"（统计截至 {through}）" if through else ""
    return "，".join(parts) + suffix


def notable_text(repo: dict, growth: dict | None, rule: str) -> str:
    stars = int(repo.get("stars") or 0)
    owner = (repo.get("full_name") or "/").split("/")[0].lower()
    if rule == "stars":
        text = f"公开 Star {stars:,}，达到不少于 {STAR_THRESHOLD:,} 的收录门槛。"
        if growth and growth.get("available"):
            text += growth_phrase(growth) + "。"
    else:
        text = (
            f"当前 Star {stars:,}，低于 {STAR_THRESHOLD:,}，但{growth_phrase(growth)}，"
            "符合快速增长标准。"
        )
    if owner in OFFICIAL_OWNERS:
        text += f" {owner} 官方仓库。"
    description = (repo.get("description") or "").strip()
    if description:
        short = description if len(description) <= 90 else description[:89].rstrip() + "…"
        text += f" 简介：{short}"
    return text


def qualification_reason(repo: dict, growth: dict | None, rule: str) -> str:
    return notable_text(repo, growth, rule)


def extract_documented_install(readme: str) -> str | None:
    if not readme:
        return None
    for fence in FENCE_RE.findall(readme):
        for raw_line in fence.splitlines():
            line = raw_line.strip()
            if line.startswith("$ "):
                line = line[2:].strip()
            if INSTALL_LINE.match(line):
                return line
    return None


def archive_zip_url(full_name: str, branch: str) -> str:
    safe_branch = branch or "main"
    return f"https://github.com/{full_name}/archive/refs/heads/{safe_branch}.zip"


def install_command(clone_url: str) -> str:
    return f"git clone {clone_url}"


def choose_release_asset(assets: list[dict]) -> str | None:
    urls = []
    for asset in assets or []:
        url = asset.get("browser_download_url") or ""
        name = (asset.get("name") or "").lower()
        if url.startswith("https://") and (name.endswith(".zip") or name.endswith(".tar.gz")):
            urls.append((name, url))
    if not urls:
        return None
    zips = [url for name, url in urls if name.endswith(".zip")]
    return zips[0] if zips else urls[0][1]


def snapshot_record(existing: dict | None, full_id: str, today: str, stars: int) -> dict:
    record = existing or {"last_seen": today, "points": []}
    points = [point for point in record.get("points") or [] if point.get("date") != today]
    points.append({"date": today, "stars": stars})
    points.sort(key=lambda point: point["date"])
    cutoff = date.fromisoformat(today) - timedelta(days=45)
    points = [point for point in points if date.fromisoformat(point["date"]) >= cutoff]
    return {"last_seen": today, "points": points}


def prune_snapshots(snapshots: dict, today: str) -> dict:
    cutoff = date.fromisoformat(today) - timedelta(days=45)
    kept = {}
    for repo_id, record in snapshots.items():
        try:
            seen = date.fromisoformat(record.get("last_seen"))
        except (TypeError, ValueError):
            continue
        if seen >= cutoff:
            kept[repo_id] = record
    return kept


def render_page(payload: dict) -> str:
    skills = payload["skills"]
    generated = payload["generated_at"]
    run_day = payload["run_date"]
    new_skills = [skill for skill in skills if skill.get("first_seen") == run_day]
    counts = {category: 0 for category in CATEGORIES}
    for skill in skills:
        for category in skill.get("categories") or []:
            if category in counts:
                counts[category] += 1
    ranked_new = sorted(new_skills, key=lambda item: item.get("stars") or 0, reverse=True)
    preview = ranked_new[:8]
    new_links = [
        f'<a href="#{html.escape(anchor_id(skill["id"]))}">{html.escape(skill["name"])}</a>'
        for skill in preview
    ]
    if not new_skills:
        new_block = "<p>今天没有新进入名录的 Skill。下面是已经收录的全部技能。</p>"
    elif len(new_skills) == len(skills):
        new_block = (
            f"<p>这是目前的全部收录，<strong>{len(new_skills)}</strong> 个都是今天新增。"
            "卡片上有「今日新增」标记。Star 最高的几个：</p>"
            f"<div class=\"new-links\">{''.join(new_links)}</div>"
        )
    else:
        more = ""
        if len(ranked_new) > len(preview):
            more = f"<p>其余 {len(ranked_new) - len(preview)} 个也带「今日新增」标记，可以用上面的范围筛选。</p>"
        new_block = (
            f"<p>今天新进入名录 <strong>{len(new_skills)}</strong> 个。点击名称可跳到卡片。</p>"
            f"<div class=\"new-links\">{''.join(new_links)}</div>{more}"
        )
    cards = "\n".join(render_card(skill, run_day) for skill in skills)
    category_buttons = [
        '<button type="button" class="chip" data-cat="" aria-pressed="true">全部 '
        f"<span>{len(skills)}</span></button>"
    ]
    for category in CATEGORIES:
        category_buttons.append(
            f'<button type="button" class="chip" data-cat="{html.escape(category)}" aria-pressed="false">'
            f"{html.escape(category)} <span>{counts[category]}</span></button>"
        )
    rules = payload["criteria"]["growth"]
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>热门 AI 编程 Skills</title>
  <meta name="description" content="可浏览、可搜索的热门 AI 编程技能目录。数据来自公开 GitHub 仓库，每日更新。">
  <meta name="theme-color" content="#1a1714">
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <a class="skip" href="#grid">跳到技能列表</a>
  <header class="masthead">
    <div class="wrap">
      <p class="eyebrow">AI Coding Hot Skills</p>
      <h1>热门 AI 编程 Skills</h1>
      <p class="lede">跟踪可复用的编码代理技能：Cursor、Claude Code、Codex，以及 SKILL.md 技能库和知名合集。这里不收录泛泛的模型新闻或通用 AI 工具站。</p>
      <dl class="stats">
        <div><dt>收录</dt><dd>{len(skills)}</dd></div>
        <div><dt>今日新增</dt><dd>{len(new_skills)}</dd></div>
        <div><dt>今日更新</dt><dd>{payload.get("updated_today", 0)}</dd></div>
        <div><dt>更新时间</dt><dd>{html.escape(generated.replace("T", " ")[:16])}</dd></div>
      </dl>
    </div>
  </header>
  <main class="wrap">
    <section class="panel" id="new-today">
      <h2>今日新增</h2>
      {new_block}
    </section>
    <section class="toolbar" aria-label="筛选">
      <label class="search">
        <span>搜索</span>
        <input id="q" type="search" placeholder="搜索名称、仓库或简介" autocomplete="off">
      </label>
      <div class="chips" role="group" aria-label="分类">{''.join(category_buttons)}</div>
      <div class="toolbar-row">
        <label>范围
          <select id="rule">
            <option value="all">全部</option>
            <option value="stars">不少于 {STAR_THRESHOLD:,} Star</option>
            <option value="growth">快速增长</option>
            <option value="new">今日新增</option>
          </select>
        </label>
        <label>排序
          <select id="sort">
            <option value="stars">Star 从高到低</option>
            <option value="updated">最近推送</option>
            <option value="new">今日新增优先</option>
            <option value="name">名称</option>
          </select>
        </label>
        <p id="result-count" class="result-count">{len(skills)} 个结果</p>
      </div>
    </section>
    <p id="empty" class="empty" hidden>没有符合筛选条件的 Skill。</p>
    <section class="grid" id="grid">
      {cards}
    </section>
    <section class="panel rules">
      <h2>收录规则</h2>
      <p>追踪单位是一个公开 GitHub 仓库。满足下面任一条件就会出现在本页：</p>
      <ol>
        <li>GitHub 显示的 Star 不少于 {STAR_THRESHOLD:,}。</li>
        <li>Star 仍低于 {STAR_THRESHOLD:,}，但增长很快：近 7 个 UTC 日历日新增至少 {rules["stars_7d_min"]} 且不少于当前 Star 的 {int(rules["stars_7d_ratio_min"] * 100)}%，或者近 30 日新增至少 {rules["stars_30d_min"]} 且不少于当前 Star 的 {int(rules["stars_30d_ratio_min"] * 100)}%。增长数字来自 GitHub 的按日 Star 历史，写不出来就不会靠猜测收录。</li>
      </ol>
      <p>分类可以多选：需求、开发、测试、绘制设计图、生成 PPT。数据文件在仓库的 <code>data/skills.json</code>，每日报告在 <code>data/daily-report.json</code>。本项目不使用数据库。</p>
    </section>
  </main>
  <footer class="wrap site-footer">
    <p>静态页面，由仓库里的 JSON 生成。机器可读报告：<a href="data/daily-report.json">data/daily-report.json</a>。技能数据：<a href="data/skills.json">data/skills.json</a>。</p>
  </footer>
  <script src="assets/site.js"></script>
</body>
</html>
"""


def anchor_id(skill_id_value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", skill_id_value.lower()).strip("-")
    return f"skill-{slug}"


def render_card(skill: dict, run_day: str) -> str:
    categories = skill.get("categories") or []
    chips = "".join(f"<li>{html.escape(category)}</li>" for category in categories)
    description = skill.get("description") or "仓库未填写简介。"
    growth = skill.get("growth") or {}
    growth_html = ""
    if isinstance(growth.get("stars_7d"), int):
        prefix = "至少 " if growth.get("partial") else ""
        growth_html = (
            f'<p class="growth">{prefix}近 7 日 +{growth["stars_7d"]:,} · '
            f'近 30 日 +{growth.get("stars_30d") or 0:,}'
            f'（截至 {html.escape(str(growth.get("history_through") or ""))}）</p>'
        )
    rule = (skill.get("qualification") or {}).get("rule") or ""
    rule_label = "快速增长" if rule == "growth" else f"Star ≥ {STAR_THRESHOLD:,}"
    new_badge = '<span class="badge new">今日新增</span>' if skill.get("first_seen") == run_day else ""
    archive_badge = '<span class="badge">已归档</span>' if skill.get("archived") else ""
    download_url = skill.get("download_url")
    if skill.get("download_available") and download_url:
        download_html = (
            f'<a class="btn" href="{html.escape(download_url)}">下载</a>'
        )
        download_note = f'<p class="meta-line">{html.escape(skill.get("download_note") or "")}</p>'
    else:
        download_html = '<span class="btn disabled">直接下载未核验</span>'
        download_note = (
            '<p class="meta-line warn">直接下载：未核验。'
            f'{html.escape(skill.get("download_note") or "没有可用的归档或发行包链接。")}</p>'
        )
    documented = skill.get("documented_install")
    documented_html = ""
    if documented:
        documented_html = (
            '<p class="install"><span>文档中的安装命令</span> '
            f"<code>{html.escape(documented)}</code></p>"
        )
    homepage = skill.get("homepage") or ""
    homepage_html = ""
    if homepage.startswith("http"):
        homepage_html = f'<a class="btn ghost" href="{html.escape(homepage)}">主页</a>'
    search_blob = " ".join(
        [
            skill.get("name") or "",
            skill.get("id") or "",
            skill.get("description") or "",
            " ".join(categories),
            skill.get("notable_zh") or "",
        ]
    ).lower()
    pushed = skill.get("pushed_date") or ""
    return f"""<article class="card" id="{html.escape(anchor_id(skill["id"]))}" data-cats="{html.escape(",".join(categories))}" data-stars="{int(skill.get("stars") or 0)}" data-pushed="{html.escape(pushed)}" data-new="{"1" if skill.get("first_seen") == run_day else "0"}" data-rule="{html.escape(rule)}" data-name="{html.escape(skill.get("name") or "")}" data-search="{html.escape(search_blob)}">
  <header class="card-head">
    <h2>{html.escape(skill.get("name") or skill.get("id") or "")}</h2>
    <p class="repo">{html.escape(skill.get("full_name") or "")}</p>
    <div class="badges">{new_badge}{archive_badge}<span class="badge quiet">{html.escape(rule_label)}</span></div>
  </header>
  <p class="stars">{int(skill.get("stars") or 0):,} Star <span>· Fork {int(skill.get("forks") or 0):,}</span></p>
  {growth_html}
  <ul class="cats">{chips}</ul>
  <p class="desc">{html.escape(description)}</p>
  <p class="why"><span>为什么收录</span>{html.escape(skill.get("notable_zh") or "")}</p>
  <div class="actions">
    <a class="btn primary" href="{html.escape(skill.get("source_url") or "")}">来源</a>
    {download_html}
    {homepage_html}
  </div>
  {download_note}
  <p class="install"><span>克隆安装</span> <code>{html.escape(skill.get("install_command") or "")}</code></p>
  {documented_html}
  <p class="meta-line">最近推送 {html.escape(pushed)} · 首次收录 {html.escape(skill.get("first_seen") or "")}</p>
</article>"""


def render_latest_update(report: dict) -> str:
    lines = [
        "# 最近一次更新",
        "",
        f"- 运行时间（Asia/Shanghai）：{report['run_at']}",
        f"- 收录总数：{report['total_skills']}",
        f"- 今日新增：{report['new_today']}",
        f"- 今日更新：{report['updated_today']}",
        f"- 今日移出：{report['removed_today']}",
        "",
        "## 今日新增",
        "",
    ]
    if not report["new_items"]:
        lines.append("本次没有新进入名录的 Skill。")
        lines.append("")
    for item in report["new_items"]:
        categories = "、".join(item["categories"])
        download = item["download"] or "直接下载未核验"
        lines.append(
            f"- [{item['name']}]({item['link']}) · {categories} · Star {item['stars']:,} · "
            f"来源 {item['source']} · 下载 {download}"
        )
        lines.append(f"  - {item['reason']}")
    lines.append("")
    lines.append("机器可读版本见 `data/daily-report.json`。")
    lines.append("")
    return "\n".join(lines)


def render_changelog(history: list[dict]) -> str:
    parts = ["# 更新日志", ""]
    for report in history:
        parts.extend(
            [
                f"## {report['run_date']}",
                "",
                f"- 运行时间（Asia/Shanghai）：{report['run_at']}",
                f"- 收录总数：{report['total_skills']}",
                f"- 今日新增：{report['new_today']}",
                f"- 今日更新：{report['updated_today']}",
                f"- 今日移出：{report.get('removed_today', 0)}",
                "",
            ]
        )
        if not report.get("new_items"):
            parts.append("没有新增 Skill。")
            parts.append("")
            continue
        for item in report["new_items"]:
            categories = "、".join(item["categories"])
            download = item["download"] or "直接下载未核验"
            parts.append(
                f"- {item['name']} · {categories} · Star {item['stars']:,} · "
                f"[来源]({item['source']}) · 下载 {download}"
            )
            parts.append(f"  - {item['reason']}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def validate_dataset(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version 不正确")
    skills = payload.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("skills 必须是非空数组")
        return errors
    seen = set()
    for skill in skills:
        sid = skill.get("id")
        if not sid or sid in seen:
            errors.append(f"技能 id 缺失或重复：{sid}")
        seen.add(sid)
        if not skill.get("name"):
            errors.append(f"{sid} 缺少 name")
        categories = skill.get("categories") or []
        if not categories or any(category not in CATEGORIES for category in categories):
            errors.append(f"{sid} 分类无效：{categories}")
        source = skill.get("source_url") or ""
        if not source.startswith("https://github.com/"):
            errors.append(f"{sid} 来源链接无效")
        if "download_available" not in skill:
            errors.append(f"{sid} 缺少 download_available")
        if skill.get("download_available"):
            if not str(skill.get("download_url") or "").startswith("https://"):
                errors.append(f"{sid} 标记了可下载但链接无效")
        else:
            if skill.get("download_url"):
                errors.append(f"{sid} 未核验下载却填写了链接")
            if not skill.get("download_note"):
                errors.append(f"{sid} 未核验下载时必须说明原因")
        install = skill.get("install_command") or ""
        if not install.startswith("git clone https://github.com/"):
            errors.append(f"{sid} 缺少可核验的克隆命令")
        if not isinstance(skill.get("stars"), int):
            errors.append(f"{sid} Star 不是整数")
        rule = (skill.get("qualification") or {}).get("rule")
        if rule not in {"stars", "growth"}:
            errors.append(f"{sid} 收录规则无效")
        if rule == "stars" and skill["stars"] < STAR_THRESHOLD:
            errors.append(f"{sid} 以 Star 门槛收录但数量不足")
        if rule == "growth" and skill["stars"] >= STAR_THRESHOLD:
            errors.append(f"{sid} 已达到 Star 门槛，不应标成仅靠增长")
        if not skill.get("notable_zh"):
            errors.append(f"{sid} 缺少收录理由")
    return errors


def validate_report(report: dict, skills: list[dict]) -> list[str]:
    errors = []
    required = [
        "schema_version",
        "timezone",
        "run_at",
        "run_date",
        "total_skills",
        "new_today",
        "updated_today",
        "removed_today",
        "new_items",
        "updated_items",
        "removed_items",
    ]
    for key in required:
        if key not in report:
            errors.append(f"日报缺少 {key}")
    if report.get("timezone") != "Asia/Shanghai":
        errors.append("日报时区必须是 Asia/Shanghai")
    if report.get("total_skills") != len(skills):
        errors.append("日报总数与技能列表不一致")
    if report.get("new_today") != len(report.get("new_items") or []):
        errors.append("new_today 与 new_items 数量不一致")
    for item in report.get("new_items") or []:
        for key in ("name", "categories", "stars", "source", "download", "link", "reason"):
            if key not in item:
                errors.append(f"新增项缺少 {key}")
        if item.get("source") and not str(item["source"]).startswith("https://"):
            errors.append(f"{item.get('name')} 来源不是链接")
        if item.get("download") is not None and not str(item["download"]).startswith("https://"):
            errors.append(f"{item.get('name')} 下载链接无效")
    return errors
