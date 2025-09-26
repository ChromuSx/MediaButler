# 🎬 MediaButler - Telegram 媒体整理机器人

<div align="center">
  <img src="logo.png" alt="MediaButler" width="200">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/docker-ready-brightgreen.svg" alt="Docker Ready">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/telegram-bot-blue.svg" alt="Telegram Bot">
</p>

<p align="center">
  <strong>模块化 Telegram 机器人，自动整理你的媒体库</strong>
</p>

<p align="center">
  <a href="README.md">🇺🇸 English</a> | <b>🇨🇳 简体中文</b>
</p>

## ✨ 功能亮点

- 🎬 **智能整理** - 自动为电影和电视剧创建文件夹
- 📺 **剧集识别** - 识别季/集模式（S01E01、1x01 等）
- 🎯 **TMDB 集成** - 元数据、海报和自动重命名
- 📁 **结构清晰** - 电影独立文件夹，剧集按季整理
- ⏳ **队列管理** - 多任务下载，支持配置并发数
- 💾 **空间监控** - 实时磁盘空间管理，自动队列
- 👥 **多用户** - 白名单授权系统
- 🔄 **高可用** - 支持断点续传和自动重试
- 🐳 **Docker 支持** - 一键 Docker Compose 部署

## 🏗️ 架构

本项目采用模块化架构，便于维护和扩展：

```
mediabutler/
├── main.py                 # 主入口
├── core/                   # 核心系统模块
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── auth.py            # 授权管理
│   ├── downloader.py      # 下载与队列管理
│   ├── space_manager.py   # 磁盘空间监控
│   └── tmdb_client.py     # TMDB API 客户端
├── handlers/              # Telegram 事件处理
│   ├── __init__.py
│   ├── commands.py        # 命令处理（/start, /status 等）
│   ├── callbacks.py       # 按钮回调处理
│   └── files.py           # 文件接收与识别
├── models/                # 数据模型
│   ├── __init__.py
│   └── download.py        # 下载信息数据类
├── utils/                 # 工具与辅助
│   ├── __init__.py
│   ├── naming.py          # 文件名解析与管理
│   ├── formatters.py      # 消息格式化
│   └── helpers.py         # 通用辅助
└── requirements.txt       # 依赖列表
```

### 📦 主要模块说明

#### Core
- **`config`**: 配置管理与校验
- **`auth`**: 多用户授权与管理员
- **`downloader`**: 下载队列、重试与错误处理
- **`space_manager`**: 空间监控与智能清理
- **`tmdb_client`**: TMDB 集成与限流

#### Handlers
- **`commands`**: 所有机器人命令（`/start`、`/status`、`/space` 等）
- **`callbacks`**: 按钮与交互管理
- **`files`**: 文件识别与处理

#### Utils
- **`naming`**: 智能文件名解析与结构生成
- **`formatters`**: Telegram 消息格式化与进度条
- **`helpers`**: 重试、校验、限流、异步辅助

## 🚀 快速开始

### 前置条件

