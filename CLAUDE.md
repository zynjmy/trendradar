# 舆情快报 (TrendRadar)

零服务器、纯云端运行的舆情监控系统。基于 GitHub Actions 定时爬取 13 个平台热搜/热榜，通过钉钉推送到群聊或个人 IM。整合 BettaFish (微舆) 的 newsnow 聚合 API 和多 Agent 分析思路。

## 架构

```
舆情快报/
├── main.py                          # 主程序：爬取 → 去重 → 格式化 → AI 分析 → 推送
├── crawlers/                        # 爬虫模块（每个返回 list[dict]）
│   ├── _common.py                   #   共享 HTTP headers / User-Agent
│   ├── newsnow.py                   #   newsnow.busiyi.world 统一聚合客户端（10 源在用）
│   ├── retry.py                     #   指数退避重试逻辑（参考 BettaFish）
│   ├── weibo.py                     #   微博热搜 — Web AJAX + 移动端双 API ✅
│   ├── zhihu.py                     #   知乎热榜 — api.zhihu.com + newsnow 回退 ✅
│   ├── baidu.py                     #   百度热搜 — top.baidu.com 递归解析 ✅
│   ├── douyin.py                    #   抖音热点 — newsnow 聚合 ✅
│   ├── wechat.py                    #   微信热文 — 已从管道移除（newsnow+vvhan 均不稳定）
│   └── kuaishou.py                  #   快手热门 — 已从管道移除（同上）
├── analyst/                         # AI 分析（可选，env-gated）
│   └── summarizer.py                #   OpenAI 兼容 LLM 跨平台趋势洞察
├── notifier/dingtalk.py             # 钉钉推送 — 群机器人 webhook（方案A）+ 工作通知（方案B）
├── scripts/
│   ├── test_push.py                 #   验证工作通知配置
│   └── lookup_user.py              #   通过手机号查 userId
├── .github/workflows/crawl.yml      # 定时任务（每天 UTC 1:00 = 北京时间 9:00）
├── BettaFish/                       # BettaFish v3.0.0 参考项目（git submodule，见下文）
└── data/                            # 爬取数据存档（每次运行 git commit）
    ├── latest.json                  #   最新结果（用于去重比对）
    └── archive/                     #   历史快照 {timestamp}.json
```

## 当前活跃的 13 个平台

| # | 平台 | source_id | 数据来源 |
|---|------|-----------|----------|
| 1 | 微博热搜 | `weibo` | 直接 API（Web AJAX → 移动端回退） |
| 2 | 知乎热榜 | `zhihu` | 直接 API → newsnow 回退 |
| 3 | 百度热搜 | `baidu` | 直接 API（top.baidu.com） |
| 4 | 抖音热点 | `douyin` | newsnow 聚合 |
| 5 | B站热搜 | `bilibili` | newsnow 聚合 |
| 6 | 今日头条 | `toutiao` | newsnow 聚合 |
| 7 | 百度贴吧 | `tieba` | newsnow 聚合 |
| 8 | 澎湃新闻 | `thepaper` | newsnow 聚合 |
| 9 | 华尔街见闻 | `wallstreetcn` | newsnow 聚合 |
| 10 | 财联社 | `cls` | newsnow 聚合 |
| 11 | 雪球热榜 | `xueqiu` | newsnow 聚合 |
| 12 | GitHub趋势 | `github` | newsnow 聚合 |
| 13 | 酷安热榜 | `coolapk` | newsnow 聚合 |

微信和快手的爬虫代码保留在 `crawlers/wechat.py` 和 `crawlers/kuaishou.py`，但因缺乏稳定 API 已从 `main.py` 管道中注释掉。

## 数据流

```
GitHub Actions cron (每天 9:00 CST) / workflow_dispatch 手动触发
  → 13 个爬虫顺序抓取 TOP 10（带指数退避重试）
  → 对比 data/latest.json 去重（按 title 匹配）
  → 生成 Markdown 报告（概览 + 跨平台 TOP 5 + 各平台详情）
  → (可选) LLM AI 跨平台洞察
  → 钉钉推送：优先工作通知（方案B），否则 webhook（方案A），都没有则仅打印预览
  → 数据写回 data/ → git commit → git push
```

## 运行方式

```bash
# 本地测试 — 爬取 + 打印预览（不推送）
python main.py

# 方案A: 群机器人 webhook（推荐，配置最简单）
export DINGTALK_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=..."
export DINGTALK_SECRET="SEC..."           # 可选，如果机器人设置了加签
python main.py

# 方案B: 工作通知推送到个人 IM
export DINGTALK_APP_KEY=...
export DINGTALK_APP_SECRET=...
export DINGTALK_AGENT_ID=...
export DINGTALK_USER_IDS=...
python main.py

# 验证方案B配置
export DINGTALK_APP_KEY=... DINGTALK_APP_SECRET=... \
       DINGTALK_AGENT_ID=... DINGTALK_USER_IDS=...
python scripts/test_push.py
```

## 环境变量

### 方案A — 群机器人 webhook（推荐）

| 变量 | 必需 | 用途 |
|------|------|------|
| `DINGTALK_WEBHOOK_URL` | ✅ | 群机器人 Webhook 地址 |
| `DINGTALK_SECRET` | 可选 | 机器人加签密钥（如未设置加签可不填） |

