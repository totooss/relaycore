# EchoMemory Cross-AI-Agent Control Plane 构建蓝图（无 Obsidian 版）

> 版本：v0.3.0  
> 范围：本蓝图**不考虑 Obsidian 接入**。EchoMemory 的核心目标是服务 AI Agent 执行，而不是做人类 Markdown 知识库。  
> 目标：把 EchoMemory 从“多 Agent 共享记忆库”升级为“跨 AI Agent 的统一长期记忆、命令总线、事件日志、记忆质量治理、低 token 检索与协同控制框架”。

---

## 0. 定位

EchoMemory 的核心不是普通笔记系统，也不是给人阅读的 PKM，而是：

```text
Cross-AI-Agent Runtime Context Infrastructure
```

它应服务于：

- Claude Code
- Codex CLI
- Cursor
- Kiro
- Gemini CLI
- Generic MCP-compatible Agents

核心能力：

1. 跨 AI Agent 共享长期记忆。
2. 让 Agent 默认使用 EchoMemory，而不是只使用自己的原生 memory。
3. 多 Agent 可协作、评审、对抗、流水线执行。
4. HTML/CLI 可发布结构化命令。
5. 所有执行过程写入 append-only event log。
6. 记忆写入时去重、纠错、合并、冲突检测。
7. 检索时只返回摘要、ID、相关性理由和必要 rejected，避免 token 膨胀。
8. rejected 是一等公民，防止 Agent 重复建议已否决方案。

---

## 1. 当前 EchoMemory 优势

EchoMemory 已有的核心基础：

- SQLite + FTS5，适合轻量部署和全文检索。
- REST API、MCP Server、CLI 三种接入方向。
- 七类知识：decision、lesson、process、insight、rule、reference、contact。
- rejected 字段，适合记录被否决方案。
- Agent 身份认证方向，适合追踪不同 Agent 写入来源。
- Web UI 已有雏形，可演进为 Mission Control。

---

## 2. 设计原则

### 2.1 不统一 Agent 内部上下文，只统一外部事实

不要试图让 Claude Code 读取 Codex 的内部上下文，也不要让 Codex 直接读取 Claude Code 的私有会话状态。EchoMemory 只统一：

```text
长期记忆
任务命令
执行事件
协作模式
审计记录
```

### 2.2 EchoMemory 是唯一长期记忆源

Agent 原生 memory 只作为短期 scratchpad。任何长期有效的：

- 决策
- 规则
- 教训
- 用户/项目偏好
- rejected 方案
- 跨 Agent 结论

都必须进入 EchoMemory。

### 2.3 运行时默认低 token

默认只返回：

```text
summary + id + why_relevant + rejected summary + expand handle
```

不默认返回：

- 完整 Skill 文档
- 完整 memory content
- 完整 event timeline
- 完整工具日志
- 完整 diff

### 2.4 所有协作行为 append-only

多 Agent 不直接抢写同一个共享状态对象。所有行为写入 `agent_events`：

- proposal
- critique
- revision
- approval
- rejection
- command status
- memory write
- tool summary

### 2.5 HTML 只发布结构化 Agent Command

HTML Mission Control 不是远程 shell。它只发布结构化命令，由目标 Agent Runtime 自行执行，并遵循权限等级。

---

## 3. 总体架构

