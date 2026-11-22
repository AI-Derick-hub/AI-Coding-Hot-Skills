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

CATEGORIES = ["Requirements", "Development", "Testing", "Design diagrams", "Generate PPT"]


def _cp(codes: str) -> str:
    """Decode space-separated code points. Keeps source-text match tokens out of this file."""
    return "".join(chr(int(part, 16)) for part in codes.split())

OFFICIAL_OWNERS = {"anthropics", "openai", "github", "microsoft", "vercel-labs", "google"}

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Requirements": [
        r"planning",
        r"product management",
        r"product-manager",
        r"\bprd\b",
        r"user stor(?:y|ies)",
        r"brainstorm",
        _cp("9700 6c42"),
        _cp("4ea7 54c1 7ecf 7406"),
        _cp("8def 7ebf 56fe"),
        r"roadmap",
    ],
    "Development": [
        r"coding",
        r"developer",
        r"programming",
        r"refactor",
        r"full[- ]stack",
        r"software development",
        r"\bengineering\b",
        r"\bdevelopment\b",
        _cp("7f16 7a0b"),
        _cp("5f00 53d1"),
        _cp("5de5 7a0b 5e08"),
        r"pair programmer",
        r"frontend",
        r"ui/ux",
        _cp("754c 9762"),
        r"landing page",
        _cp("843d 5730 9875"),
    ],
    "Testing": [
        r"\btesting\b",
        r"test-driven",
        r"\btests\b",
        r"\btdd\b",
        r"\bqa\b",
        r"code review",
        r"threat model",
        r"\btriage\b",
        _cp("6d4b 8bd5"),
        _cp("8d28 91cf 4fdd 969c"),
    ],
    "Design diagrams": [
        r"diagram",
        r"flowchart",
        r"mermaid",
        r"draw\.?io",
        r"wireframe",
        r"architecture diagram",
        _cp("4fe1 606f 56fe"),
        r"infographic",
        _cp("67b6 6784 56fe"),
        _cp("8bbe 8ba1 56fe"),
        _cp("6d41 7a0b 56fe"),
        r"\buml\b",
        r"c4-model",
        r"c4 model",
    ],
    "Generate PPT": [
        r"pptx",
        r"powerpoint",
        r"\bppt\b",
        r"slide deck",
        r"\bslides\b",
        _cp("5e7b 706f 7247"),
        _cp("6f14 793a 6587 7a3f"),
    ],
}

TOPIC_CATEGORY = {
    "planning": "Requirements",
    "product-management": "Requirements",
    "brainstorming": "Requirements",
    "tdd": "Testing",
    "testing": "Testing",
    "code-review": "Testing",
    "diagrams": "Design diagrams",
    "diagram": "Design diagrams",
    "mermaid": "Design diagrams",
    "drawio": "Design diagrams",
    "flowchart": "Design diagrams",
    "architecture-diagram": "Design diagrams",
    "infographic": "Design diagrams",
    "uml": "Design diagrams",
    "c4-model": "Design diagrams",
    "pptx": "Generate PPT",
    "slides": "Generate PPT",
    "powerpoint": "Generate PPT",
    "ppt-skill": "Generate PPT",
    "ai-ppt": "Generate PPT",
    "coding": "Development",
    "coding-agent": "Development",
    "coding-agents": "Development",
    "ai-coding": "Development",
    "developer-tools": "Development",
    "sdlc": "Development",
    "frontend": "Development",
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
    r"coding agents?|ai agents?|agentic|agent skills?|\.agents\b|"
    + _cp("667a 80fd 4f53")
    + "|"
    + _cp("7f16 7801 4ee3 7406"),
    re.I,
)

OFFENSIVE_PATTERN = re.compile(
    r"red[- ]team|offensive security|pentest|penetration testing|\bexploit\b|"
    r"\bmalware\b|\bphishing\b|\bransomware\b|" + _cp("6f0f 6d1e 5229 7528"),
    re.I,
)