### 方案B — 工作通知（个人推送）

| 变量 | 必需 | 用途 |
|------|------|------|
| `DINGTALK_APP_KEY` | ✅ | 企业应用 AppKey（Client ID） |
| `DINGTALK_APP_SECRET` | ✅ | 企业应用 AppSecret（Client Secret） |
| `DINGTALK_AGENT_ID` | ✅ | 企业应用 AgentId |
| `DINGTALK_USER_IDS` | ✅ | 推送目标 userId，多个逗号分隔 |

> 两种方案同时配置时，优先使用方案 B（工作通知）。如果在 GitHub Actions 中运行，对应变量设为 GitHub Secrets。

### 可选配置

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `TREND_LLM_API_KEY` | (空) | LLM API Key，设置后启用 AI 跨平台洞察 |
| `TREND_LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容 API 地址（**需在 GitHub Secrets 中显式设置**） |
| `TREND_LLM_MODEL` | `deepseek-chat` | 模型名（使用 DeepSeek V4 时设为 `deepseek-v4-pro`） |
| `TREND_LLM_MAX_TOKENS` | `2000` | LLM 最大输出 token（推理模型需 ≥2000，否则内部思维链耗尽配额） |
| `CRAWLER_MAX_RETRIES` | `3` | 爬虫失败重试次数（0=不重试） |
| `CRAWLER_RETRY_DELAY` | `1.0` | 重试初始延迟（秒），指数退避 |

> **DeepSeek V4 注意**：V4 Pro 为推理模型，内部会消耗 token 做思维链。`analyst/summarizer.py` 中 `max_tokens` 已设为 `2000`（V4 flash 用 `500` 即可）。若切换模型后洞察为空，检查该参数是否需要调整。

## 设计决策

- **不依赖浏览器**：所有爬虫纯 HTTP 请求，适合 GitHub Actions 无头环境
- **独立模块**：每个爬虫文件独立，单个 API 挂了只影响一个源，互不干扰
- **去重机制**：每次对比上一次 `data/latest.json`，已有标题不重复推送
- **双重推送**：优先工作通知（方案B），未配置则回退群机器人 webhook（方案A）
- **指数退避重试**：爬虫调用自动重试（默认 3 次），避免瞬时网络抖动误报
- **AI 可选降级**：LLM API Key 未配置或调用失败时静默跳过，报告保持原有格式。使用推理模型（如 DeepSeek V4 Pro）时注意 `max_tokens` 需足够大（≥2000），否则内部推理会耗尽 token 配额导致输出为空
- **微信/快手已移除**：两个模块代码保留但未接入管道。newsnow 上这两个源的稳定性差，vvhan.com 域名也已失效
- **BettaFish 参考**：`BettaFish/` 是 git submodule，指向微舆 v3.0.0 完整项目。newsnow 聚合客户端、重试逻辑和 AI 分析 Prompt 均参考其 `MindSpider/` 和 `utils/` 设计。BettaFish 需要 PostgreSQL + 多个 LLM API，不适合 GitHub Actions 轻量运行，仅作为模块参考

## 已知问题

- **GitHub Secrets 空字符串陷阱**：workflow 中引用未配置的 Secret（如 `${{ secrets.X }}`）会注入空字符串环境变量。代码中 `os.environ.get("X", default)` 因 key 存在（值为空）返回空字符串而非 default。必须使用 `os.environ.get("X") or default` 模式。`crawlers/retry.py` 和 `analyst/summarizer.py` 已统一采用此模式
- **Rebase 冲突 — data/latest.json**：两次 workflow 运行时间重叠时（如 cron + workflow_dispatch 相邻触发），`git pull --rebase` 会因两地都修改了 `latest.json` 而冲突。已添加 `|| { git checkout --theirs data/latest.json; git add data/latest.json; git rebase --continue; }` 自动用本地最新数据覆盖。注意 rebase 中 `--theirs` 指向正在 rebase 的本地 commit（新数据），`--ours` 指向目标分支（远端旧数据），与 merge 时相反
- GitHub Actions cron 调度偶尔会跳过触发（尤其大量 workflow_dispatch 手动调试后），代码/配置没问题时观察次日是否恢复
- 知乎直接 API 在某些网络环境下返回 401（需认证），已添加 newsnow 回退
- 百度 API 数据结构使用嵌套 `cards[0].content[0].content[...]`，已通过递归解析适配
- vvhan、imsyy、tenapi 等免费热搜聚合器已于 2025-2026 年停止服务
- GitHub Actions runner 在境外，部分中国网站可能限速或拒绝连接
- 华尔街见闻 (newsnow) 某些条目将多条快讯合并为超长标题，已添加 120 字符截断

## 修改定时频率

编辑 `.github/workflows/crawl.yml` 中的 `cron` 字段（UTC 时间）：

```yaml
schedule:
  - cron: "0 1 * * *"       # 每天 UTC 1:00 = 北京时间 9:00
  # - cron: "0 1,13 * * *"  # 每天两次：9:00 和 21:00
  # - cron: "*/30 * * * *"  # 每 30 分钟
```

cron 格式：`分 时 日 月 周`（UTC）。也可通过 GitHub Actions 页面手动触发（workflow_dispatch）。
