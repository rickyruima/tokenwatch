# PRD：AI Cost Anomaly Detection (Local-First)

**产品代号**：TokenWatch
**版本**：v1.0
**作者**：Ricky
**最后更新**：2026-05

---

## 1. 一句话定位

> **htop for LLM spend. See where your tokens go, catch anomalies before they drain your wallet.**

为开发者提供 LLM token 消耗的本地异常检测和归因——零基础设施、零账号注册、`pip install` 即用。

---

## 2. 问题陈述

### 2.1 用户痛点

LLM 账单失控的故事在每个工程团队都在发生：
- 月账单从 $1k 涨到 $50k，没人知道原因
- agent 进入死循环重试，一夜烧 $20k
- 一个用户写 prompt injection 让 system prompt 重复展开
- retrieval 系统改了 chunk size，每次请求 token 翻 5 倍
- 模型升级（gpt-4 → gpt-4-turbo）后，单价 + 实际行为变化导致总成本不可预测

**核心问题**：
- LLM provider 的 dashboard（OpenAI / Anthropic）只显示总量，**没有归因**
- 公司不知道每个 customer / feature / endpoint 花了多少
- 异常发生时没有告警，等月底账单才发现
- 即使发现了，trace 不到根因（哪个 prompt？哪个 user？哪个时间点开始的？）

### 2.2 当前缓解方案的不足

- **OpenAI / Anthropic Dashboard**：聚合数据、没维度、无告警
- **Datadog / New Relic**：在做 LLM monitoring，但聚焦在 latency / errors，cost 是 afterthought
- **LangSmith / Helicone**：偏向 trace / debug，cost 维度浅、需要注册 SaaS 账号
- **自建 logging**：每家公司重新发明轮子，且通常做得不好

### 2.3 为什么 Local-First

| 维度 | SaaS 方案 | TokenWatch Local-First |
|------|----------|----------------------|
| 信任 | 数据发到第三方 | 数据永远在你机器上 |
| 成本 | $99-$1999/mo | 免费 |
| 隐私 | 需要签 DPA | 无隐私顾虑 |
| 延迟 | 网络 I/O | 本地磁盘 |
| 依赖 | 服务挂了就没数据 | 无外部依赖 |
| 接入 | 注册 → API key → 配置 | `pip install tokenwatch` |

**用户更信任本地工具。成本更低。上手更快。**

### 2.4 用户画像

**核心用户**：
- 独立开发者 / 小团队，用 LLM API 构建产品
- LLM 月支出 $100-$10k
- 想了解钱花在哪里，但不想注册另一个 SaaS
- 偏好 CLI / 终端工作流

**扩展用户**：
- Engineering leader / staff engineer（月支出 > $5k）
- 需要 chargeback 数据的平台团队

---

## 3. 解决方案

### 3.1 架构概览

```
Your app code
    │
    ▼
tokenwatch SDK (Python)  ←  wrap OpenAI/Anthropic client
    │
    ▼
~/.tokenwatch/usage.db   ←  本地 SQLite (DuckDB optional)
    │
    ▼
tw CLI                   ←  报告、告警、查询
```

**核心原则**：
- 数据永远留在本地
- 零网络依赖（SDK 不做任何网络调用）
- 单文件数据库，可以 git / rsync / 备份
- CLI-first，TUI 可选

### 3.2 接入方式

```python
from tokenwatch import TokenWatch
import openai

tw = TokenWatch()  # 无需 API key，数据存本地

# 包装现有 client
client = tw.wrap(openai.OpenAI())

response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    metadata={  # 业务维度标签
        "customer_id": "cust_123",
        "feature": "summarization",
        "endpoint": "/api/summarize",
    }
)
# 自动记录 tokens、cost、metadata 到本地 DB
```

### 3.3 核心功能

#### 3.3.1 CLI 报告

