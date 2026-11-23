# Hot AI Coding Skills

This repository tracks **reusable AI coding skills**: skill packs for Cursor, Claude Code, Codex, and other coding agents, `SKILL.md` repositories, and well-known skill collections. It is not a model-news site and not a general AI-tools directory.

The page is static HTML. Skill records, star snapshots, and the daily report are JSON and Markdown files in this repository. **There is no database and no SMTP.**

## The page

Open [`site/index.html`](site/index.html) to search, filter by category, and sort by stars or last push. Each card shows:

- Name and summary. Repository names stay as published.
- One or more categories
- Source link (the original GitHub repository)
- Download or install path (a verified release asset or source zip, plus a `git clone` command)
- Star count, growth numbers when they are available, and the last push date
- One sentence on why it is listed
- A "New today" badge when it was added on the latest run

GitHub Pages publishes the `site/` directory. See below for how to turn that on.

## What gets listed

The unit is **one public GitHub repository** (a skill, a skill pack, or a skill catalog). Stars and growth are repository-level public numbers, so a collection is one entry. Skills inside a monorepo are not split out, because they do not have their own star counts.

A repository has to look like a skill pack for a coding agent: the name or description says skill / skills / `SKILL.md`, and the pack is about software delivery (coding, requirements, testing, architecture diagrams, or PPT). Marketing, trading, short video, academic writing, medical, social-media ops, note-taking apps, persona distillation, and offensive red-team packs are left out. A design pack that also mentions a social format, but is mainly PPT or diagrams, stays in. A boilerplate or CLI that only says "includes skills" at the end of its description does not.

Either rule is enough:

1. **Star bar:** GitHub shows at least **2,000** stars.
2. **Fast growth:** Stars may be under 2,000 when the growth is large and the numbers can be verified:
   - At least **100** new stars in the last **7** UTC calendar days, and at least **10%** of the current total, or
   - At least **250** new stars in the last **30** UTC calendar days, and at least **25%** of the current total.

Growth comes first from `GET /repos/{owner}/{repo}/stargazers/history`, which returns weekly buckets with a daily breakdown. If today's bucket is not posted yet, the page labels the figure as "at least" and does not guess the missing day. If that endpoint fails, the job uses daily snapshots in `data/star-snapshots.json`. Those snapshots can support a 7-day or 30-day window only after about that many daily runs. If neither source has the numbers, the repository is **not** added for growth.

## Categories

A skill can belong to more than one category:

| Category | Meaning |
| --- | --- |
| Requirements | Planning, requirements, product work, brainstorming |
| Development | Coding, implementation, engineering packs, and general skill libraries |
| Testing | Tests, TDD, code review, threat modeling, and triage |
| Design diagrams | Architecture diagrams, flowcharts, draw.io, Mermaid, infographics |
| Generate PPT | PPTX, PowerPoint, slide decks |

Categories are chosen the first time a skill is listed, from the name, description, topics, and README headings. They are recalculated only when the name, description, or topics change, so history is not reshuffled every day. To pin categories, edit [`data/category-overrides.json`](data/category-overrides.json):

```json
{
  "anthropics/skills": ["Development", "Testing", "Generate PPT"]
}
```

Keys are `owner/repo` (case-insensitive). Values must be categories from the table above.

## Data files

| File | Role |
| --- | --- |
| `data/skills.json` | Canonical skill data. The page and the report are generated from it. |
| `data/star-snapshots.json` | Daily star snapshot for each listed repository, kept for 45 days |
| `data/daily-report.json` | Machine-readable report for the latest run |
| `data/report-history.json` | Compact history of the last 90 runs, used to render the changelog |
| `data/category-overrides.json` | Hand-pinned categories |
| `docs/latest-update.md` | Human-readable note for the latest run |
| `CHANGELOG.md` | Day-by-day log |
| `site/index.html` | Static page generated from the data |
| `site/data/` | Copies published with the site |

These files are the whole store. Do not add a database, object store, or hosted data service.

