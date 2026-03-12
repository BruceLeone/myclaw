# Telegram 订单查询机器人

## 功能特性

1. **群聊监听** - 自动检测包含订单关键词的消息（订单号、订单、order）
2. **订单匹配** - 从消息中提取订单号，查询数据库匹配
3. **图片保存** - 匹配成功后自动提取并保存消息中的图片
4. **错误反馈** - 未匹配时返回友好错误提示

## 项目结构

```
tg-order-bot/
├── bot.py              # 主程序入口
├── config.py           # 配置文件
├── database.py         # 数据库操作
├── handlers.py         # 消息处理器
├── requirements.txt    # 依赖包
├── .env.example        # 环境变量示例
└── data/               # 数据目录
    ├── orders.db       # SQLite数据库
    └── images/         # 图片存储目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Bot Token
```

### 3. 初始化数据库

```bash
python database.py
```

### 4. 运行机器人

```bash
python bot.py
```

## 获取 Bot Token

1. 在 Telegram 中搜索 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 按提示设置名称和用户名
4. 复制获得的 Token 到 `.env` 文件

## 使用方法

### 方式1：自动监听（群聊）
将机器人添加到群聊后，它会自动监听包含订单关键词的消息：
- "订单号: 12345"
- "订单 12345"
- "order 12345"
- "order#12345"

### 方式2：主动查询（私聊/群聊）
发送 `/check 订单号` 主动查询订单

## 数据库结构

**orders 表：**
- id: 主键
- order_number: 订单号（唯一）
- images: 图片路径（JSON数组）
- status: 订单状态
- created_at: 创建时间
- updated_at: 更新时间

**order_images 表：**
- id: 主键
- order_id: 关联订单ID
- file_path: 图片文件路径
- file_id: Telegram文件ID
- created_at: 创建时间

## 部署建议

### 使用 systemd 守护进程

```bash
sudo nano /etc/systemd/system/tg-order-bot.service
```

内容：
```ini
[Unit]
Description=Telegram Order Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/tg-order-bot
ExecStart=/usr/bin/python3 /path/to/tg-order-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用：
```bash
sudo systemctl enable tg-order-bot
sudo systemctl start tg-order-bot
```

### 使用 Docker

```bash
docker build -t tg-order-bot .
docker run -d --name tg-order-bot --env-file .env tg-order-bot
```

## 注意事项

1. 机器人需要有群聊消息读取权限
2. 确保 `data/images` 目录有写入权限
3. 生产环境建议使用 PostgreSQL 替代 SQLite
