# 热门 AI 编程 Skills

这个仓库跟踪**可复用的 AI 编程技能**：给 Cursor、Claude Code、Codex 以及其他编码代理使用的 Skill、`SKILL.md` 技能包，以及官方或知名技能合集。它不是模型新闻站，也不是泛泛的 AI 工具目录。

页面是静态 HTML。技能数据、Star 快照和每日报告都放在仓库里的 JSON / Markdown 文件中。**不使用数据库，也不需要 SMTP。**

## 页面

打开 [`site/index.html`](site/index.html) 可以搜索、按分类筛选、按 Star 或最近推送排序。每张卡片都有：

- 名称（保留英文专名）和简介
- 一个或多个分类
- 来源链接（原始 GitHub 仓库）
- 下载或安装路径（核验过的 Release / 源码 zip，以及 `git clone` 命令）
- Star 数、增长数字（如果查得到）、最近推送日期
- 一句话说明为什么被收录
- 「今日新增」标记

GitHub Pages 发布的是 `site/` 目录。启用方式见下文。

## 什么会被收录

追踪单位是**一个公开 GitHub 仓库**（一个技能、一个技能包，或一个技能目录）。Star 和增长都是仓库级别的公开数字，所以合集仓库算一条，而不是把合集里的每个子技能拆成没有独立 Star 的条目。

仓库必须看起来像编码代理的技能包：名称或简介里有 skill / skills / `SKILL.md`，并且和软件交付有关（写代码、需求规划、测试、架构图、PPT）。营销、交易、短视频、学术写作、医疗、社媒运营、笔记软件、人格蒸馏，以及红队 / 漏洞利用类技能包不会进入目录。附带提到小红书或公众号、但主体是 PPT / 设计图的技能包仍然保留。只是在产品简介末尾写了 “includes skills” 的脚手架或 CLI 也不会收录。

满足下面**任一**条件即收录：

1. **Star 门槛：** GitHub 显示的 Star 不少于 **2000**。
2. **快速增长：** 当前 Star 可以低于 2000，但增长要足够明显，并且数字必须核验得到：
   - 近 **7** 个 UTC 日历日新增至少 **100** Star，且不少于当前 Star 的 **10%**；或
   - 近 **30** 个 UTC 日历日新增至少 **250** Star，且不少于当前 Star 的 **25%**。

增长优先来自 GitHub API `GET /repos/{owner}/{repo}/stargazers/history` 的按日计数。这个接口返回的是按周汇总、里面再拆到每一天的公开数据。若当天的周统计还没入账，页面会把已入账的天数标成「至少新增」，不会把缺失的天数估进去。接口失败时，改用本仓库 `data/star-snapshots.json` 里按天保存的 Star 快照；快照要积累满大约 7 天或 30 天后才能算出对应窗口。两种来源都没有时，**不会猜测增长，也不会仅凭感觉收录**。

## 分类

一个技能可以属于多个分类：

| 分类 | 含义 |
| --- | --- |
| 需求 | 规划、需求、产品方案、头脑风暴 |
| 开发 | 编码、实现、工程化技能包和综合技能库 |
| 测试 | 测试、TDD、代码审查、威胁建模和修复分流 |
| 绘制设计图 | 架构图、流程图、draw.io、Mermaid 等信息图 |
| 生成 PPT | PPTX、PowerPoint、幻灯片 |

分类在技能**第一次收录**时根据名称、简介、topic 和 README 判定。之后只有名称、简介或 topic 变了才会重算，避免每天把历史分类打乱。需要固定分类时，写入 [`data/category-overrides.json`](data/category-overrides.json)：

```json
{
  "anthropics/skills": ["开发", "测试", "生成 PPT"]
}
```

键是 `owner/repo`（大小写不敏感），值必须是上表里的分类。

## 数据文件

| 文件 | 作用 |
| --- | --- |
| `data/skills.json` | 技能主数据。页面和日报都由它生成 |
| `data/star-snapshots.json` | 每个已收录仓库的每日 Star 快照，最多保留 45 天 |
| `data/daily-report.json` | 最近一次运行的机器可读日报 |
| `data/report-history.json` | 最近 90 次运行的摘要，用来生成更新日志 |
| `data/category-overrides.json` | 人工固定的分类 |
| `docs/latest-update.md` | 给人读的最近一次更新 |
| `CHANGELOG.md` | 按日累积的更新日志 |
| `site/index.html` | 由数据生成的静态页面 |
| `site/data/` | 发布到 Pages 的数据副本，方便直接打开网站时读取 |

