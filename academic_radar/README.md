# 每日学术雷达

这是一个面向社会学研究生的轻量级学术信息筛选器。它每天从 OpenAlex、arXiv 和 RSS 源检索新近学术动态，围绕社会学理论、遗产研究、工业遗产旅游、军舰岛/端岛、平台表征、旅游社会学、日本社会、中日比较、生成 AI 与社会关系等主题进行去重、打分、筛选，并生成：

- 完整 Markdown 日报：`output/digests/YYYY-MM-DD_academic_digest.md`
- 一页 PDF 简报：`output/digests/YYYY-MM-DD_academic_brief.pdf`
- 公网网页静态站点：`output/site/index.html`
- 手机阅读短版：通过 ntfy、飞书、Telegram、Pushover 或 Email 推送；飞书版正文直接包含关键内容，不依赖电脑本地链接
- 运行日志：`output/logs/YYYY-MM-DD_run.log`

第一版默认启用 OpenAlex、arXiv、RSS 和中文/日文公开页面来源；Crossref 已实现但默认关闭，避免第一版过多噪声。

## 中文题名与中文速读

日报现在会同时显示：

- 原题
- 中文题名
- 原文摘要
- 中文速读

如果条目本身是中文或日文，系统会直接保留原题作为中文题名。如果是英文条目，自动翻译需要在 `.env` 中配置：

```text
OPENAI_API_KEY=
```

翻译只基于标题、摘要和来源元数据，不抓取全文，不声称读过全文。没有摘要时会明确写“摘要缺失，需人工查看”。如果没有配置 `OPENAI_API_KEY`，日报仍会生成，但中文题名会提示“未启用自动翻译，见原题”，中文速读会保留原文摘要摘录。

翻译缓存保存在：

```text
data/source_cache/translations.json
```

避免每天重复翻译同一条。

## 安装依赖

建议使用虚拟环境：

```bash
cd /Users/zhaomuchuan/Documents/ai使用研究/academic_radar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置 `.env`

复制示例文件：

```bash
cp .env.example .env
```

最小配置可以什么都不填。这样会只生成本地日报，不推送。

推荐填写 OpenAlex 邮箱，便于 API 联系和限流识别：

```text
OPENALEX_EMAIL=your_email@example.com
```

如果已经把 `output/site` 发布到公网，可以填写公网根地址：

```text
PUBLIC_BASE_URL=https://your-name.github.io/your-repo
```

这样飞书推送里会自动附上“公网网页”和“公网 PDF”链接。没有配置时，程序仍会生成本地网页和 PDF，但不会伪装成手机可打开的链接。

## 手动运行

```bash
cd /Users/zhaomuchuan/Documents/ai使用研究/academic_radar
python scripts/run_daily.py
```

运行完成后查看：

```bash
ls output/digests
ls output/logs
open output/site/index.html
```

## 手机推送

### ntfy，默认优先

在手机安装 ntfy，订阅一个足够随机的 topic，然后在 `.env` 中配置：

```text
NOTIFY_CHANNEL=ntfy
NTFY_TOPIC=your-random-topic
NTFY_SERVER=https://ntfy.sh
```

如果 `NTFY_TOPIC` 为空，程序会跳过推送，只保存日报。

### Telegram Bot

```text
NOTIFY_CHANNEL=telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

缺少 token 或 chat id 时不会推送。

### 飞书自定义机器人

适合不想安装 ntfy、但已经使用飞书的情况。建议建一个只有你自己的飞书群：

1. 打开飞书，建一个群或使用已有群。
2. 群设置里找到“机器人”或“群机器人”。
3. 添加“自定义机器人”。
4. 复制机器人 webhook 地址。
5. 如果开启“签名校验”，同时复制签名密钥。

在 `.env` 中配置：

```text
NOTIFY_CHANNEL=feishu
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx
FEISHU_SECRET=
```

如果机器人安全设置只使用“关键词”，请确保关键词包含在推送正文里，比如可以把关键词设为“每日学术雷达”。如果使用签名校验，就填写 `FEISHU_SECRET`。

