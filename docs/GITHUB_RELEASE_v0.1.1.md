# RelayCore v0.1.1

这是 RelayCore 的首个中文化公开发布版本。

## 本次更新

- 新增中文主 README
- 新增公开对比表与构建导图
- 明确标注项目借鉴来源：`EastSword/EchoMemory`
- 统一对外品牌名称为 `RelayCore`
- 保留内部 Python 包名 `echomemory` 作为兼容层

## 当前能力

- SQLite 共享记忆与 command store
- 结构化 command relay
- append-only event timeline 与 digest
- MCP-style memory / command tools
- Mission Control Web UI
- 安全基线：token、CORS、audit、redaction、export、backup
- 本地 Claude / Codex memory 迁移器

## CLI

- `relaycore init-db`
- `relaycore serve`
- `relaycore export`

兼容入口仍可用：

- `python -m echomemory init-db`
- `python -m echomemory serve`
- `python -m echomemory export`

## 借鉴说明

本项目在公开定位与思路上借鉴了：

- [EastSword/EchoMemory](https://github.com/EastSword/EchoMemory)

但当前仓库中的实现、打包、CLI、迁移器、Mission Control、安全与测试体系均为本仓库自身版本。

## 验证状态

- 本地自动化测试通过
- 2026-07-19 当前状态：`46 passed`
