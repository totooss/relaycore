# Codex 执行 EchoMemory Cross-AI-Agent 构建的指导对话模板（无 Obsidian 版）

> 用途：把这份文件交给 Codex CLI，按阶段驱动它实现 EchoMemory Cross-AI-Agent Control Plane。  
> 范围：**不考虑 Obsidian**。本项目核心是辅助 AI Agent 执行，不是构建人类 Markdown 知识库。  
> 核心目标：采用“短规则 + 阶段文件 + 单阶段执行 + 每阶段验收 + 外部参考限读”的方式，降低上下文噪音和运行时 token 消耗。

---

## 0. 总原则

Codex 执行时不要直接把完整构建蓝图长期放进上下文。推荐结构：

```text
AGENTS.md                                      # 短运行时规则，Codex 默认读
CLAUDE.md                                      # Claude Code 补充规则
docs/CODEX_EXECUTION_GUIDE_NO_OBSIDIAN.md      # 本文件
docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md # 完整蓝图，只在拆分阶段读取
docs/phases/                                   # 后续每次只读一个 phase
```

Codex 的执行策略：

1. 第一次只读完整蓝图并拆分阶段文件，不改业务代码。
2. 后续每次只处理一个 Phase。
3. 每个 Phase 开始前先输出计划和预计修改文件。
4. 每个 Phase 结束后输出测试结果、风险、下一步建议。
5. 不允许 Codex 自行扩大任务范围。
6. 不允许把 HTML 控制台做成直接 shell 执行器。
7. 不考虑 Obsidian 接入、导出或同步。
8. 所有长期设计决策写入 EchoMemory；如果 EchoMemory MCP 暂不可用，则写入 `docs/decisions/` 作为临时替代。

---

## 1. 推荐准备文件

```text
AGENTS.md
CLAUDE.md
docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md
docs/CODEX_EXECUTION_GUIDE_NO_OBSIDIAN.md
```

其中：

- `AGENTS.md`：短规则，控制在 500–800 tokens。
- `docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md`：完整方案。
- `docs/CODEX_EXECUTION_GUIDE_NO_OBSIDIAN.md`：本文件。
- `docs/phases/`：由 Codex 根据完整蓝图拆分生成。

---

## 2. AGENTS.md 推荐内容

```markdown
# AGENTS.md

## EchoMemory Runtime Rules

EchoMemory is the only long-term memory backend for this project.

Before work:
1. Call `memory_begin_task` if EchoMemory MCP is available.
2. Call `memory_context` with `max_tokens <= 1200`.
3. Read active decisions, rules, lessons, and relevant rejected options.

During work:
1. Append only important events with `agent_event_append`.
2. Poll commands with `command_poll` when in managed session.
3. Do not store durable project decisions only in native agent memory.

Before stop:
1. Call `memory_commit_task` if available.
2. Save durable decisions and rejected options.
3. If EchoMemory is unavailable, explicitly report it.

Implementation rules:
- Do not read the full build document unless explicitly asked.
- For implementation, read only the current `docs/phases/phase-*.md` file and relevant source files.
- Do not implement multiple phases at once.
- Do not turn the HTML UI into a direct shell execution console.
- Do not consider Obsidian integration.
```

---

## 3. Codex MCP 接入 EchoMemory

如果 EchoMemory 当前已经能启动 MCP Server：

```bash
codex mcp add echomemory -- echomemory mcp --server http://127.0.0.1:9090
```

也可以写入 `.codex/config.toml`：

```toml
[mcp_servers.echomemory]
command = "echomemory"
args = ["mcp", "--server", "http://127.0.0.1:9090"]
```

如果 MCP Server 还没实现，先跳过 MCP 配置，使用 REST / CLI / 文档文件作为临时替代。

---

## 4. Codex Hooks 可选配置

如果 `echomemory hook codex ...` 已实现，可创建 `.codex/hooks.json`：

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

如果 hook 命令还没实现，不要启用 hooks，避免 Codex 启动时报错。

---

## 5. 外部参考项目限读策略

### 总规则

不要让 Codex 阅读整个外部仓库。只允许按当前 Phase 局部参考。

### Phase 1 / Phase 7：Claude/Codex Adapter

只参考 AgentMemory：

```text
.claude-plugin
.codex-plugin
packages/mcp
INSTALL_FOR_AGENTS.md
integrations
```

不要读：

```text
benchmark
website
eval
完整 docs
```

