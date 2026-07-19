# RelayCore v0.1.2

这是 RelayCore 完成内部实现统一命名后的发布版本。

## 本次更新

- 内部 Python 包名统一为 `relaycore`
- 代码、测试、脚本、环境变量、HTTP 头与指标前缀全部统一为 `RelayCore`
- 清理旧的兼容层表述，公开文档与仓库结构完全对齐
- 保留对灵感来源 `EastSword/EchoMemory` 的明确致谢

## 当前能力

- SQLite 共享记忆与 command store
- 结构化 command relay
- append-only event timeline 与 digest
- MCP-style memory / command tools
- Mission Control Web UI
- token、CORS、audit、redaction、export、backup 相关接口
- 本地 Claude / Codex memory 迁移器

## CLI

- `relaycore init-db`
- `relaycore serve`
- `relaycore export`
- `python -m relaycore init-db`
- `python -m relaycore serve`
- `python -m relaycore export`

## 借鉴说明

本项目在公开定位与思路上借鉴了：

- [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory)

但当前仓库中的实现、打包、CLI、迁移器、Mission Control、安全与测试体系均为本仓库自身版本。

## 验证状态

- 本地自动化测试通过
- 2026-07-19 当前状态：`46 passed`

<details>
<summary>English</summary>

This release consolidates the repository under the unified RelayCore product and package naming.

## What Changed

- The internal Python package name is `relaycore`
- Runtime code, tests, scripts, environment variables, headers, and metric prefixes use `RelayCore` / `relaycore`
- Public documentation and repository structure use the same naming
- Attribution to `EastSword/EchoMemory` remains explicit

## Repository Surfaces

- SQLite-backed shared memory and command store
- structured command relay
- append-only event timeline and digests
- MCP-style memory and command tools
- Mission Control web UI
- security-related endpoints for token, CORS, audit, export, and backup flows
- local Claude/Codex memory migration scripts

## CLI

- `relaycore init-db`
- `relaycore serve`
- `relaycore export`
- `python -m relaycore init-db`
- `python -m relaycore serve`
- `python -m relaycore export`

## Validation

- Local automated tests passed
- Status on July 19, 2026: `46 passed`

</details>