```text
                 ┌──────────────────────────────┐
                 │      HTML Mission Control     │
                 │ Session / Mode / Command      │
                 │ Event Timeline / Memory Queue │
                 └───────────────┬──────────────┘
                                 │ REST / SSE
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                       EchoMemory Server                      │
│                                                              │
│ ┌─────────────┐ ┌─────────────┐ ┌──────────────────────────┐ │
│ │ Memory API  │ │ Command Bus │ │ Event Stream / SSE       │ │
│ └──────┬──────┘ └──────┬──────┘ └───────────┬──────────────┘ │
│        │               │                    │                │
│ ┌──────▼───────────────▼────────────────────▼──────────────┐ │
│ │ SQLite Storage                                           │ │
│ │ knowledge / relations / sessions / commands / events      │ │
│ │ digests / clusters / candidates / audit_logs / artifacts  │ │
│ │ WAL + FTS5 + indexes                                      │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ EchoMemory MCP Server                                    │ │
│ │ memory_context / memory_propose / command_poll / events   │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Memory Quality Pipeline                                  │ │
│ │ normalize / dedupe / merge / correct / conflict / rerank  │ │
│ └───────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
           ▲                              ▲
           │ MCP + Hooks + CLI            │ MCP + Hooks + CLI
           │                              │
┌──────────▼───────────┐        ┌─────────▼──────────┐
│ Claude Code Adapter   │        │ Codex CLI Adapter  │
│ CLAUDE.md / Hooks     │        │ AGENTS.md / Hooks  │
│ claude mcp add        │        │ codex mcp add      │
└──────────────────────┘        └────────────────────┘
```

---

## 4. 推荐目录结构

```text
EchoMemory/
├── AGENTS.md
├── CLAUDE.md
├── docs/
│   ├── ECHOMEMORY_CROSS_AGENT_BUILD.md
│   ├── ECHOMEMORY_RUNTIME_CONTRACT.md
│   ├── ECHOMEMORY_TOKEN_POLICY.md
│   ├── ECHOMEMORY_MEMORY_QUALITY.md
│   ├── ECHOMEMORY_EXTERNAL_REFERENCES.md
│   └── ECHOMEMORY_SECURITY_MODEL.md
├── .claude/
│   └── skills/
│       └── echomemory-cross-agent/
│           └── SKILL.md
├── .codex/
│   ├── config.toml
│   └── hooks.json
├── echomemory/
│   ├── storage.py
│   ├── server.py
│   ├── mcp_server.py
│   ├── command_bus.py
│   ├── event_log.py
│   ├── memory_quality.py
│   ├── token_budget.py
│   ├── runtime_adapters.py
│   ├── web_ui.py
│   └── migrations.py
└── tests/
    ├── test_memory_quality.py
    ├── test_command_bus.py
    ├── test_event_log.py
    ├── test_mcp_tools.py
    └── test_web_ui.py
```

---

## 5. Runtime Contract

运行时只加载短协议，不加载完整蓝图。

```markdown
# EchoMemory Runtime Contract

EchoMemory is the only long-term memory backend.

Before work:
1. Call `memory_begin_task`.
2. Call `memory_context` with `max_tokens <= 1200`.
3. Read active decisions, rules, lessons, and relevant rejected options.

During work:
1. Append important events only with `agent_event_append`.
2. Poll commands with `command_poll` when in managed session.
3. Follow assigned mode: assist, review, adversarial, debate, or pipeline.

Before stop:
1. Call `memory_commit_task`.
2. Save durable decisions and rejected options.
3. Do not store long-term memory only in native agent memory.

If EchoMemory is unavailable, report:
"EchoMemory unavailable, cannot persist long-term memory."
```

---

## 6. 数据库模型

### 6.1 sessions

```sql
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  goal TEXT NOT NULL,
  mode TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  metadata TEXT DEFAULT '{}'
);
```

### 6.2 commands

```sql
CREATE TABLE IF NOT EXISTS commands (
  command_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  target_agent TEXT,
  target_runtime TEXT,
  mode TEXT NOT NULL,
  command_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  priority INTEGER DEFAULT 100,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  claimed_by TEXT,
  claimed_at TEXT,
  lease_expires_at TEXT,
  completed_at TEXT,
  result TEXT DEFAULT '{}',
  idempotency_key TEXT,
  permission_level TEXT DEFAULT 'L1'
);
```

### 6.3 agent_events

```sql
CREATE TABLE IF NOT EXISTS agent_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  runtime TEXT,
  mode TEXT,
  event_type TEXT NOT NULL,
  content TEXT NOT NULL,
  command_id TEXT,
  parent_seq INTEGER,
  metadata TEXT DEFAULT '{}',
  created_at TEXT NOT NULL
);
```

