# 舆情快报 (TrendRadar)

零服务器、纯云端运行的舆情监控系统。基于 GitHub Actions 定时爬取 13 大中文平台热搜，通过钉钉工作通知推送到个人 IM。整合 BettaFish (微舆) 的聚合 API 和多 Agent 分析思路。

## 架构

```
舆情快报/
├── main.py                          # 主程序：爬取 → 去重 → 格式化 → AI 分析 → 推送
├── crawlers/                        # 爬虫模块（每个返回 list[dict]）
│   ├── _common.py                   #   共享 HTTP headers
│   ├── newsnow.py                   #   newsnow.busiyi.world 统一聚合客户端（12源）
│   ├── retry.py                     #   指数退避重试逻辑
│   ├── weibo.py                     #   微博热搜 — 移动端 API ✅
│   ├── zhihu.py                     #   知乎热榜 — api.zhihu.com + newsnow 回退 ✅
│   ├── baidu.py                     #   百度热搜 — top.baidu.com ✅
│   ├── douyin.py                    #   抖音热点 — newsnow 聚合 ✅
│   ├── wechat.py                    #   微信热文 — ⚠️ 已移除（无可用 API）
│   └── kuaishou.py                  #   快手热门 — ⚠️ 已移除（无可用 API）
├── analyst/                         # AI 分析（可选，env-gated）
│   └── summarizer.py                #   LLM 跨平台趋势洞察
├── notifier/dingtalk.py             # 钉钉推送（工作通知 + webhook 回退）
├── scripts/
│   ├── test_push.py                 # 本地验证钉钉配置
│   └── lookup_user.py              # 通过手机号查 userId
├── .github/workflows/crawl.yml      # 定时任务（每天 UTC 1:00 = 北京时间 9:00）
├── BettaFish/                       # BettaFish 参考项目（微舆，见下文）
└── data/                            # 爬取数据存档（每次运行 git commit）
    ├── latest.json                  # 最新结果（用于去重）
    └── archive/                     # 历史快照
```

## 数据流

```
GitHub Actions cron (每天 9:00 CST)
  → 13 个爬虫顺序抓取 TOP 10（带指数退避重试）
  → 对比 data/latest.json 去重
  → 生成 Markdown 报告（概览 + 跨平台 TOP 5 + 各平台详情）
  → (可选) LLM AI 跨平台洞察
  → 钉钉工作通知（方案B）或群机器人（方案A）
  → 数据写回 data/ → git commit → git push
```

## 运行方式

```bash
# 本地测试（不推送，仅打印预览）
python main.py

# 完整运行（需要环境变量）
DINGTALK_APP_KEY=xxx \
DINGTALK_APP_SECRET=xxx \
DINGTALK_AGENT_ID=xxx \
DINGTALK_USER_IDS=xxx \
python main.py

# 验证钉钉配置
DINGTALK_APP_KEY=xxx DINGTALK_APP_SECRET=xxx \
DINGTALK_AGENT_ID=xxx DINGTALK_USER_IDS=xxx \
python scripts/test_push.py
```

## 必需的环境变量

| 变量 | 用途 |
|------|------|
| `DINGTALK_APP_KEY` | 钉钉企业应用 AppKey |
| `DINGTALK_APP_SECRET` | 钉钉企业应用 AppSecret |
| `DINGTALK_AGENT_ID` | 钉钉企业应用 AgentId |
| `DINGTALK_USER_IDS` | 推送目标 userId，多个逗号分隔 |

回退方案（群机器人）：设置 `DINGTALK_WEBHOOK_URL` 即可。

## 可选环境变量

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `CRAWLER_MAX_RETRIES` | `3` | 爬虫失败重试次数（0=不重试） |
| `CRAWLER_RETRY_DELAY` | `1.0` | 重试初始延迟（秒） |
| `TREND_LLM_API_KEY` | (空) | LLM API Key，设置后启用 AI 跨平台洞察 |
| `TREND_LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容 API 地址 |
| `TREND_LLM_MODEL` | `deepseek-chat` | 模型名 |

## 设计决策

- **不依赖浏览器**：所有爬虫纯 HTTP 请求，适合 GitHub Actions 无头环境
- **独立模块**：每个爬虫文件独立，API 挂了只影响单个源，互不干扰
- **去重机制**：每次对比上一次 `latest.json`，只推送新增/变化的热搜
- **双重推送**：优先工作通知（方案B），检测不到则回退群机器人（方案A）
- **指数退避重试**：爬虫调用自动重试 3 次（可配置），避免瞬时网络抖动误报
- **AI 可选降级**：LLM API Key 未配置或调用失败时静默跳过，报告保持原有格式
- **微信/快手**：已移除。两个平台均无公开 API，且 vvhan.com 域名已失效（DNS 无法解析）
- **BettaFish 参考**：`BettaFish/` 目录含完整的多 Agent 舆情分析系统（微舆 v3.0.0），newsnow 聚合客户端和重试逻辑均参考其设计。BettaFish 需 PostgreSQL + 多个 LLM API，不适合 GitHub Actions 轻量运行，仅作为模块参考

## 已知问题

- 知乎直接 API 已返回 401（需认证），已添加 newsnow 回退方案
- 百度 API 数据结构更新为嵌套 `cards[0].content[0].content[...]`，已通过递归解析适配
- vvhan、imsyy、tenapi 等免费聚合器已停止服务（2025-2026）
- GitHub Actions runner 在境外，部分中国网站可能限速或拒绝连接
- 华尔街见闻(newsnow)某些条目会将多条快讯合并为超长标题，已添加 120 字符截断

## 修改定时频率

编辑 `.github/workflows/crawl.yml` 中的 `cron` 字段（UTC 时间）：

```yaml
schedule:
  - cron: "0 1 * * *"       # 每天 UTC 1:00 = 北京时间 9:00
  # - cron: "0 1,13 * * *"  # 每天两次：9:00 和 21:00
  # - cron: "*/30 * * * *"  # 每 30 分钟
```

cron 格式：`分 时 日 月 周`（UTC）
