# RelayCore v0.1.3

这是 RelayCore 补齐本地 Codex / MCP 可运行链路后的发布版本。

## 本次更新

- 新增 `relaycore mcp-http`，用于启动 streamable HTTP MCP 服务
- 明确区分核心服务依赖与 MCP 可选依赖
- README 补充本地 Codex 接入与运行步骤
- 清理包元数据中的个人作者名暴露

## 当前能力

- SQLite 共享记忆与 command store
- 结构化 command relay
- append-only event timeline 与 digest
- MCP-style memory / command tools
- Mission Control Web UI
- token、CORS、audit、redaction、export、backup 相关接口
- 本地 Claude / Codex memory 迁移器
- 本地 Codex 可接入的 streamable HTTP MCP bridge

## CLI

- `relaycore init-db`
- `relaycore serve`
- `relaycore export`
- `relaycore mcp-http`
- `python -m relaycore init-db`
- `python -m relaycore serve`
- `python -m relaycore export`

## 运行说明

- 核心服务：`Python 3.9+`
- MCP bridge：`Python 3.10+`，并安装 `pip install -e .[mcp]`

## 验证状态

- 本地自动化测试通过
- `pytest` 当前状态：`48 passed`
- 本地 MCP 连通验证已完成，可列出 12 个工具并成功调用 `memory_begin_task`

<details>
<summary>English</summary>

This release adds a verified local Codex / MCP runtime path for RelayCore.

## What Changed

- Added `relaycore mcp-http` for running a streamable HTTP MCP service
- Clarified the split between core dependencies and optional MCP dependencies
- Added documented local Codex setup steps to the README
- Removed the previous personal author name from package metadata

## Runtime Notes

- Core service: `Python 3.9+`
- MCP bridge: `Python 3.10+` with `pip install -e .[mcp]`

## Validation

- Local automated tests passed
- `pytest` status: `48 passed`
- Local MCP connectivity was verified by listing tools and calling `memory_begin_task`

</details>