### 6.4 agent_states

```sql
CREATE TABLE IF NOT EXISTS agent_states (
  agent_id TEXT PRIMARY KEY,
  runtime TEXT NOT NULL,
  session_id TEXT,
  role TEXT,
  status TEXT DEFAULT 'idle',
  last_seen_seq INTEGER DEFAULT 0,
  last_heartbeat TEXT,
  current_task TEXT,
  capabilities TEXT DEFAULT '[]',
  metadata TEXT DEFAULT '{}'
);
```

### 6.5 session_digests

```sql
CREATE TABLE IF NOT EXISTS session_digests (
  digest_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  from_seq INTEGER NOT NULL,
  to_seq INTEGER NOT NULL,
  summary TEXT NOT NULL,
  decisions TEXT DEFAULT '[]',
  open_questions TEXT DEFAULT '[]',
  rejected_candidates TEXT DEFAULT '[]',
  created_at TEXT NOT NULL
);
```

### 6.6 memory_candidates

```sql
CREATE TABLE IF NOT EXISTS memory_candidates (
  candidate_id TEXT PRIMARY KEY,
  proposed_by TEXT NOT NULL,
  runtime TEXT,
  session_id TEXT,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  summary TEXT DEFAULT '',
  rejected TEXT DEFAULT '[]',
  tags TEXT DEFAULT '[]',
  status TEXT DEFAULT 'pending',
  similar_to TEXT DEFAULT '[]',
  conflicts_with TEXT DEFAULT '[]',
  recommended_action TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  resolved_at TEXT
);
```

### 6.7 memory_occurrences

```sql
CREATE TABLE IF NOT EXISTS memory_occurrences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  runtime TEXT,
  session_id TEXT,
  observed_at TEXT NOT NULL,
  note TEXT DEFAULT ''
);
```

### 6.8 memory_clusters

```sql
CREATE TABLE IF NOT EXISTS memory_clusters (
  cluster_id TEXT PRIMARY KEY,
  canonical_memory_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  tags TEXT DEFAULT '[]',
  source_count INTEGER DEFAULT 1,
  quality_score REAL DEFAULT 0.5,
  updated_at TEXT NOT NULL,
  metadata TEXT DEFAULT '{}'
);
```

### 6.9 artifacts

```sql
CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  session_id TEXT,
  agent_id TEXT,
  kind TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  size_bytes INTEGER DEFAULT 0,
  summary TEXT DEFAULT '',
  created_at TEXT NOT NULL
);
```

### 6.10 audit_logs

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  request_id TEXT,
  ip TEXT,
  metadata TEXT DEFAULT '{}',
  created_at TEXT NOT NULL
);
```

### 6.11 SQLite PRAGMA

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
```

---

## 7. Memory Quality Pipeline

### 7.1 写入路径

```text
Agent proposes memory
      │
      ▼
Validate schema and type
      │
      ▼
Normalize title/content/tags/source/runtime
      │
      ▼
Generate summary and claims
      │
      ▼
Exact dedupe by content hash
      │
      ▼
Near dedupe by FTS5 + tags + title similarity
      │
      ▼
Conflict detection against active decisions/rules
      │
      ▼
Create candidate / merge / correct / supersede / active
      │
      ▼
Assign quality_score, confidence, cluster_id
      │
      ▼
Index and log audit
```

### 7.2 状态

```text
ephemeral    临时信息，只进 event
candidate    候选长期记忆，等待合并或确认
active       当前有效长期记忆
superseded   已被替代，但保留引用
archived     已归档，默认不检索
rejected     作为 decision 的 rejected 字段保存
```

### 7.3 去重阈值

```yaml
exact_hash_match: duplicate
similarity_gt_0_92: auto_merge
similarity_0_75_to_0_92: candidate_merge
similarity_lt_0_75: create_new
```

### 7.4 关系类型