当前飞书自定义机器人 webhook 不能直接上传本地 PDF 附件。系统会把手机版日报直接发到飞书正文里：Top 3 会包含中文题名、原题、来源、研究内容、与你研究的关系和链接；其他条目也会简短说明“研究了什么”。PDF 仍会保存在电脑本地作为归档。

如果配置了 `PUBLIC_BASE_URL`，飞书正文还会附上公网 HTML 日报和公网 PDF 链接。推荐用 GitHub Pages 承载这个静态站点。若要把 PDF 作为真正的飞书文件附件发到群里，需要改用飞书开放平台应用，并提供 `APP_ID`、`APP_SECRET` 和群 `CHAT_ID`。

### Pushover

```text
NOTIFY_CHANNEL=pushover
PUSHOVER_USER_KEY=
PUSHOVER_API_TOKEN=
```

### Email

```text
NOTIFY_CHANNEL=email
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=
EMAIL_TO=
```

## 本地 cron

每天北京时间早上 8:30 执行：

```bash
30 8 * * * cd /Users/zhaomuchuan/Documents/ai使用研究/academic_radar && /Users/zhaomuchuan/Documents/ai使用研究/academic_radar/.venv/bin/python scripts/run_daily.py
```

如果没有使用虚拟环境，可以把 Python 路径换成：

```bash
30 8 * * * cd /Users/zhaomuchuan/Documents/ai使用研究/academic_radar && /usr/bin/python3 scripts/run_daily.py
```

用 `crontab -e` 添加即可。

## GitHub Actions

工作流文件已经创建：

```text
../.github/workflows/daily_academic_radar.yml
```

GitHub Actions 使用 UTC。北京时间/JST 早上 8:30 对应 UTC 00:30，所以 workflow 中是：

```yaml
cron: "30 0 * * *"
```

支持手动触发 `workflow_dispatch`。每次运行后会上传 `output/digests/*.md`、`output/digests/*.pdf` 和 `output/logs/*.log` 作为 artifact，并把 `output/site` 发布到 GitHub Pages。

推送配置请放到 GitHub 仓库的 `Settings -> Secrets and variables -> Actions -> Repository secrets`：

- `OPENALEX_EMAIL`
- `OPENAI_API_KEY`
- `NOTIFY_CHANNEL`
- `NTFY_TOPIC`
- `NTFY_SERVER`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FEISHU_WEBHOOK_URL`
- `FEISHU_SECRET`
- `PUSHOVER_USER_KEY`
- `PUSHOVER_API_TOKEN`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_TO`

当前不会默认自动 commit 日报到仓库。如果你确认需要版本化保存，可以后续再加 commit 步骤。

### GitHub Pages 公网网页

当前 workflow 会把 `academic_radar/output/site` 发布到 GitHub Pages。第一次使用时需要：

1. 把当前项目推到 GitHub 仓库。
2. 打开仓库 `Settings -> Pages`。
3. Source 选择 `GitHub Actions`。
4. 在 Actions secrets 里配置 `NOTIFY_CHANNEL=feishu` 和 `FEISHU_WEBHOOK_URL`。
5. 手动运行一次 `Daily Academic Radar` workflow。

发布后，默认公网地址形如：

```text
https://你的GitHub用户名.github.io/仓库名/
```

每天飞书会收到这个公网网页地址，以及对应的公网 PDF 地址。手机不需要和电脑在同一个 Wi-Fi 下。

## 修改关键词

关键词在 `config.yaml` 的 `keyword_groups` 中。

主要分组：

- `sociology_core`：社会学核心
- `heritage_research`：遗产、旅游、平台、军舰岛方向
- `japan_china`：日本社会与中日比较
- `generative_ai_society`：生成 AI 与社会研究
- `japanese_terms`：日文关键词
- `chinese_terms`：中文关键词

每个分组有 `weight`。权重越高，命中后越容易进入日报。你的核心论文方向建议放在 `heritage_research` 或 `generative_ai_society` 中。

## RSS 源

RSS 源在 `config.yaml` 的 `sources.rss.feeds` 中。第一版预置了社会学博客、期刊、旅游/遗产研究、机构动态源，以及日本社会学会、J-STAGE 日文期刊、科学网 RSS。

注意：