When a GitHub description is not in English, `description` keeps the original text and `description_en` is the English summary shown on the site.

## Daily update

[`.github/workflows/daily-update.yml`](.github/workflows/daily-update.yml) runs at **23:00 UTC**, which is **07:00 in Asia/Shanghai** on the following calendar day. China does not observe daylight saving time. The report `run_date` is that Shanghai date, so a 23:00 UTC run is dated the next day in Asia/Shanghai. You can also run **Daily skill update** by hand from the Actions tab.

Each run:

1. Checks out `main` and refreshes stars with `GITHUB_TOKEN`
2. Finds repositories that newly meet the rules. Repositories already listed are refreshed even if search misses them that day.
3. Recategorizes only when the name, description, or topics change. The id stays the lowercase `owner/repo`.
4. Rewrites the JSON, the report, the changelog, and `site/index.html`
5. Commits straight to `main`. The message looks like `chore: daily skill update 2026-11-22`.

A push made with the Actions `GITHUB_TOKEN` does not start another run of this workflow, so the job does not loop. The workflow declares `contents: write`.

### Rate limits and an optional token

The scheduled job uses the built-in `GITHUB_TOKEN`. That is usually enough: search is about 30 requests per minute, and other core API calls are about 5,000 per hour. The script pauses between searches and retries short secondary rate limits.

Locally, use an existing `gh` login, or set `GITHUB_TOKEN` / `GH_TOKEN`. If that token cannot read star history, set `SKILL_GITHUB_TOKEN` to a classic personal access token that can read public repositories. Without the extra token, the star bar still works. Growth then falls back to the snapshots in this repository.

Each run checks growth for at most 80 relevant repositories under 2,000 stars, highest star count first. Repositories already listed are always refreshed and are not subject to that cap.

## Run it locally

Python 3.11 or newer. The standard library is enough.

```bash
python3 scripts/test_skills_lib.py
python3 scripts/update.py
python3 scripts/validate.py
python3 -m http.server -d site 8000
```

Then open `http://127.0.0.1:8000/`. `update.py` calls GitHub and overwrites `data/` and `site/index.html`. `python3 scripts/update.py --render-only` rebuilds the page from the files already on disk.

## Daily report

`data/daily-report.json` is the file a mailer or other tool should read. This repository does not store mailbox credentials and does not send email. A separate Grok Bot can read the report after the daily update and send it to `duan.mop@gmail.com`.

| Field | Meaning |
| --- | --- |
| `timezone` | Always `Asia/Shanghai` |
| `run_at` | Run time with a timezone offset |
| `run_date` | Date in Asia/Shanghai |
| `total_skills` | How many skills are listed |
| `new_today` | How many were seen for the first time today |
| `updated_today` | How many already listed skills changed stars, description, categories, download URL, or push time |
| `removed_today` | How many no longer qualify and were removed |
| `new_items` | New skills. Each item has `name`, `categories`, `stars`, `source`, `download`, `link`, and `reason` |
| `updated_items` / `removed_items` | Short lists of updates and removals |

`source` and `link` are both the canonical repository URL. `download` is a verified direct download URL, or `null` when verification failed. The page and `download_note` say so, and the clone command from the verified repository URL remains. `reason` is one English sentence on why the skill was added.

The same note for people is [`docs/latest-update.md`](docs/latest-update.md).

## Turn on GitHub Pages

1. Merge this repository to `main`.
2. Open Settings, then Pages.
3. Under **Build and deployment**, set Source to **GitHub Actions**.
4. [`.github/workflows/pages.yml`](.github/workflows/pages.yml) publishes `site/` when that directory changes on `main`.

The project site is usually `https://ai-derick-hub.github.io/AI-Coding-Hot-Skills/`. Styles, scripts, and data use relative paths, so the site works on that subpath.

## License

[MIT License](LICENSE). Skill names, descriptions, and links belong to their repositories. This project only stores facts read from the public GitHub API.