```text
corrects
supersedes
conflicts_with
duplicates
merged_into
supports
weakens
```

高风险纠错只标记为 candidate，不自动覆盖。

---

## 8. 检索与 token 预算

### 8.1 默认预算

```text
Runtime Contract <= 800 tokens
CLAUDE.md supplement <= 500 tokens
MCP instructions <= 800 tokens
memory_context default <= 1200 tokens
command payload <= 500 tokens
event digest <= 1000 tokens
hook output <= 300 tokens
normal task overhead 2000–5000 tokens
multi-agent task overhead 8000–25000 tokens
```

### 8.2 Context Levels

```text
summary  默认，只返回摘要
detail   按 ID 展开选定条目
full     显式请求才返回全文
```

### 8.3 memory_context 默认响应

```json
{
  "max_items": 5,
  "max_tokens": 1200,
  "include_full_content": false,
  "return_cluster_summary": true,
  "include_rejected": "if_relevant"
}
```

### 8.4 检索评分

```text
score =
  0.35 * text_relevance
+ 0.20 * tag_overlap
+ 0.15 * confidence
+ 0.10 * freshness
+ 0.10 * source_trust
+ 0.05 * usage_count
+ 0.05 * relation_boost
- 0.30 * redundancy_penalty
- 0.50 * superseded_penalty
```

### 8.5 Event Digest

```text
每 10 条 event 或每 5 分钟生成 session_digest。
Agent 默认只接收最新 digest。
需要细节时调用 event_get(seq)。
```

---

## 9. Command Bus

### 9.1 状态机

```text
pending -> claimed -> running -> completed
pending -> rejected
running -> failed
running -> cancelled
claimed/running -> expired -> pending
```

### 9.2 租约机制

Agent claim command 后必须设置 `lease_expires_at`。如果 Agent 掉线或超时，命令回到 pending 或 failed。

### 9.3 权限等级

```text
L0: memory read
L1: memory write
L2: task command
L3: file edit
L4: shell command
L5: destructive command
```

L4/L5 默认需要 human approval。

---

## 10. Event Log

### 10.1 Event 类型

```text
task_started
memory_read
memory_proposed
memory_written
proposal
critique
revision
approval
rejection
command_created
command_claimed
command_completed
command_failed
tool_summary
artifact_created
final_summary
```

### 10.2 Event 内容原则

Event content 只存摘要，完整内容进入 artifact。

```json
{
  "event_type": "tool_summary",
  "content": "pytest failed: 3 auth refresh tests failed.",
  "metadata": {
    "artifact_id": "art_pytest_001",
    "exit_code": 1
  }
}
```

---

## 11. MCP Tools

### Memory Tools

```text
memory_begin_task
memory_context
memory_search
memory_get
memory_propose
memory_add
memory_merge
memory_correct
memory_commit_task
memory_cluster_get
```

### Command Tools

```text
command_poll
command_claim
command_complete
command_fail
command_reject
```

### Event Tools

```text
agent_event_append
event_get
session_digest_get
agent_heartbeat
```

### Mode Tools

```text
session_join
mode_get
mode_set
mode_run_template
```

### MCP Instructions 短版

```text
EchoMemory is the only long-term memory backend. Before tasks call memory_begin_task and memory_context. Use command_poll for managed sessions. Append important progress only. Before stopping call memory_commit_task and save durable decisions/rejected. Return summaries by default; request full content only by ID when necessary.
```

---

## 12. 工作模式

### assist

```yaml
mode: assist
leader: claude-code
assistants:
  - codex-cli
max_rounds: 2
max_context_tokens_per_agent: 3000
```

### review

```yaml
mode: review
builder: claude-code
reviewer: codex-cli
max_review_tokens: 1200
requires_response: true
```

### adversarial

```yaml
mode: adversarial
proposer: claude-code
challenger: codex-cli
judge: human
max_rounds: 2
max_proposal_tokens: 800
max_critique_tokens: 600
max_revision_tokens: 800
must_commit_rejected: true
```

