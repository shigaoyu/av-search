# AV Resource Searcher (AV 资源搜索下载器)

一个现代化的“番号下载器”，支持多源聚合、智能排序及远程下载管理。

## 🌟 核心功能

- **现代化 Premium UI**: 基于 Plus Jakarta Sans 字体与 Zinc 色调的暗色/白天模式切换。
- **毛玻璃效果 (Glassmorphism)**: 顶部导航栏与搜索区域采用 `backdrop-filter` 模糊效果，视觉质感出众。
- **智能图片代理 (防盗链解决)**: 使用 `wsrv.nl` 全局代理与 `referrerpolicy` 策略，彻底解决 JAVBus 封面加载失败问题。
- **多语言支持 (i18n)**: 支持中英文一键切换，偏好自动保存。
- **智能排序与筛选**: 番号/有码/无码/中文字幕全维度筛选，支持按热度(种子数)、发布日期、文件大小排序。
- **一键磁力下载**: 快速唤起本地下载器（迅雷/BitComet）或一键复制磁力链接。
- **搜索历史**: 自动记录最近搜索关键词，支持快速回找。

## 🛠️ 环境要求

- Python 3.12+
- Aria2 (可选，用于远程下载)
- 本地代理工具 (如 Clash, v2ray, 默认端口 7890)

## 🚀 快速开始

### 1. 克隆项目与安装依赖

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境（可选）

在项目根目录下创建一个 `.env` 文件（可选），或直接修改 `config.py`。

```env
# 代理配置
PROXY=http://127.0.0.1:7890

# Aria2 配置
ARIA2_RPC_URL=http://localhost:6800/rpc
ARIA2_SECRET=your_aria2_token
```

### 3. 启动应用

```bash
python app.py
```

访问 `http://localhost:5001` 即可开始使用。

## 📁 项目结构

- `app.py`: Flask 主程序与 API 接口。
- `config.py`: 项目全局配置文件。
- `engine/`: 爬虫引擎目录。
- `templates/`: 前端 HTML 模板。
- `static/`: 静态资源文件。
- `requirements.txt`: Python 依赖库列表。

---

_本项目仅供技术交流与学习使用。_