# Name-level or lead-in signals that the repo is not a software-delivery skill.
NON_SDLC_PATTERN = re.compile(
    r"trading|equity investor|\bstocks?\b|"
    + _cp("671f 6743")
    + "|"
    + _cp("91d1 878d")
    + r"|finance|financial|"
    r"\bvideo\b|b-roll|short[- ]drama|"
    + _cp("77ed 5267")
    + "|"
    + _cp("6f2b 5267")
    + r"|stickman|motion graphics|\bffmpeg\b|"
    r"xiaohongshu|"
    + _cp("5c0f 7ea2 4e66")
    + "|"
    + _cp("516c 4f17 53f7")
    + r"|instagram|linkedin|"
    r"academic research|"
    + _cp("5b66 672f")
    + "|"
    + _cp("8bba 6587")
    + r"|empirical research|\bads\b|"
    r"\bmedical\b|"
    + _cp("4e34 5e8a")
    + "|"
    + _cp("533b 7597")
    + r"|\bnsfw\b|"
    r"\bctf\b|reverse engineering|\bpwn\b|"
    r"humanizer|ai-generated writing|"
    + _cp("9632 5fa1 6027 5199 4f5c")
    + "|"
    r"distill how anyone|"
    + _cp("601d 7ef4 65b9 5f0f")
    + "|"
    + _cp("5fc3 667a 6a21 578b")
    + "|"
    r"\bobsidian\b|numerolog|"
    + _cp("5360 535c")
    + "|"
    + _cp("516b 5b57")
    + "|"
    r"supply-chain|automotive|\bbooking\b|\bblender\b|"
    r"turns books into|book-to-skill|marketing|copywriting|\bseo\b|"
    r"ai scientist|bioinformatics|drug discovery|job search|"
    + _cp("7f51 6587")
    + r"|fanfic",
    re.I,
)
SDLC_PATTERN = re.compile(
    r"coding|developer|engineer|software|programming|refactor|frontend|backend|"
    r"full[- ]stack|code review|\btdd\b|\btesting\b|\bqa\b|diagram|architecture|"
    r"pptx|powerpoint|\bslides?\b|planning|\bprd\b|\bsdlc\b|debug|"
    + _cp("7f16 7a0b")
    + "|"
    + _cp("5f00 53d1")
    + "|"
    + _cp("6d4b 8bd5")
    + "|"
    + _cp("67b6 6784 56fe")
    + "|"
    + _cp("9700 6c42")
    + "|"
    + _cp("8bbe 8ba1 56fe")
    + "|"
    + _cp("5e7b 706f 7247")
    + "|"
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
    _cp("5c0f 8bf4")
    + "|"
    + _cp("7f51 6587")
    + r"|novelist|fanfic|"
    + _cp("9ad8 8003")
    + "|"
    + _cp("8003 7814")
    + "|"
    + _cp("4e2d 533b")
    + "|"
    + _cp("7d2b 5fae")
    + "|"
    + _cp("516b 5b57")
    + "|"
    + _cp("5360 535c")
    + "|"
    r"\bresume\b|job application|"
    + _cp("6c42 804c")
    + r"|paper writing|"
    + _cp("8bba 6587 5199 4f5c")
    + "|"
    r"reverse engineering|"
    + _cp("9006 5411")
    + "|"
    r"persona[- ]distill|"
    + _cp("4eba 683c 84b8 998f")
    + r"|de-ai writing|"
    + _cp("53bb")
    + r" ?ai ?"
    + _cp("5473")
    + "|"
    r"distill high-value|"
    + _cp("9ad8 4ef7 503c 5185 5bb9 84b8 998f")
    + r"|logo[- ]design|"
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
        "storage": "JSON and Markdown files in this repository. No database and no external datastore.",
        "unit": "One public GitHub repository (a skill, a skill pack, or an official skill catalog)",
        "star_threshold": STAR_THRESHOLD,
        "growth": {
            "source": "Daily counts from GET /repos/{owner}/{repo}/stargazers/history. If that endpoint is unavailable, use the daily snapshots in data/star-snapshots.json.",
            "stars_7d_min": GROWTH_7D_MIN,
            "stars_7d_ratio_min": GROWTH_7D_RATIO,
            "stars_30d_min": GROWTH_30D_MIN,
            "stars_30d_ratio_min": GROWTH_30D_RATIO,
            "window": "UTC calendar days ending on the run date, including that date. If GitHub has not posted the current day yet, the counted days are a lower bound.",
            "logic": "Below the star bar, qualify on either the 7-day absolute count and share, or the 30-day absolute count and share.",
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
    catalog_words = r"curated|collection of|catalog of|awesome|" + _cp("6280 80fd 5e93") + "|" + _cp("6280 80fd 5305")
    if "Development" not in found and re.search(r"skill", short, re.I) and re.search(catalog_words, short, re.I):
        found.append("Development")
    if not found and (
        _is_general_coding_pack(name, description)
        or re.search(r"agent skills|skills catalog|skills framework|" + _cp("6280 80fd 5305") + "|" + _cp("6280 80fd 5e93"), short, re.I)
    ):
        found.append("Development")
    return [category for category in CATEGORIES if category in found]


def _is_general_coding_pack(name: str, description: str) -> bool:
    if not re.search(r"skill", name or "", re.I):
        return False
    return bool(
        re.search(
            r"engineer|coding|developer|" + _cp("7f16 7a0b") + "|" + _cp("5f00 53d1") + "|" + _cp("8f6f 4ef6"),
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
    return not bool(
        re.search(
            r"pptx|powerpoint|\bdiagram\b|"
            + _cp("67b6 6784 56fe")
            + "|"
            + _cp("7f16 7a0b")
            + "|"
            + _cp("8f6f 4ef6 5f00 53d1"),
            description or "",
            re.I,
        )
    )


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
        return False, "fork or mirror; not listed separately"
    name = repo.get("name") or ""
    description = repo.get("description") or ""
    topics = [str(topic).lower() for topic in repo.get("topics") or []]
    blob = f"{name}\n{description}\n{' '.join(topics)}"
    if OFFENSIVE_PATTERN.search(blob):
        return False, "offensive security or exploit skill; not listed"
    if _outside_software_delivery(name, description):
        return False, "not a software-delivery skill (requirements, development, testing, diagrams, or PPT)"
    if CONVERTER_PATTERN.search(description.strip()) or PRODUCT_NOT_SKILL_PATTERN.search(description):
        return False, "tool, scanner, or builder rather than an installable skill pack"
    if not _skill_is_the_product(name, description):
        skill_topic = any(topic in SKILL_TOPICS for topic in topics)
        diagram_or_ppt = bool(re.search(r"pptx|powerpoint|\bdiagram\b", description, re.I))
        if not (skill_topic and diagram_or_ppt):
            return False, "skills are not the subject of this repository"
    elif not (
        re.search(r"skill", name, re.I)
        or re.search(r"\bskills?\b|SKILL\.md", description, re.I)
        or any(topic in SKILL_TOPICS for topic in topics)
    ):
        return False, "name, description, and topics do not identify a skill repository"
    if not HOST_PATTERN.search(blob) and not any(topic in SKILL_TOPICS for topic in topics):
        return False, "not aimed at Claude, Cursor, Codex, Copilot, or another coding agent"
    if not _software_delivery_focus(name, description, topics):
        return False, "does not match requirements, development, testing, diagrams, or PPT"
    return True, "name or description shows a reusable skill pack for coding agents"


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
        return "growth figures are not available yet"
    prefix = "at least " if growth.get("partial") else ""
    parts = []
    if isinstance(growth.get("stars_7d"), int):
        parts.append(f"{prefix}{growth['stars_7d']:,} new stars in the last 7 days")
    if isinstance(growth.get("stars_30d"), int):
        parts.append(f"{prefix}{growth['stars_30d']:,} new stars in the last 30 days")
    through = growth.get("history_through")
    suffix = f" (counted through {through})" if through else ""
    return ", ".join(parts) + suffix


def notable_text(repo: dict, growth: dict | None, rule: str) -> str:
    stars = int(repo.get("stars") or 0)
    owner = (repo.get("full_name") or "/").split("/")[0].lower()
    if rule == "stars":
        text = f"Public stars: {stars:,}, which meets the {STAR_THRESHOLD:,}-star bar."
        if growth and growth.get("available"):
            text += " " + growth_phrase(growth).capitalize() + "."
    else:
        text = (
            f"Current stars: {stars:,}, below {STAR_THRESHOLD:,}, but {growth_phrase(growth)}, "
            "which meets the fast-growth bar."
        )
    if owner in OFFICIAL_OWNERS:
        text += f" Official repository from {owner}."
    description = (repo.get("description_en") or repo.get("description") or "").strip()
    if description:
        short = description if len(description) <= 90 else description[:89].rstrip() + "…"
        text += f" Summary: {short}"
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


def public_payload(payload: dict) -> dict:
    """Copy used on the static site. Display text is English."""
    published = json.loads(json.dumps(payload))
    for skill in published.get("skills") or []:
        english = skill.get("description_en")
        if english:
            skill["description"] = english
    return published


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
        new_block = "<p>Nothing new entered the catalog today. Everything already listed is below.</p>"
    elif len(new_skills) == len(skills):
        new_block = (
            f"<p>Every skill currently listed, <strong>{len(new_skills)}</strong> in total, was added today. "
            "Each card is marked New today. Highest star counts:</p>"
            f"<div class=\"new-links\">{''.join(new_links)}</div>"
        )
    else:
        more = ""
        if len(ranked_new) > len(preview):
            more = (
                f"<p>The other {len(ranked_new) - len(preview)} are also marked New today. "
                "Use the scope filter to see only those.</p>"
            )
        new_block = (
            f"<p><strong>{len(new_skills)}</strong> skills entered the catalog today. "
            "Select a name to jump to its card.</p>"
            f"<div class=\"new-links\">{''.join(new_links)}</div>{more}"
        )
    cards = "\n".join(render_card(skill, run_day) for skill in skills)
    category_buttons = [
        '<button type="button" class="chip" data-cat="" aria-pressed="true">All '
        f"<span>{len(skills)}</span></button>"
    ]
    for category in CATEGORIES:
        category_buttons.append(
            f'<button type="button" class="chip" data-cat="{html.escape(category)}" aria-pressed="false">'
            f"{html.escape(category)} <span>{counts[category]}</span></button>"
        )
    rules = payload["criteria"]["growth"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hot AI Coding Skills</title>
  <meta name="description" content="A searchable catalog of hot AI coding skills. Data comes from public GitHub repositories and is updated daily.">
  <meta name="theme-color" content="#000000">
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <div class="sky" aria-hidden="true">
    <svg class="circuit" viewBox="0 0 1200 280" preserveAspectRatio="xMaxYMin slice">
      <path d="M760 70 H920 V150 H1080 V90 H1180"/>
      <path d="M920 150 V220 H1040"/>
      <circle cx="920" cy="70" r="3.5"/>
      <circle cx="1080" cy="150" r="3.5"/>
      <circle cx="1180" cy="90" r="4"/>
    </svg>
  </div>
  <a class="skip" href="#grid">Skip to the skill list</a>
  <header class="masthead">
    <div class="wrap">
      <p class="eyebrow">AI Coding Hot Skills</p>
      <h1>Hot AI Coding Skills</h1>
      <p class="lede">Reusable skills for coding agents: Cursor, Claude Code, Codex, SKILL.md packs, and well-known collections. This is not a general model-news or AI-tools directory.</p>
      <dl class="stats">
        <div><dt>Listed</dt><dd>{len(skills)}</dd></div>
        <div><dt>New today</dt><dd>{len(new_skills)}</dd></div>
        <div><dt>Updated today</dt><dd>{payload.get("updated_today", 0)}</dd></div>
        <div><dt>Updated at</dt><dd>{html.escape(generated.replace("T", " ")[:16])}</dd></div>
      </dl>
    </div>
  </header>
  <main class="wrap">
    <section class="panel" id="new-today">
      <h2>New today</h2>
      {new_block}
    </section>
    <section class="toolbar" aria-label="Filters">
      <label class="search">
        <span>Search</span>
        <input id="q" type="search" placeholder="Search name, repository, or summary" autocomplete="off">
      </label>
      <div class="chips" role="group" aria-label="Categories">{''.join(category_buttons)}</div>
      <div class="toolbar-row">
        <label>Scope
          <select id="rule">
            <option value="all">All</option>
            <option value="stars">At least {STAR_THRESHOLD:,} stars</option>
            <option value="growth">Fast growth</option>
            <option value="new">New today</option>
          </select>
        </label>
        <label>Sort
          <select id="sort">
            <option value="stars">Stars, high to low</option>
            <option value="updated">Recently pushed</option>
            <option value="new">New today first</option>
            <option value="name">Name</option>
          </select>
        </label>
        <p id="result-count" class="result-count">{len(skills)} results</p>
      </div>
    </section>
    <p id="empty" class="empty" hidden>No skills match these filters.</p>
    <section class="grid" id="grid">
      {cards}
    </section>
    <section class="panel rules">
      <h2>Inclusion rules</h2>
      <p>Each entry is one public GitHub repository. It is listed when either rule is true:</p>
      <ol>
        <li>GitHub shows at least {STAR_THRESHOLD:,} stars.</li>
        <li>Stars are still below {STAR_THRESHOLD:,}, but growth is fast: at least {rules["stars_7d_min"]} new stars in 7 UTC calendar days and at least {int(rules["stars_7d_ratio_min"] * 100)}% of the current total, or at least {rules["stars_30d_min"]} new stars in 30 days and at least {int(rules["stars_30d_ratio_min"] * 100)}%. The counts come from GitHub's daily star history. If they cannot be verified, the repository is not added.</li>
      </ol>
      <p>A skill can have more than one category: Requirements, Development, Testing, Design diagrams, and Generate PPT. The files are <code>data/skills.json</code> and <code>data/daily-report.json</code>. This project does not use a database.</p>
    </section>
  </main>
  <footer class="wrap site-footer">
    <p>Static page generated from JSON in the repository. Machine-readable report: <a href="data/daily-report.json">data/daily-report.json</a>. Skill data: <a href="data/skills.json">data/skills.json</a>.</p>
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
    description = skill.get("description_en") or skill.get("description") or "This repository has no description."
    growth = skill.get("growth") or {}
    growth_html = ""
    if isinstance(growth.get("stars_7d"), int):
        prefix = "at least " if growth.get("partial") else ""
        growth_html = (
            f'<p class="growth">{prefix}+{growth["stars_7d"]:,} stars in 7 days · '
            f'+{growth.get("stars_30d") or 0:,} in 30 days '
            f'(through {html.escape(str(growth.get("history_through") or ""))})</p>'
        )
    rule = (skill.get("qualification") or {}).get("rule") or ""
    rule_label = "Fast growth" if rule == "growth" else f"Stars ≥ {STAR_THRESHOLD:,}"
    new_badge = '<span class="badge new">New today</span>' if skill.get("first_seen") == run_day else ""
    archive_badge = '<span class="badge">Archived</span>' if skill.get("archived") else ""
    download_url = skill.get("download_url")
    if skill.get("download_available") and download_url:
        download_html = (
            f'<a class="btn" href="{html.escape(download_url)}">Download</a>'
        )
        download_note = f'<p class="meta-line">{html.escape(skill.get("download_note") or "")}</p>'
    else:
        download_html = '<span class="btn disabled">Direct download not verified</span>'
        download_note = (
            '<p class="meta-line warn">Direct download: not verified. '
            f'{html.escape(skill.get("download_note") or "No verified archive or release asset.")}</p>'
        )
    documented = skill.get("documented_install")
    documented_html = ""
    if documented:
        documented_html = (
            '<p class="install"><span>Install command from the docs</span> '
            f"<code>{html.escape(documented)}</code></p>"
        )
    homepage = skill.get("homepage") or ""
    homepage_html = ""
    if homepage.startswith("http"):
        homepage_html = f'<a class="btn ghost" href="{html.escape(homepage)}">Homepage</a>'
    search_blob = " ".join(
        [
            skill.get("name") or "",
            skill.get("id") or "",
            description,
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
  <p class="why"><span>Why it is listed</span>{html.escape(skill.get("notable_zh") or "")}</p>
  <div class="actions">
    <a class="btn primary" href="{html.escape(skill.get("source_url") or "")}">Source</a>
    {download_html}
    {homepage_html}
  </div>
  {download_note}
  <p class="install"><span>Clone</span> <code>{html.escape(skill.get("install_command") or "")}</code></p>
  {documented_html}
  <p class="meta-line">Last push {html.escape(pushed)} · First listed {html.escape(skill.get("first_seen") or "")}</p>
</article>"""


def render_latest_update(report: dict) -> str:
    lines = [
        "# Latest update",
        "",
        f"- Run time (Asia/Shanghai): {report['run_at']}",
        f"- Total skills: {report['total_skills']}",
        f"- New today: {report['new_today']}",
        f"- Updated today: {report['updated_today']}",
        f"- Removed today: {report['removed_today']}",
        "",
        "## New today",
        "",
    ]
    if not report["new_items"]:
        lines.append("No skills entered the catalog on this run.")
        lines.append("")
    for item in report["new_items"]:
        categories = ", ".join(item["categories"])
        download = item["download"] or "direct download not verified"
        lines.append(
            f"- [{item['name']}]({item['link']}) · {categories} · {item['stars']:,} stars · "
            f"source {item['source']} · download {download}"
        )
        lines.append(f"  - {item['reason']}")
    lines.append("")
    lines.append("The machine-readable copy is `data/daily-report.json`.")
    lines.append("")
    return "\n".join(lines)


def render_changelog(history: list[dict]) -> str:
    parts = ["# Changelog", ""]
    for report in history:
        parts.extend(
            [
                f"## {report['run_date']}",
                "",
                f"- Run time (Asia/Shanghai): {report['run_at']}",
                f"- Total skills: {report['total_skills']}",
                f"- New today: {report['new_today']}",
                f"- Updated today: {report['updated_today']}",
                f"- Removed today: {report.get('removed_today', 0)}",
                "",
            ]
        )
        if not report.get("new_items"):
            parts.append("No new skills.")
            parts.append("")
            continue
        for item in report["new_items"]:
            categories = ", ".join(item["categories"])
            download = item["download"] or "direct download not verified"
            parts.append(
                f"- {item['name']} · {categories} · {item['stars']:,} stars · "
                f"[source]({item['source']}) · download {download}"
            )
            parts.append(f"  - {item['reason']}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def validate_dataset(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version is wrong")
    skills = payload.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("skills must be a non-empty list")
        return errors
    seen = set()
    for skill in skills:
        sid = skill.get("id")
        if not sid or sid in seen:
            errors.append(f"missing or duplicate skill id: {sid}")
        seen.add(sid)
        if not skill.get("name"):
            errors.append(f"{sid} is missing name")
        categories = skill.get("categories") or []
        if not categories or any(category not in CATEGORIES for category in categories):
            errors.append(f"{sid} has invalid categories: {categories}")
        source = skill.get("source_url") or ""
        if not source.startswith("https://github.com/"):
            errors.append(f"{sid} has an invalid source URL")
        if "download_available" not in skill:
            errors.append(f"{sid} is missing download_available")
        if skill.get("download_available"):
            if not str(skill.get("download_url") or "").startswith("https://"):
                errors.append(f"{sid} is marked downloadable but the URL is invalid")
        else:
            if skill.get("download_url"):
                errors.append(f"{sid} has a download URL but was not verified")
            if not skill.get("download_note"):
                errors.append(f"{sid} needs a note when the download is not verified")
        install = skill.get("install_command") or ""
        if not install.startswith("git clone https://github.com/"):
            errors.append(f"{sid} is missing a verified clone command")
        if not isinstance(skill.get("stars"), int):
            errors.append(f"{sid} stars value is not an integer")
        rule = (skill.get("qualification") or {}).get("rule")
        if rule not in {"stars", "growth"}:
            errors.append(f"{sid} has an invalid inclusion rule")
        if rule == "stars" and skill["stars"] < STAR_THRESHOLD:
            errors.append(f"{sid} is included by the star bar but is under the threshold")
        if rule == "growth" and skill["stars"] >= STAR_THRESHOLD:
            errors.append(f"{sid} already meets the star bar and should not be marked growth-only")
        if not skill.get("notable_zh"):
            errors.append(f"{sid} is missing the inclusion reason")
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
            errors.append(f"daily report is missing {key}")
    if report.get("timezone") != "Asia/Shanghai":
        errors.append("daily report timezone must be Asia/Shanghai")
    if report.get("total_skills") != len(skills):
        errors.append("daily report total does not match the skill list")
    if report.get("new_today") != len(report.get("new_items") or []):
        errors.append("new_today does not match the number of new_items")
    for item in report.get("new_items") or []:
        for key in ("name", "categories", "stars", "source", "download", "link", "reason"):
            if key not in item:
                errors.append(f"new item is missing {key}")
        if item.get("source") and not str(item["source"]).startswith("https://"):
            errors.append(f"{item.get('name')} source is not a URL")
        if item.get("download") is not None and not str(item["download"]).startswith("https://"):
            errors.append(f"{item.get('name')} download URL is invalid")
    return errors