```bash
# 今日花费概览
$ tw report
Today: $42.13 (↑12% vs yesterday)
  gpt-4-turbo   $28.40  (67%)
  claude-3-opus  $11.20  (27%)
  gpt-3.5        $2.53  (6%)

# 按维度切分
$ tw top --by customer_id --period 7d
  cust_xyz789   $312.40  (47 requests, avg 8400 tokens)
  cust_abc456    $89.10  (12 requests, avg 12000 tokens)
  ...

# 按 feature 看趋势
$ tw trend --by feature --period 30d

# 单次请求分布
$ tw outliers --period 24h
```

#### 3.3.2 异常检测

```bash
# 一次性检查
$ tw check
🚨 Spike: feature=agent_chat cost $312 in last hour (baseline: $42, +643%)
   Top contributor: customer_id=cust_xyz789 (47x normal volume)
   Likely cause: retry loop (152 similar requests in 1h)

⚠️  Trend: model=gpt-4-turbo daily cost up 180% over 7 days

✅ No outlier requests detected

# 守护进程模式（持续监控）
$ tw watch --interval 5m --alert slack
```

**检测算法（v1，纯统计）**：
- **Spike detection**：滑动窗口 baseline（过去 7 天同时段），当前值 > baseline + 3σ → 触发
- **Outlier detection**：单次请求 tokens > p99（按 endpoint 分组）
- **Loop detection**：同一 customer + 相似 prompt hash 短时间内 > N 次
- **Trend deviation**：偏离过去 4 周同期 > 30%

#### 3.3.3 预算与告警

```yaml
# ~/.tokenwatch/config.yaml
budgets:
  - name: "Daily total"
    daily_limit_usd: 100
    action: alert

  - name: "Per-customer cap"
    dimension: customer_id
    daily_limit_usd: 50
    action: alert

  - name: "Feature: agent"
    dimension: feature
    value: "agent"
    daily_limit_usd: 30
    action: alert

alerts:
  slack:
    webhook: https://hooks.slack.com/...
  desktop: true  # macOS notification
  stdout: true   # 终端输出
```

#### 3.3.4 数据查询

```bash
# SQL 直接查本地 DB
$ tw query "SELECT feature, SUM(cost_usd) FROM events WHERE date > '2026-05-01' GROUP BY feature"

# 或 Python API
from tokenwatch import TokenWatch
tw = TokenWatch()
results = tw.query(
    metric="total_cost",
    group_by=["customer_id", "feature"],
    period="7d",
    order_by="total_cost desc",
    limit=20
)
```

#### 3.3.5 TUI Dashboard（可选）

```bash
$ tw dashboard
# 用 textual/rich 渲染终端 dashboard
# 实时刷新、可交互、键盘导航
```

### 3.4 关键设计决策

**为什么 SQLite 而不是 ClickHouse**：
- 单文件，零运维
- 对于单机数据量（< 100M rows/year 对大多数用户），SQLite 足够快
- DuckDB 作为可选后端，处理分析查询更快

**为什么不需要 API key**：
- 数据留本地，不需要身份验证
- 开箱即用，零 friction

**为什么 CLI-first 而非 Web**：
- 目标用户（开发者）住在终端
- 不需要运行 web server
- TUI 可以做到 dashboard 80% 的功能
- 未来可以加 `tw serve` 起本地 web UI

**为什么不做实时拦截**：
- SDK 是观察者，不是 gatekeeper
- 拦截需要 proxy 模式，增加复杂度
- v1 告警足够

---

## 4. v1.0 Scope

### 4.1 In Scope

- **Python SDK**（`pip install tokenwatch`）：wrap OpenAI / Anthropic client
- **本地 SQLite 存储**：~/.tokenwatch/usage.db
- **CLI 工具**：report, top, trend, outliers, check, watch, query
- **异常检测**：spike + outlier + loop detection（纯统计）
- **告警**：Slack webhook + desktop notification + stdout
- **基础预算**：daily limit per dimension
- **配置**：~/.tokenwatch/config.yaml
- **TUI dashboard**：用 textual 实现终端仪表盘

### 4.2 Out of Scope（v1 明确不做）