### debate

```yaml
mode: debate
agents:
  - claude-code
  - codex-cli
rounds: 3
max_turn_tokens: 500
require_final_digest: true
```

### pipeline

```yaml
mode: pipeline
steps:
  - name: design
    agent: claude-code
  - name: review
    agent: codex-cli
  - name: implement
    agent: claude-code
  - name: summarize
    agent: echomemory
pass_digest_only: true
```

---

## 13. Claude Code Adapter

### MCP 添加

```bash
claude mcp add --transport stdio echomemory -- echomemory mcp --server http://127.0.0.1:9090
```

### CLAUDE.md

```markdown
# CLAUDE.md

@AGENTS.md

## Claude Code Specific Rules

Use EchoMemory as the only long-term memory backend.

Before work:
- call memory_begin_task
- call memory_context with max_tokens <= 1200

During work:
- append important events only
- poll commands if managed

Before stop:
- call memory_commit_task
- save durable decisions and rejected options
```

---

## 14. Codex CLI Adapter

### MCP 添加

```bash
codex mcp add echomemory -- echomemory mcp --server http://127.0.0.1:9090
```

### `.codex/config.toml`

```toml
[mcp_servers.echomemory]
command = "echomemory"
args = ["mcp", "--server", "http://127.0.0.1:9090"]
```