- Python 3.8+ 或 Docker
- Telegram API 凭证（[my.telegram.org](https://my.telegram.org)）
- BotFather 机器人令牌（[@BotFather](https://t.me/botfather)）
- （可选）TMDB API Key

### 推荐：Docker 部署

1. **克隆仓库**：
```bash
git clone https://github.com/yourusername/mediabutler.git
cd mediabutler
```

2. **配置环境变量**：
```bash
cp .env.example .env
nano .env  # 填写你的凭证
```

3. **Docker Compose 启动**：
```bash
docker-compose up -d
```

### 手动安装

1. **创建 Python 虚拟环境**：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

2. **安装依赖**：
```bash
pip install -r requirements.txt
```

3. **配置并启动**：
```bash
cp .env.example .env
nano .env  # 配置凭证
python main.py
```

## 📖 配置说明

### 主要环境变量

```env
# Telegram（必填）
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=abcdef123456
TELEGRAM_BOT_TOKEN=123456:ABC-DEF

# TMDB（可选）
TMDB_API_KEY=your_tmdb_api_key
TMDB_LANGUAGE=en-US

# 路径
MOVIES_PATH=/media/movies
TV_PATH=/media/tv
TEMP_PATH=/media/temp

# 授权用户
AUTHORIZED_USERS=123456789,987654321

# 限制
MAX_CONCURRENT_DOWNLOADS=3
MIN_FREE_SPACE_GB=5
WARNING_THRESHOLD_GB=10
```

详见 .env.example 获取全部配置项。

## 🎯 使用方法

### 机器人命令

| 命令           | 说明                       | 权限    |
|----------------|----------------------------|---------|
| `/start`       | 启动机器人并显示信息       | 所有用户 |
| `/status`      | 显示活跃下载和队列         | 所有用户 |
| `/space`       | 显示磁盘空间详情           | 所有用户 |
| `/waiting`     | 显示等待空间的文件         | 所有用户 |
| `/cancel_all`  | 取消所有下载               | 所有用户 |
| `/help`        | 显示命令帮助               | 所有用户 |
| `/users`       | 列出授权用户               | 管理员   |
| `/stop`        | 停止机器人                 | 管理员   |

### 下载流程

1. **发送/转发** 视频文件到机器人
2. 机器人**分析**文件名并搜索 TMDB
3. **确认**或选择电影/剧集
4. 剧集可**选择季数**
5. **自动下载**或进入队列

### 文件夹结构示例

```
/media/
├── movies/
│   ├── Avatar (2009)/
│   │   └── Avatar (2009).mp4
│   └── Inception (2010)/
│       └── Inception (2010).mp4
└── tv/
    ├── Breaking Bad [EN]/
    │   ├── Season 01/
    │   │   ├── Breaking Bad - S01E01 - Pilot.mp4
    │   │   └── Breaking Bad - S01E02 - Cat's in the Bag.mp4
    │   └── Season 02/
    └── The Office/
        └── Season 04/
```

## 🔧 开发

### 扩展机器人

模块化设计，便于添加新功能：

#### 新增命令

1. 在 commands.py 中添加方法：
```python
async def mycommand_handler(self, event):
    """Handler for /mycommand"""
    if not await self.auth.check_authorized(event):
        return
    
    # 命令逻辑
    await event.reply("Command response")
```

2. 在 `register()` 注册：
```python
self.client.on(events.NewMessage(pattern='/mycommand'))(self.mycommand_handler)
```

#### 新增元数据源

1. 在 core 新建模块：
```python
# core/metadata_provider.py
class MetadataProvider:
    async def search(self, query: str):
        # 实现搜索
        pass
```

2. 在 `FileHandlers` 或相关位置集成

### 测试

```bash
# 单元测试
python -m pytest tests/

# 覆盖率测试
python -m pytest --cov=core --cov=handlers --cov=utils tests/
```

### 代码风格

遵循 PEP 8：
```bash
# 格式化
black .

# 代码检查
flake8 . --max-line-length=100

# 类型检查
mypy .
```

## 🐳 Docker

### 构建镜像

```bash
docker build -t mediabutler:latest .
```

### 自定义 Docker Compose

```yaml
version: '3.8'

services:
  mediabutler:
    image: mediabutler:latest
    container_name: mediabutler
    restart: unless-stopped
    env_file: .env
    volumes:
      - ${MOVIES_PATH}:/media/movies
      - ${TV_PATH}:/media/tv
      - ./session:/app/session
    networks:
      - media_network

networks:
  media_network:
    external: true
```

## 📊 监控

### 日志

```bash
# Docker 日志
docker logs -f mediabutler

# 日志文件（如配置）
tail -f logs/mediabutler.log
```

### 指标

通过 `/status` 命令可查看：
- 活跃下载
- 队列文件
- 可用空间
- 下载速度

## 🚧 路线图

- [ ] Web 管理界面
- [ ] Jellyfin/Plex 集成
- [ ] 字幕支持
- [ ] 播放列表/频道下载
- [ ] 通知自定义
- [ ] 配置备份/恢复
- [ ] REST API 集成
- [ ] 完整多语言支持

## 🤝 贡献

欢迎贡献！详见 CONTRIBUTING.md。

1. Fork 本项目
2. 创建分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证，详见 LICENSE。

## 🙏 鸣谢

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram MTProto 客户端
- [TMDB](https://www.themoviedb.org) - 元数据库
- [aiohttp](https://github.com/aio-libs/aiohttp) - 异步 HTTP 客户端
- 自托管社区 ❤️

## ⚠️ 免责声明

本机器人仅供个人使用。请遵守版权法规，仅下载您有权获取的内容。

---

<p align="center">
  为自托管社区开发 ❤️
</p>