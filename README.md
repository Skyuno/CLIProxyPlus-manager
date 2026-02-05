# CLIProxyPlus Manager

Python 工具集，用于管理和监控 CLIProxyAPIPlus 服务的 Kiro 认证文件和用量。

## 功能

| 脚本 | 功能 |
|------|------|
| `scripts/usage_query.py` | 一次性查询所有 Kiro 账户余额 |
| `scripts/usage_monitor.py` | 实时监控用量，计算消耗速率和预计用完时间 |
| `scripts/kiro_format_converter.py` | Kiro JSON 格式互转（aiclient2api ↔ cliprproxyplus） |

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写：

```env
CLIPROXY_URL=http://127.0.0.1:8080
CLIPROXY_KEY=your_management_api_key
```

### 3. 运行

```bash
# 查询余额
python scripts/usage_query.py

# 实时监控（默认60秒刷新）
python scripts/usage_monitor.py

# 自定义刷新间隔
python scripts/usage_monitor.py -i 30

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
│   ├── usage_query.py           # 余额查询
│   ├── usage_monitor.py         # 实时监控
│   └── kiro_format_converter.py # 格式转换
├── src/CLIProxyPlus_manager/    # 核心库
│   ├── panel/                   # CLIProxyPlus 管理面板 API
│   └── kiro/                    # Kiro API 和格式化工具
├── template/                    # JSON 格式模板
├── output/                      # 查询结果和历史记录
└── .env                         # 配置文件
```

## License

MIT