Prompt：

```text
请只参考 AgentMemory 中与 Claude/Codex/MCP 接入有关的部分：.claude-plugin、.codex-plugin、packages/mcp、INSTALL_FOR_AGENTS.md、integrations。
总结它如何让 Claude Code / Codex 类 coding agents 接入持久记忆。
不要阅读 benchmark、website、eval、完整 docs。
不要复制实现，只提取 adapter 设计模式。
```

### Phase 7：MCP Memory Tools

参考 OpenMemory/Mem0：

```text
add_memories
search_memory
list_memories
delete_all_memories
```

参考 Cognee MCP：

```text
remember
recall
forget
Standalone Mode vs API Mode
session-aware memory
```

参考 Redis Agent Memory Server：

```text
working memory
long-term memory
search/get/edit/delete
memory_prompt
```

不要引入：

```text
Qdrant
Redis
完整 Docker stack
完整 graph pipeline
```

### Phase 4：Memory Quality

参考 Zep/Graphiti：

```text
新事实 invalidates old fact
旧事实保留为 history
current state 与 historical state 分离
hybrid retrieval 概念
```

参考 Supermemory：

```text
contradiction
forgetting
one memory across tools
```

参考 LangMem：

```text
hot path memory tools
background memory manager
namespace-based shared memory
memory consolidation
```

不要引入：

```text
Neo4j
FalkorDB
Neptune
LangGraph runtime
external connectors
multimodal extractors
```

### Phase 6：REST + MCP + SSE

参考 mcp-memory-service：

```text
REST + MCP 双接口
X-Agent-ID
conversation_id
SSE events
dashboard/CLI 管理面
```

不要实现：

```text
OAuth
ONNX embeddings
完整 endpoint 集
```

### Hindsight 可选参考

只参考语义：

```text
retain -> memory_propose / memory_add
recall -> memory_context / memory_search
reflect -> session_digest / memory_quality job
```

不要引入：

```text
PostgreSQL
pgvector
cross-encoder
```

---

## 6. 第一轮：拆分 Phase 文档

Prompt 1：

```text
请先阅读：

1. AGENTS.md
2. docs/ECHOMEMORY_CROSS_AGENT_BUILD_NO_OBSIDIAN.md

任务：

不要修改任何业务代码。
不要实现功能。
请只做文档拆分。

请根据完整蓝图创建 `docs/phases/` 目录，并把构建流程拆成以下阶段文件：

- phase-0-overview.md
- phase-1-runtime-contract-and-adapters.md
- phase-2-schema-migrations.md
- phase-3-storage-layer.md
- phase-4-memory-quality.md
- phase-5-command-bus-api.md
- phase-6-event-log-and-sse.md
- phase-7-mcp-tools.md
- phase-8-html-mission-control.md
- phase-9-collaboration-modes.md
- phase-10-security-and-observability.md
- phase-11-tests-and-validation.md

每个 phase 文件必须包含：

1. 本阶段目标
2. 输入文件
3. 预计修改文件
4. 可参考的外部项目局部范围
5. 详细 TODO
6. 不允许做的事情
7. 验收标准
8. 推荐测试命令

特别要求：

- 不考虑 Obsidian。
- 不允许把完整蓝图复制进 phase 文件。
- 每个 phase 文件只保留该阶段需要的信息。

输出要求：

- 先列出你准备创建的文件。
- 然后创建文件。
- 最后总结每个 phase 的作用。
```

---

## 7. Phase 执行模板

每个 Phase 都采用：

```text
先计划 -> 等确认 -> 再实现 -> 再复盘
```

### 计划 Prompt

```text
请只阅读：

1. AGENTS.md
2. docs/phases/<当前phase>.md
3. 当前 phase 明确要求的源码文件

任务：

实现当前 Phase。

限制：

- 不要读取完整蓝图。
- 不要实现其他 Phase。
- 不要考虑 Obsidian。
- 不要引入当前 phase 未要求的新依赖。
- 不要让 HTML 直接执行 shell。

请先输出：

1. 实现计划
2. 预计新增或修改的文件
3. 需要参考的外部项目局部范围
4. 风险点
5. 需要我确认的问题

等待我确认后再修改文件。
```

### 确认执行 Prompt

```text
确认执行当前 Phase。请按刚才计划修改文件。
完成后输出：

1. 修改了哪些文件
2. 每个文件改了什么
3. 已完成 TODO
4. 未完成 TODO 与原因
5. 如何验证
6. 风险
7. 下一阶段建议

不要继续实现下一阶段。
```

