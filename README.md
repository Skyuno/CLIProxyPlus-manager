# CLIProxyPlus Manager

Python 工具集，用于管理和监控 CLIProxyAPIPlus 服务的 Kiro 认证文件和用量。支持多面板并发查询。

## 功能

| 脚本 | 功能 |
|------|------|
| `scripts/usage_query.py` | 异步并发查询所有 Kiro 账户余额，支持多面板 |
| `scripts/usage_monitor.py` | 实时监控用量，计算消耗速率和预计用完时间 |
| `scripts/kiro_format_converter.py` | Kiro JSON 格式互转（aiclient2api ↔ cliprproxyplus） |

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置

复制 `config.example.yaml` 到 `config.yaml` 并填写：

```yaml
global:
  timeout: 30

panels:
  - name: "Panel 1"
    url: "http://127.0.0.1:8080"
    key: "your-management-key-here"

  - name: "Panel 2"
    url: "http://127.0.0.1:8081"
    key: "another-management-key"
```

### 3. 运行

```bash
# 查询余额（全部面板）
python scripts/usage_query.py

# 查询指定面板
python scripts/usage_query.py --panel "Panel 1"

# 实时监控（默认60秒刷新）
python scripts/usage_monitor.py

# 自定义刷新间隔
python scripts/usage_monitor.py -i 30

# 监控指定面板
python scripts/usage_monitor.py --panel "Panel 1" --panel "Panel 2"

# 格式转换（自动检测方向）
python scripts/kiro_format_converter.py input.json -o output.json
```

## 用量监控示例

```
[2026-02-06 01:00:00] 💰 总剩余: 123.45 | 📈 5.20/h | ⏱️ 23小时 45分钟
  [███████░░░░░░░░]  45.2% |  50.00 | user1@example.com
  [██████████░░░░░]  65.0% |  73.45 | user2@example.com
```

## 格式转换说明

`kiro_format_converter.py` 支持两种 Kiro JSON 格式之间的互转：

| 格式 | 命名风格 | 示例字段 |
|------|----------|----------|
| **aiclient2api** | 驼峰命名 | `accessToken`, `authMethod: "IdC"` |
| **cliprproxyplus** | 下划线命名 | `access_token`, `auth_method: "idc"` |

```bash
# 自动检测并转换
python scripts/kiro_format_converter.py kiro.json

# 指定目标格式
python scripts/kiro_format_converter.py kiro.json --to cliproxy
python scripts/kiro_format_converter.py kiro.json --to aiclient
```

## 项目结构

```
CLIProxyPlus-manager/
├── scripts/                     # CLI 脚本
│   ├── usage_query.py           # 余额查询（异步）
│   ├── usage_monitor.py         # 实时监控（异步）
│   └── kiro_format_converter.py # 格式转换
├── src/CLIProxyPlus_manager/    # 核心库
│   ├── panel/                   # CLIProxyPlus 面板管理
│   │   ├── config.py            # 多面板 YAML 配置（AppConfig）
│   │   ├── client.py            # 同步面板 API 客户端
│   │   └── async_client.py      # 异步面板 API 客户端
│   ├── kiro/                    # Kiro API
│   │   ├── api.py               # 同步 Kiro 用量查询
│   │   ├── async_api.py         # 异步 Kiro 用量查询
│   │   └── formatter.py         # 用量格式化和展示
│   └── utils/                   # 通用工具
├── template/                    # JSON 格式模板
├── config.yaml                  # 配置文件（不纳入版本控制）
└── config.example.yaml          # 配置示例
```

## License

MIT