- RSS 站点经常改 URL 或屏蔽抓取。
- 某个 RSS 源失败不会中断整体运行。
- 失败原因会写入 `output/logs/YYYY-MM-DD_run.log`。
- RSS 条目会按学术相关性筛选，不会把普通新闻强行当论文。

## 中文和日文平台来源

新增两类非英语来源：

- 日文 RSS：日本社会学会、J-STAGE 相关期刊，包括社会学、旅游研究、科学技术社会论等。
- 中文公开平台：科学网 RSS、中国社会科学网首页和社会学/社科好书/网络强国/考古现场等公开栏目。

中文网页栏目不是正式论文 API，通常只有标题和链接，没有稳定摘要、作者、DOI。因此系统会把它们标为“中文学术平台”或“学术动态”，并通过关键词筛选，不会把它们伪装成论文。

暂不直接抓取：

- CNKI / 知网：无稳定开放 API，且有访问限制。
- 万方 / 维普：无稳定开放 API。
- Google Scholar：不建议直接抓取网页；如果你提供 Alert 邮件、RSS 或导出方式，可以接入。
- 小红书 / TripAdvisor：它们更适合做专题研究数据采集，不适合作为每日学术信息源；后续可单独做“平台表征专题监测”。

## 去重规则

去重记录保存在：

```text
data/seen_items.json
```

优先级：

1. DOI
2. OpenAlex ID
3. arXiv ID
4. URL
5. 标题标准化哈希

同一篇内容在多个来源出现时，会尽量保留摘要、DOI、链接等信息更完整的一条。

## 打分逻辑

每条候选内容会计算 `relevance_score`。

加分包括：

- 命中社会学核心关键词
- 命中遗产/旅游/平台/军舰岛关键词
- 命中生成 AI 与社会研究关键词
- 涉及日本、中国、东亚或中日比较
- 有理论或方法信号
- 有 DOI 或稳定链接
- 最近 7 天或 30 天发布

降权包括：

- 纯技术论文但没有社会科学关联
- 商业新闻
- 无摘要且无法判断
- 医学、生物、工程细节强相关但没有社会研究意义

每天默认推送 Top 8 到 Top 12 条。如果不足，会从最近 7 天未推送过的高相关内容中补充。

## 查看历史日报

```bash
open output/digests
```

或直接打开某天文件：

```bash
less output/digests/YYYY-MM-DD_academic_digest.md
```

## 可选扩展

已经留好入口，但第一版未默认启用或未实现深度处理：

- Crossref：代码已实现，在 `config.yaml` 中把 `sources.crossref.enabled` 改成 `true` 即可。
- Semantic Scholar、SocArXiv、OSF、SSRN：建议后续逐一加入，避免噪声过大。
- Google Scholar Alert：不建议直接抓取 Google Scholar 网页；如果你提供可访问的邮件/RSS/导出方式，可以接入。
- LLM 摘要优化：当前使用规则摘要，不依赖 OpenAI API。若后续启用 LLM，摘要必须只基于标题、摘要和来源元数据，不能编造，不能声称读过全文。

## 常见问题

### 没有推送到手机

先看 `.env` 是否存在、`NOTIFY_CHANNEL` 和对应 token/topic 是否填写。没有配置时程序会正常生成日报并跳过推送。

### RSS 经常失败

这是正常现象。RSS URL 可能改版、限流或返回非标准 XML。程序会记录错误并继续处理其他来源。

### arXiv 出现偏技术内容

arXiv 本身偏计算机科学。程序会对纯技术、无社会科学关联的条目降权；如仍觉得噪声大，可以减少 `sources.arxiv.queries` 或提高 `project.min_score`。

### 想让日报更贴近论文方向

把你的具体论文题目、核心概念、田野对象、方法词加入 `heritage_research` 或对应分组，并适当提高分组权重。

### 中文/日文来源太少

可以在 `config.yaml` 里继续添加 RSS 或网页栏目。优先添加公开 RSS、大学研究所新闻页、学会公告页和出版社新书页。封闭数据库不建议直接抓取。

### 不想每天重复看到同一篇

不要删除 `data/seen_items.json`。如果你想重置历史记录，可以备份后清空其中的 `items`。