---

## 8. 推荐 Phase 顺序

```text
1. Prompt 1：拆分 phase 文档
2. Phase 1：短协议与 adapter 配置
3. Phase 2：Schema Migration
4. Phase 3：Storage Layer
5. Phase 4：Memory Quality
6. Phase 5：Command Bus API
7. Phase 6：Event Log + SSE
8. Phase 7：MCP Tools
9. Phase 8：HTML Mission Control
10. Phase 9：Collaboration Modes
11. Phase 10：Security and Observability
12. Phase 11：Tests and Validation
```

---

## 9. 复盘 Prompt

```text
请对刚完成的 Phase 做复盘：

1. 实际修改了哪些文件？
2. 每个文件的关键变化是什么？
3. 哪些 TODO 已完成？
4. 哪些 TODO 未完成？为什么？
5. 有哪些风险？
6. 是否引入了 token 运行时膨胀风险？
7. 是否引入了安全风险？
8. 是否错误引入了 Obsidian 相关内容？如果有，请指出并建议移除。
9. 下一阶段开始前需要我确认什么？

请不要继续实现下一阶段。
```

---

## 10. 偏航纠正 Prompt

```text
停止当前扩展实现。
你已经超出当前 Phase 范围。
请回到当前阶段文件：docs/phases/<当前phase>.md。

请输出：
1. 你刚才做了哪些超范围修改？
2. 是否引入了 Obsidian 或人类知识库相关内容？如果有，建议删除。
3. 哪些应该回滚？
4. 哪些可以保留？
5. 回到当前 Phase 后的最小实现计划。

不要继续写代码，等待确认。
```

---

## 11. Token 过载时的压缩 Prompt

```text
请停止实现，生成当前阶段的 compact handoff summary。

格式：

# Handoff Summary

## Current Phase

## Goal

## Completed Changes

## Files Modified

## Remaining TODO

## Known Risks

## Test Status

## Next Exact Prompt

要求：
- 不超过 1000 tokens。
- 不包含完整代码。
- 不包含 Obsidian 内容。
- 只保留下一轮继续所需信息。
```

新开 Codex 会话时只提供：

```text
AGENTS.md
当前 phase 文件
Handoff Summary
相关源码文件
```

---

## 12. 设计决策记录

如果 EchoMemory MCP 已可用：

```text
请将本阶段的重要设计决策写入 EchoMemory：

- type: decision
- title: <简短标题>
- content: <为什么这样设计>
- rejected: <被否决方案和原因>
- tags: ["echomemory", "cross-agent", "phase-X"]
```

如果 EchoMemory MCP 不可用：

```text
EchoMemory MCP 暂不可用。
请把本阶段设计决策写入：

docs/decisions/phase-X-<short-title>.md

格式：

# Decision: <title>

## Context

## Decision

## Rejected Options

## Consequences

## Tags
```

---

## 13. 最小启动命令

### 启动 EchoMemory

```bash
echomemory serve --port 9090
```

### 配置 Codex MCP

```bash
codex mcp add echomemory -- echomemory mcp --server http://127.0.0.1:9090
```

### 打开 Codex

```bash
codex
```

然后从 Prompt 1 开始。

---

## 14. 明确禁止

不要让 Codex 做这些事：

1. 一次性实现全部 Phase。
2. 把完整蓝图复制进 AGENTS.md。
3. 在 HTML 中直接执行 shell 命令。
4. 默认返回完整 memory content。
5. 默认返回完整 event timeline。
6. 自动删除冲突记忆。
7. 自动覆盖安全相关 decision。
8. 引入重型依赖或需要联网的依赖。
9. 跳过测试直接声称完成。
10. 修改认证逻辑但不说明风险。
11. 加入 Obsidian 接入、导出、同步或 Roadmap。
12. 为 Claude Code 和 Codex CLI 写两套不同业务逻辑。

---

## 15. 成功标志

正确执行时应看到：

```text
Phase 计划清楚
修改文件很少
每次只解决一个层级
外部参考只读局部
测试或验证明确
复盘能指出风险
不会把完整文档塞进上下文
不会越权实现后续阶段
不会加入 Obsidian 内容
```

最终目标：

```text
用 Codex 稳定、低上下文、低 token、可回滚地完成 EchoMemory Cross-AI-Agent Control Plane 的 MVP 构建。
```