- ❌ Node.js / Go SDK（v1.5）
- ❌ Web UI（v2，`tw serve` 起本地 Flask/FastAPI）
- ❌ 云同步 / 团队共享（v2，opt-in `tw sync`）
- ❌ 实时拦截 / hard block（v2）
- ❌ ML-based 异常检测（v2，v1 用统计）
- ❌ 自动优化建议（v2）
- ❌ Azure / Bedrock / Gemini 支持（v1.5）

### 4.3 显式非目标

**TokenWatch 不是**：
- 不是 LLM tracing 工具（LangSmith 在做）
- 不是通用 APM（Datadog 在做）
- 不是 SaaS platform（数据不离开你的机器）
- 不是 model router

**TokenWatch 只解决一件事：本地 cost anomaly detection + attribution**。

---

## 5. 技术架构

### 5.1 技术栈

- **SDK**：Python（httpx-free，纯标准库 + pydantic）
- **存储**：SQLite（标准库 sqlite3），DuckDB 可选
- **异常检测**：Python + 简单统计（z-score、EWMA、percentile）
- **CLI**：click + rich
- **TUI**：textual（可选依赖）

### 5.2 数据模型

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,       -- openai, anthropic
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms INTEGER,
    metadata JSON,               -- {"customer_id": "...", "feature": "..."}
    prompt_hash TEXT             -- 用于 loop detection
);

CREATE INDEX idx_timestamp ON events(timestamp);
CREATE INDEX idx_model ON events(model);
CREATE INDEX idx_cost ON events(cost_usd);
```

### 5.3 SDK 设计

```python
from tokenwatch import TokenWatch

tw = TokenWatch(
    db_path="~/.tokenwatch/usage.db",  # 可自定义
    config_path="~/.tokenwatch/config.yaml",
)

# Wrap 模式（推荐）
client = tw.wrap(openai.OpenAI())

# 手动记录模式（任何 provider）
tw.record(
    provider="anthropic",
    model="claude-3-opus",
    input_tokens=1234,
    output_tokens=567,
    cost_usd=0.0421,
    metadata={"feature": "chat"}
)
```

### 5.4 项目结构

```
tokenwatch/
├── pyproject.toml
├── src/tokenwatch/
│   ├── __init__.py          # TokenWatch 主类
│   ├── wrapper.py           # OpenAI/Anthropic client wrapper
│   ├── storage.py           # SQLite 存储层
│   ├── pricing.py           # 模型价格表（本地 JSON）
│   ├── anomaly/
│   │   ├── __init__.py
│   │   ├── spike.py         # Spike detection
│   │   ├── outlier.py       # Outlier detection
│   │   ├── loop.py          # Loop detection
│   │   └── trend.py         # Trend deviation
│   ├── alert/
│   │   ├── __init__.py
│   │   ├── slack.py         # Slack webhook
│   │   └── desktop.py       # macOS notification
│   └── cli/
│       ├── __init__.py
│       ├── report.py        # tw report
│       ├── top.py           # tw top
│       ├── check.py         # tw check
│       ├── watch.py         # tw watch (daemon)
│       ├── query.py         # tw query
│       └── dashboard.py     # tw dashboard (TUI)
├── tests/
└── pricing/
    └── models.json          # 各模型单价
```

### 5.5 性能要求

- SDK record() < 1ms（SQLite write，异步可选）
- CLI report 查询 < 500ms（百万行级别）
- 异常检测 check < 2s
- 数据库文件大小：~100 bytes/event，1M events ≈ 100MB

---

## 6. 用户旅程

### 6.1 30 秒接入

```bash
pip install tokenwatch
```

```python
from tokenwatch import TokenWatch
import openai

tw = TokenWatch()
client = tw.wrap(openai.OpenAI())

# 正常使用，自动记录
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    metadata={"feature": "chat"}
)
```

### 6.2 第一天

```bash
$ tw report
Today: $3.42 (23 requests)
  gpt-4    $2.80 (12 requests)
  gpt-3.5  $0.62 (11 requests)

