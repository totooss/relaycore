# RelayCore

> 面向本地或自托管 AI runtime 的共享记忆与结构化命令中继控制面。

`中文为主` | `English summary below`

## 项目简介

RelayCore 提供一套轻量、可自托管的控制平面，让多个 AI runtime 共享长期记忆、事件时间线和结构化命令流，而不是依赖一次性聊天上下文传话。

当前仓库公开包含：

- SQLite 共享存储
- 结构化 command bus
- append-only event timeline 与 digest
- MCP-style memory / command tools
- Mission Control Web UI
- 记忆浏览与冲突处理界面
- export、backup、audit、metrics、CORS、token 相关接口
- 本地历史记忆迁移脚本

## 核心能力

- 用统一存储层承载跨 runtime 的长期记忆
- 用结构化命令总线分发任务、声明权限和记录状态
- 用事件时间线和 digest 追踪执行过程
- 用 REST API、CLI、MCP HTTP bridge 与 Web UI 提供多种接入方式
- 用本地迁移脚本把历史记忆导入 RelayCore

## 安装

核心服务：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

启用 MCP HTTP bridge：

```bash
python3.12 -m venv .venv-mcp
source .venv-mcp/bin/activate
pip install -e .[mcp]
```

说明：

- 核心服务支持 `Python 3.9+`
- `relaycore mcp-http` 依赖官方 MCP Python SDK，需要 `Python 3.10+`

## 快速开始

```bash
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

## MCP 接入示例

启动 MCP HTTP bridge：

```bash
relaycore mcp-http --host 127.0.0.1 --port 9090 --db ~/.relaycore/relaycore.db
```

将示例配置合并到 `~/.codex/config.toml`：

```toml
[mcp_servers.relaycore]
url = "http://127.0.0.1:9090/mcp"
```

示例文件：

- `examples/codex/config.toml.example`

验证方式：

- `codex mcp get relaycore`
- `codex mcp list`

## 迁移历史记忆

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

```bash
relaycore init-db
relaycore serve
relaycore export
relaycore mcp-http
```

## 仓库内容

- `relaycore/`：核心运行时代码
- `scripts/`：迁移与辅助脚本
- `tests/`：自动化测试
- `examples/`：公开可用配置示例
- `docs/ROADMAP.md`：后续规划
- `docs/GITHUB_RELEASE_v1.0.md`：当前 release 文案

## 测试

```bash
pytest
```

当前本地测试结果（2026-07-19）：`55 passed`

## 致谢

- 本项目参考了 [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory) 的公开项目思路。

## 许可证

MIT，见 [LICENSE](LICENSE)。

<details>
<summary>English</summary>

## Overview

RelayCore is a lightweight shared-memory and structured command relay for local or self-hosted AI runtimes.

This public repository includes:

- SQLite-backed shared storage
- a structured command bus
- an append-only event timeline with digests
- MCP-style memory and command tools
- a Mission Control web UI
- a memory viewer and conflict-resolution workflow
- export, backup, audit, metrics, CORS, and token-related surfaces
- local history migration scripts

## Quick Start

```bash
relaycore init-db
relaycore serve --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/mission-control`.

## MCP Bridge

```bash
relaycore mcp-http --host 127.0.0.1 --port 9090 --db ~/.relaycore/relaycore.db
```

For Codex, merge the example from `examples/codex/config.toml.example` into `~/.codex/config.toml`.

## Validation

- `pytest`
- Local status on July 19, 2026: `55 passed`

</details>