这些文件就是全部状态。不要再加数据库、对象存储或外部托管的数据服务。

## 每日更新

[`.github/workflows/daily-update.yml`](.github/workflows/daily-update.yml) 在每天 **00:00 UTC** 运行，也就是 **北京时间 08:00**（中国不实行夏令时）。也可以在 Actions 页面手动运行 `Daily skill update`。

每次运行会：

1. 用 `GITHUB_TOKEN` 重新搜索和刷新 Star
2. 发现达到门槛的新技能；已收录技能即使用搜索暂时漏掉也会刷新
3. 只在简介或 topic 变化时重算分类，`id` 始终是小写的 `owner/repo`
4. 重写 JSON、日报、更新日志和 `site/index.html`
5. 把变更提交回默认分支，提交信息类似 `chore: daily skill update 2026-11-22`

`GITHUB_TOKEN` 推送默认不会再次触发这个 workflow，所以不会形成循环。仓库 Actions 需要有写入内容的权限；workflow 里已经声明 `contents: write`。

### 速率限制和可选 token

日常刷新使用 Actions 自带的 `GITHUB_TOKEN`，一般够用：搜索接口大约每分钟 30 次，其余核心接口每小时 5000 次。脚本会在搜索之间暂停，并在次级速率限制时短暂重试。

本地运行可以使用已经登录的 `gh`，或者设置 `GITHUB_TOKEN` / `GH_TOKEN`。如果默认 token 读不到 Star 历史，可以再提供一个能读取公开仓库的 classic PAT，变量名是 `SKILL_GITHUB_TOKEN`。没有这个额外 token 时，Star 门槛仍然有效；增长会退回到仓库里的每日快照。

单次运行最多对 80 个 Star 低于 2000 的相关候选核验增长，按当前 Star 从高到低。已经收录的仓库每次都会刷新，不受这个上限影响。

## 本地运行

需要 Python 3.11 或更新版本，只用标准库。

```bash
python3 scripts/test_skills_lib.py
python3 scripts/update.py
python3 scripts/validate.py
python3 -m http.server -d site 8000
```

然后打开 `http://127.0.0.1:8000/`。`update.py` 会访问 GitHub，并覆盖 `data/` 和 `site/index.html`。

## 每日报告

`data/daily-report.json` 是邮件或其他下游工具应该读取的文件。本仓库不保存邮箱密码，也不发送邮件。单独的 Grok Bot 可以在每日更新后读取这份报告，并发送到 `duan.mop@gmail.com`。

字段：

| 字段 | 含义 |
| --- | --- |
| `timezone` | 固定为 `Asia/Shanghai` |
| `run_at` | 带时区的运行时间 |
| `run_date` | 北京时间的日期 |
| `total_skills` | 当前收录总数 |
| `new_today` | 今天第一次出现的数量 |
| `updated_today` | 今天已存在、但 Star、简介、分类、下载链接或推送时间有变化的数量 |
| `removed_today` | 今天不再符合规则而被移出的数量 |
| `new_items` | 新增列表。每项包含 `name`、`categories`、`stars`、`source`、`download`、`link`、`reason` |
| `updated_items` / `removed_items` | 更新和移出的简表 |

`source` 和 `link` 都是原始仓库地址。`download` 是核验过的直接下载 URL；核验失败时为 `null`，页面和 `download_note` 会写明直接下载不可用，同时仍保留来源和 `git clone` 命令。`reason` 是一行中文，说明它为什么被加进来。

给人读的同一份内容在 [`docs/latest-update.md`](docs/latest-update.md)。

## 启用 GitHub Pages

1. 把本仓库合并到 `main`。
2. 打开仓库 Settings → Pages。
3. **Build and deployment** 的 Source 选择 **GitHub Actions**。
4. [`.github/workflows/pages.yml`](.github/workflows/pages.yml) 会在 `main` 上的 `site/` 变化后发布。

项目页地址一般是 `https://ai-derick-hub.github.io/AI-Coding-Hot-Skills/`。页面里的样式、脚本和数据都使用相对路径，可以放在这个子路径下。

## 许可

[MIT License](LICENSE)。页面上的技能名称、简介和链接属于各自仓库的作者；本仓库只保存从 GitHub 公开 API 读到的事实数据。