$ tw top --by feature
  chat          $2.10
  summarize     $1.32
```

### 6.3 异常发生时

```bash
$ tw check
🚨 Spike: feature=agent_chat cost $312 in last hour (baseline: $42, +643%)
   Top contributor: customer_id=cust_xyz789 (47x normal volume)
   Likely cause: retry loop (152 similar requests in 1h)
   Suggested action: Check agent retry logic for cust_xyz789
```

或配置 `tw watch` 后台运行，自动发 Slack / desktop notification。

### 6.4 周报

```bash
$ tw report --period 7d --format markdown
# 输出 markdown 格式周报，可以直接贴 Slack / Notion
```

---

## 7. 商业模式

### 7.1 开源 + 可选付费

**核心工具完全免费开源**（MIT license）。

**可选付费方向（v2+）**：
- `tw sync` — 团队云同步（$19/mo per workspace）
- `tw dashboard --web` — hosted web UI
- Enterprise support

**为什么开源**：
- 开发者工具必须 trust-first
- 本地工具靠 distribution 而非 lock-in
- 开源建社区 → 社区贡献 provider adapter
- 靠 adoption 建 brand，付费转化自然发生

### 7.2 GTM 策略

- 写 "Why your LLM bill is out of control" blog post
- 在 Hacker News / Reddit 发布
- GitHub trending
- LangChain / LlamaIndex 集成示例
- 目标：6 个月 5k GitHub stars，1k weekly active installs

---

## 8. 成功指标

### 8.1 v1 发布指标（前 90 天）

| 指标 | 目标 |
|------|------|
| PyPI 安装量 | 5000+ |
| GitHub stars | 2000+ |
| Weekly active users (CLI usage) | 500+ |
| 社区 PR | 10+ |

### 8.2 北极星指标

**"Weekly active `tw check` users"** — 每周主动用异常检测的人数。说明用户真的依赖这个工具。

---

## 9. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| OpenAI / Anthropic 自建 cost breakdown | 高 | 中 | 他们做 single-vendor，我们做 cross-vendor + 自定义维度归因 |
| 用户不愿加 metadata 标签 | 中 | 高 | 提供 auto-infer（从 call stack / file path 自动打标） |
| SQLite 在高并发写入时有限制 | 低 | 中 | WAL mode + batch writes，或切 DuckDB |
| 模型价格变动频繁 | 高 | 低 | pricing/models.json 可自动更新，CLI `tw pricing update` |
| 竞品（Helicone / LangSmith）加本地模式 | 低 | 中 | 我们 local-native，他们 SaaS-with-local-mode，体验不同 |

---

## 10. 时间线

| 阶段 | 时间 | 里程碑 |
|------|------|--------|
| **v0.1** | 第 1 月 | SDK (OpenAI wrap) + SQLite storage + `tw report` |
| **v0.5** | 第 2 月 | Anthropic 支持 + 异常检测 + `tw check` + `tw watch` |
| **v1.0** | 第 3 月 | TUI dashboard + 完整 CLI + config + Slack alert + 开源发布 |
| **v1.5** | 第 4-6 月 | DuckDB backend + more providers + auto-tagging |
| **v2.0** | 第 7-9 月 | `tw sync`（团队版）+ web UI + ML anomaly |

---

## 11. Open Questions

1. 是否要支持 `TOKENWATCH_DB` 环境变量让 CI/CD 也能用？
2. auto-tagging（从 call stack 自动推断 feature 名）技术上可行性？用 `inspect` 模块？
3. pricing/models.json 的更新策略：内置 + CLI 更新 vs. 每次自动 fetch？（本地优先 → 内置 + 手动更新）
4. 是否提供 pytest plugin（`--tokenwatch` flag 自动记录测试中的 LLM 调用成本）？
5. DuckDB vs SQLite 默认选哪个？SQLite 零依赖但分析慢，DuckDB 分析快但多一个依赖。