### `.codex/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "echomemory hook codex session-start",
            "statusMessage": "Joining EchoMemory session"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echomemory hook codex stop",
            "statusMessage": "Committing EchoMemory summary"
          }
        ]
      }
    ]
  }
}
```

---

## 15. HTML Mission Control

### 页面模块

```text
Session Header
Agent Status Panel
Mode Selector
Command Publisher
Live Event Timeline
Memory Candidate Queue
Conflict Resolution Panel
Rejected Memory Panel
Token Budget Monitor
Audit Log Viewer
```

### 原则

- 不引入 Node.js 构建链。
- 保持 server-side rendered 或轻量原生 JS。
- HTML 只发布结构化 command。
- 不直接执行 shell。
- timeline 使用分页或 since_seq。
- 大日志只展示 artifact 摘要和链接。

---

## 16. 安全模型

### API 安全

- 所有 API 需要 Bearer Token。
- SSE 也必须鉴权。
- CORS 使用 allowlist。
- 写操作必须记录 audit log。
- Agent token 可撤销。
- command claim 必须校验 target_agent / target_runtime。

### 命令安全

- HTML 控制台不得直接执行 shell。
- L4/L5 命令需要 human approval。
- shell 命令必须走 Agent Runtime 自身权限系统。
- command payload 使用 JSON schema 校验。
- idempotency_key 防止重复执行。

### 数据安全

- artifact 存路径和 hash，不把大日志塞入 event。
- 敏感字段写入前做 redaction。
- `.env`、secret、token 不进入 memory。
- 支持导出和备份时脱敏。

---

## 17. 外部参考项目阅读策略

不要让 Codex 阅读整个外部仓库。只按模块局部参考。

### AgentMemory

参考：

- `.claude-plugin`
- `.codex-plugin`
- `packages/mcp`
- `INSTALL_FOR_AGENTS.md`
- integrations

用于：Claude/Codex adapter、MCP 安装流。

不要读：benchmark、website、eval、完整 docs。

### OpenMemory / Mem0

参考：

- add_memories
- search_memory
- list_memories
- delete_all_memories
- 本地 UI 管理 memory 的思路

用于：最小 MCP memory tools。

不要引入：Qdrant、Docker 全栈、完整 Mem0 pipeline。

### Cognee MCP

参考：

- remember / recall / forget
- Standalone Mode vs API Mode
- session-aware memory
- MCP transport 组织

用于：EchoMemory MCP 工具语义。

不要读：frontend、distributed、deployment、evals、notebooks。

### Supermemory

参考：

- one memory across AI tools
- MCP client 接入体验
- contradiction / forgetting 概念

用于：产品定位、README、UX 文案、memory quality 概念。

不要读：connectors、multimodal extractors、apps monorepo。

### mcp-memory-service

参考：

- REST + MCP 双接口模式
- X-Agent-ID
- conversation_id
- SSE events
- dashboard / CLI 组合

用于：服务化接口、Agent identity、SSE。

不要实现：OAuth、ONNX embeddings、完整 endpoint 集。

### Zep / Graphiti

参考：

- 新事实 invalidates old fact
- 旧事实保留为 history
- current state 与 historical state 分离
- hybrid retrieval 概念

用于：stale memory、superseded/corrected、conflict detection。

不要引入：Neo4j、FalkorDB、Neptune、完整 temporal graph。

### LangMem

参考：

- hot path memory tools
- background memory manager
- namespace-based shared memory
- memory consolidation

用于：memory_quality background jobs。

不要引入：LangGraph runtime。

### Hindsight

参考：

- retain / recall / reflect 三段式

映射：

```text
retain -> memory_propose / memory_add
recall -> memory_context / memory_search
reflect -> session_digest / memory_quality job
```

不要引入：PostgreSQL、pgvector、cross-encoder。

### Redis Agent Memory Server

参考：

- working memory vs long-term memory
- search/get/edit/delete
- memory_prompt

用于：MCP tool taxonomy。

不要引入：Redis 依赖。

---

## 18. 构建 TODO

### Phase 0：基础梳理

- [ ] 阅读当前 README / DESIGN / storage / server / web_ui / auth。
- [ ] 标记现有 API、CLI、MCP、Web UI 能力。
- [ ] 创建 feature branch。
- [ ] 新增本文档到 `docs/`。

### Phase 1：短协议与 Adapter 配置

- [ ] 新增 `AGENTS.md`，保持 <= 800 tokens。
- [ ] 新增 `CLAUDE.md`，引用 AGENTS.md。
- [ ] 新增 `.codex/config.toml` 示例。
- [ ] 新增 `.codex/hooks.json` 示例。
- [ ] 新增 Claude hooks 示例文档。

### Phase 2：Schema Migration

- [ ] 新增 `migrations.py`。
- [ ] 创建 sessions。
- [ ] 创建 commands。
- [ ] 创建 agent_events。
- [ ] 创建 agent_states。
- [ ] 创建 session_digests。
- [ ] 创建 memory_candidates。
- [ ] 创建 memory_occurrences。
- [ ] 创建 memory_clusters。
- [ ] 创建 artifacts。
- [ ] 创建 audit_logs。
- [ ] 开启 WAL。

### Phase 3：Storage Layer

- [ ] session CRUD。
- [ ] command CRUD 和状态机。
- [ ] event append 和查询。
- [ ] digest 写入和读取。
- [ ] candidate memory 基础操作。
- [ ] occurrence / cluster。
- [ ] audit log。

### Phase 4：Memory Quality

- [ ] normalize。
- [ ] exact dedupe。
- [ ] near dedupe。
- [ ] conflict detection。
- [ ] memory_propose。
- [ ] merge / correct / supersede。
- [ ] quality_score。
- [ ] cluster summary。

### Phase 5：Command Bus API

- [ ] POST /api/commands。
- [ ] GET /api/commands/pending。
- [ ] POST /claim。
- [ ] POST /complete。
- [ ] POST /fail。
- [ ] lease 超时回收。
- [ ] permission_level 校验。

### Phase 6：Event Log + SSE

- [ ] POST /api/events。
- [ ] GET /api/events。
- [ ] GET /api/events/stream。
- [ ] command 状态变化写 event。
- [ ] memory 写入写 event。
- [ ] 每 10 条 event 生成 digest。

### Phase 7：MCP Tools

- [ ] memory_begin_task。
- [ ] memory_context。
- [ ] memory_propose。
- [ ] memory_add。
- [ ] memory_commit_task。
- [ ] command_poll。
- [ ] command_claim。
- [ ] command_complete。
- [ ] command_fail。
- [ ] agent_event_append。
- [ ] session_digest_get。
- [ ] agent_heartbeat。

### Phase 8：HTML Mission Control

- [ ] Session 列表。
- [ ] Agent 状态。
- [ ] Command Publisher。
- [ ] Live Timeline。
- [ ] Memory Candidate Queue。
- [ ] Conflict Resolution Panel。
- [ ] Token Budget Monitor。
- [ ] Audit Log Viewer。

### Phase 9：协作模式

- [ ] assist。
- [ ] review。
- [ ] adversarial。
- [ ] debate。
- [ ] pipeline。
- [ ] 模式模板 JSON。
- [ ] HTML 一键发布模板。

### Phase 10：安全与观测性

- [ ] CORS allowlist。
- [ ] SSE 鉴权。
- [ ] audit log。
- [ ] secret redaction。
- [ ] token budget 估算。
- [ ] metrics endpoint。
- [ ] backup/export。

### Phase 11：测试

- [ ] Storage tests。
- [ ] Command bus tests。
- [ ] Event log tests。
- [ ] Memory quality tests。
- [ ] MCP tools tests。
- [ ] HTML API tests。
- [ ] Claude/Codex adapter smoke tests。

---

## 19. 验收标准

MVP 完成标准：

- [ ] Claude Code 和 Codex CLI 均能接入同一 EchoMemory MCP。
- [ ] 同一 session 下两者能共享 event timeline。
- [ ] HTML 能发布 command 给指定 runtime / agent。
- [ ] Agent 能 claim / complete command。
- [ ] 至少跑通 adversarial 模式。
- [ ] decision 和 rejected 能沉淀到 knowledge。
- [ ] memory_context 默认返回 cluster summary，不返回重复全文。
- [ ] 命令、memory 写入、冲突解决均有 audit log。
- [ ] CORS / SSE / command 权限有基本保护。
- [ ] 未 memory_commit 的 session 显示 warning。

---

## 20. 给 Agent 的实现提示词

```text
请阅读 docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md，并按 Phase 顺序实现 EchoMemory Cross-AI-Agent Control Plane MVP。

