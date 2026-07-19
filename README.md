# RelayCore

> 面向 Codex、Claude 等本地 AI Runtime 的跨 Agent 记忆与命令中继控制面。

`中文为主` | `English available below`

## 中文

RelayCore 是一个面向本地或自托管 AI Runtime 的共享记忆与命令中继项目。当前仓库包含：

- SQLite 共享存储
- 结构化 command bus
- append-only event timeline
- digest 生成
- MCP-style memory / command tools
- Mission Control Web UI
- export、backup、metrics、audit、CORS、token 相关接口
- 本地 Claude / Codex memory 迁移脚本

## 文档

- [构建路线图](docs/ROADMAP.md)
- [发布信息](docs/RELEASE_READINESS.md)
- [当前 Release 文案](docs/GITHUB_RELEASE_v0.1.2.md)

## 与 EastSword/EchoMemory 的关系

本项目**明确借鉴了** [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory) 的公开思路与方向，尤其是：

- 多 Agent 共享记忆的产品定位
- 通过统一记忆层支撑不同智能体协作
- 将“共享上下文”从临时会话提升到可沉淀系统

这里保留这层致谢与标记，是为了对来源保持清晰说明，而不是弱化本项目的独立实现。

## 跨项目信息表

下表只基于公开仓库描述和公开可见接口整理。

| 项目 | 公开描述 | 主要接口 | 公开材料中的存储 / 运行模型 | 公开来源 |
| --- | --- | --- | --- | --- |
| RelayCore | 面向本地或自托管 AI Runtime 的共享记忆与命令中继项目 | CLI、REST API、MCP-style tools、Web UI、迁移脚本 | 当前仓库中的 Python 项目，使用 SQLite 作为共享存储 | [totooss/relaycore](https://github.com/totooss/relaycore) |
| EastSword/EchoMemory | 多 Agent 共享记忆项目 | 公开仓库描述与项目页面引用 | 本仓库引用到的公开材料未在这里展开完整实现矩阵 | [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory) |
| Mem0 | 面向 AI Agents 的通用记忆层 | CLI、SDK、云服务材料、公开仓库 | 公开 README 描述了 user / session / agent 级记忆与托管服务选项 | [mem0ai/mem0](https://github.com/mem0ai/mem0) |
| OpenMemory | 面向 LLM 和 agents 的 memory engine | Python SDK、Node SDK、server、MCP、UI、connectors | 公开 README 描述了 local-first 部署以及 SQLite / Postgres 选项 | [CaviraOSS/OpenMemory](https://github.com/CaviraOSS/OpenMemory) |
| Cognee | 面向 agents 的开源 AI memory platform | Python package、plugins、clients、knowledge-graph workflow、公开文档 | 公开 README 描述了自托管知识图谱引擎及向量 / 图组件 | [topoteretes/cognee](https://github.com/topoteretes/cognee) |

说明：

- RelayCore 条目描述的是当前仓库内容。
- 外部项目条目基于 2026-07-19 可见的公开仓库材料整理。
- 该表仅做信息整理，不做排序、评分或结论判断。

## 构建导图

```mermaid
flowchart LR
    A["CLI / Scripts"] --> B["RelayCore API Server"]
    H["Mission Control UI"] --> B
    I["Local Memory Migrator"] --> F["MCP-style Tool Layer"]
    B --> C["Command Bus"]
    B --> D["Event Log + SSE"]
    B --> E["Memory Quality"]
    F --> C
    F --> D
    F --> E
    C --> G["SQLite Storage"]
    D --> G
    E --> G
    G --> J["Export / Backup / Audit / Metrics"]
```

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
relaycore init-db
relaycore serve --host 127.0.0.1 --port 8080
```

打开：

- `http://127.0.0.1:8080/mission-control`

也可以直接使用模块入口：

```bash
python -m relaycore init-db
python -m relaycore serve --host 127.0.0.1 --port 8080
```

## Memory 迁移

只预览、不写库：

```bash
python scripts/migrate_local_memories.py --dry-run
```

显式包含历史摘要和支持的 runtime store：

```bash
python scripts/migrate_local_memories.py --dry-run --include-history --include-runtime-store
```

实际导入：

```bash
python scripts/migrate_local_memories.py --session-id local-memory-migration
```

## CLI

可用入口：

```bash
relaycore init-db
relaycore serve
relaycore export
```

## 测试

```bash
pytest
```

当前本地测试结果（2026-07-19）：`46 passed`

## 仓库结构

- `relaycore/`: 核心实现包
- `scripts/`: 迁移与辅助脚本
- `tests/`: 自动化测试
- `docs/`: 路线图、发布评估、阶段文档与决策记录

## 后续优化 TODO

- Docker 化
- 反向代理部署示例
- 环境变量与配置文档
- 更完整的 CLI smoke tests
- 在 Mission Control 中加入导入预览与勾选确认
- 增加更多 Claude / Codex source adapters
- 增加导入回滚与 snapshot 说明
- 更完整的 observability
- 恢复演练和运维 runbook
- 多用户场景下的认证与限流相关能力

如果你有建议，欢迎在 issue 中提出；后续 roadmap 会持续吸收合适的 issue 建议。

## 许可证

MIT，见 [LICENSE](LICENSE)。

<details>
<summary>English</summary>

## English

RelayCore is a shared memory and command relay project for local or self-hosted AI runtimes.

This repository currently includes:

- SQLite-backed shared storage
- a structured command bus
- an append-only event timeline
- digest generation
- MCP-style memory and command tools
- a Mission Control web UI
- export, backup, metrics, audit, CORS, and token-related surfaces
- local Claude/Codex memory migration scripts

## Documentation

- [Roadmap](docs/ROADMAP.md)
- [Release Information](docs/RELEASE_READINESS.md)
- [Current Release Notes](docs/GITHUB_RELEASE_v0.1.2.md)

## Relation to EastSword/EchoMemory

This project explicitly references [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory) as an inspiration source.

## Cross-Project Reference Table

The table below is limited to public repository descriptions and publicly visible interfaces.

| Project | Public description | Primary interfaces | Storage / runtime model in public materials | Public source |
| --- | --- | --- | --- | --- |
| RelayCore | Shared memory and command relay project for local or self-hosted AI runtimes | CLI, REST API, MCP-style tools, Web UI, migration script | SQLite-backed local/self-hosted Python project in this repository | [totooss/relaycore](https://github.com/totooss/relaycore) |
| EastSword/EchoMemory | Multi-agent shared memory project | Public repository description and project page references | Public materials referenced in this repository do not expose a full implementation matrix here | [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory) |
| Mem0 | Universal memory layer for AI Agents | CLI, SDKs, managed/cloud materials, public repositories | Public README describes user/session/agent memory and managed service options | [mem0ai/mem0](https://github.com/mem0ai/mem0) |
| OpenMemory | Cognitive memory engine for LLMs and agents | Python SDK, Node SDK, server, MCP, UI, connectors | Public README describes local-first deployment with SQLite/Postgres options | [CaviraOSS/OpenMemory](https://github.com/CaviraOSS/OpenMemory) |
| Cognee | Open-source AI memory platform for agents | Python package, plugins, clients, knowledge-graph workflow, public docs | Public README describes a self-hosted knowledge graph engine with vector and graph components | [topoteretes/cognee](https://github.com/topoteretes/cognee) |

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
relaycore init-db
relaycore serve --host 127.0.0.1 --port 8080
```

Module entrypoint:

```bash
python -m relaycore init-db
python -m relaycore serve --host 127.0.0.1 --port 8080
```

## Tests

```bash
pytest
```

Current local test result on July 19, 2026: `46 passed`

</details>
