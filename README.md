# CLIProxyPlus Manager

Python 工具集，用于管理和监控 CLIProxyAPIPlus 服务的 Kiro 认证文件和用量。

## 功能

| 脚本 | 功能 |
|------|------|
| `kiro_usage_query.py` | 一次性查询所有 Kiro 账户余额 |
| `kiro_usage_monitor.py` | 实时监控用量，计算消耗速率和预计用完时间 |

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
python kiro_usage_query.py

# 实时监控（默认60秒刷新）
python kiro_usage_monitor.py

# 自定义刷新间隔
python kiro_usage_monitor.py -i 30
```

## 监控输出示例

```
[2026-02-06 01:00:00] 💰 总剩余: 123.45 | 📈 5.20/h | ⏱️ 23小时 45分钟
  [███████░░░░░░░░]  45.2% |  50.00 | user1@example.com
  [██████████░░░░░]  65.0% |  73.45 | user2@example.com
```

## 项目结构

```
CLIProxyPlus-manager/
├── kiro_usage_query.py      # 余额查询脚本
├── kiro_usage_monitor.py    # 实时监控脚本
├── src/CLIProxyPlus_manager/
│   ├── panel/               # CLIProxyPlus 管理面板 API
│   └── kiro/                # Kiro API 和格式化工具
├── output/                  # 查询结果和历史记录
└── .env                     # 配置文件
```

## License

MIT