要求：
1. 先输出实现计划和预计修改文件。
2. 不要一次性重构全部文件。
3. 优先实现 schema、storage、REST、MCP，再做 UI。
4. memory_context 默认只返回摘要，不返回全文。
5. 所有多 Agent 协作行为写入 append-only event log。
6. 所有长期决策写入 EchoMemory knowledge。
7. 所有 rejected 方案必须保留。
8. 不要让 HTML 直接执行 shell。
9. 不考虑 Obsidian。
10. 每完成一个 Phase，运行或说明测试。
```

---

## 21. 设计底线

- 不做远程 shell 控制台。
- 不默认注入完整 Skill 文档。
- 不默认返回完整 memory content。
- 不默认返回完整 event timeline。
- 不直接删除错误记忆。
- 不让 Agent 原生 memory 成为长期事实源。
- 不为 Claude Code 和 Codex 分别维护两套业务逻辑。
- 不忽略 rejected。
- 不无上限进行 debate/adversarial。
- 不考虑 Obsidian 作为 Roadmap 或执行路径。

---

## 22. 最终愿景

完成后，用户可以：

1. 在 HTML Mission Control 创建 session。
2. 选择 adversarial / review / pipeline 模式。
3. 指定 Claude Code、Codex CLI、Cursor、Kiro 的角色。
4. 发布结构化命令。
5. 实时观察 proposal / critique / revision / decision。
6. 让 EchoMemory 自动去重、合并、纠错、压缩记忆。
7. 把最终 decision、lesson、rule、rejected 沉淀为长期记忆。
8. 后续任何 Agent 启动任务时，都只读取最小必要上下文。

最终效果：

```text
不同 AI Agent，不同产品，不同上下文窗口，
但共享同一套长期记忆、命令调度、协作流程、质量治理和审计轨迹。
```
