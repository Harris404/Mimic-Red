# Mimic-Red 

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![DrissionPage](https://img.shields.io/badge/DrissionPage-4.1.0+-orange.svg)

---

## 📖 项目简介

**Mimic-Red** 是一款针对小红书网页版的高性能、低风险数据采集工具。

与传统的 `Playwright/Selenium` 自动化方案或 `Requests` 纯协议逆向方案不同，**Mimic-Red** 采用 **CDP (Chrome DevTools Protocol)** 接管真实浏览器，通过 **DOM 交互** 和 **SSR (Server-Side Rendering) 数据提取** 技术，实现对小红书数据的无感采集。

### 核心特性

*   🕷️ **拟态采集 (Mimicry)**: 接管真实用户打开的 Chrome 浏览器，复用真实指纹、Cookies 和 LocalStorage，极难被反爬系统检测。
*   👻 **幽灵模式 (Ghost Mode)**: 采用 **"新标签页 (New Tab)"** 模式打开详情页，采集完成后自动关闭，完美模拟用户“后台打开”行为，避免页面刷新和历史记录污染。
*   🚀 **被动 SSR 提取**: 直接解析网页 `window.__INITIAL_STATE__` 数据，获取服务端原始数据（包含未显示的字段），速度快且数据完整。
*   🛡️ **智能风控**: 内置 `_smart_delay` (智能延迟)、`_random_mouse_move` (贝塞尔曲线鼠标轨迹) 和 **视频笔记自动过滤**，大幅降低封号风险。
*   🧹 **数据清洗**: 自动去除 Emoji、无意义标签，并将内容格式化为适合 **RAG (Retrieval-Augmented Generation)** 的纯文本格式。
*   💾 **增量更新**: 支持 SQLite 数据库存储，自动去重，支持断点续爬。

---

## 🛠️ 技术架构

| 模块 | 技术栈 | 说明 |
| :--- | :--- | :--- |
| **浏览器控制** | `DrissionPage` | 基于 CDP 协议，比 Selenium/Playwright 更快、更隐蔽 |
| **数据提取** | `SSR + DOM` | 优先提取 `__INITIAL_STATE__` JSON 数据，DOM 作为兜底 |
| **反爬对抗** | `Mimicry` | 真实浏览器接管 + 拟人化操作 + 随机延迟 |
| **数据存储** | `SQLite` | 轻量级关系型数据库，无需配置 MySQL |
| **文本处理** | `Regex` | 清洗 Emoji 和特殊字符，优化 RAG 检索效果 |

---

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.10+ 和 Google Chrome 浏览器。

```bash
# 克隆项目
git clone https://github.com/your-repo/Mimic-Red.git
cd Mimic-Red

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动 Chrome (调试模式)

你需要启动一个开启远程调试端口 (9222) 的 Chrome 浏览器，并手动登录小红书。

**Mac/Linux:**
```bash
chmod +x start_chrome.sh
./start_chrome.sh
```

**Windows:**
请手动创建快捷方式，添加参数：
`--remote-debugging-port=9222 --user-data-dir="C:\ChromeProfile"`

> **⚠️ 注意**：启动后，请在浏览器中打开 `https://www.xiaohongshu.com` 并扫码登录。登录成功后，**不要关闭浏览器窗口**。

> **🍪 Cookie 说明**：
> - 本项目使用 CDP 协议接管浏览器，会自动从浏览器会话中获取 Cookie，**无需手动配置** `cookies_fresh.json` 文件。
> - `cookies_fresh.json` 文件仅作为示例模板，实际运行时会自动从已登录的 Chrome 浏览器中读取认证信息。
> - 请勿将真实的 Cookie 文件上传到 GitHub，已通过 `.gitignore` 规则排除。

### 3. 运行爬虫

```bash
# 基础用法：搜索关键词并爬取 (默认限制20条)
python3 mimic_red_engine.py -k "澳洲留学"

# 进阶用法：指定数量、每日上限、最少点赞数过滤
python3 mimic_red_engine.py -k "澳洲留学" "悉尼生活" -l 50 -d 200 --min-likes 10

# 参数说明：
# -k, --keywords    关键词列表 (支持多个)
# -l, --limit       每个关键词爬取数量 (默认: 20)
# -d, --daily-limit 每日总爬取上限 (默认: 0 无限制)
# --min-likes       最少点赞数过滤 (跳过低质量笔记)
# --db              从数据库读取关键词 (datas/keywords.db)
```

---

## 📂 项目结构

```text
Mimic-Red/
├── mimic_red_engine.py      # [核心] 主爬虫引擎
├── start_chrome.sh          # [工具] Chrome 调试启动脚本
├── requirements.txt         # [依赖] 项目依赖
├── datas/                   # [数据]
│   ├── notes.db             # SQLite 数据库 (存储笔记/评论)
│   ├── keywords.db          # 关键词管理库
│   └── crawl_progress.json  # 断点续爬进度
├── xhs_utils/               # [模块] 工具库
│   ├── note_manager.py      # 数据库操作
│   └── rag_util.py          # RAG 数据处理
└── logs/                    # [日志] 运行日志
```

---

## ⚠️ 免责声明

1.  本项目仅供 **学习和研究** 使用，请勿用于商业用途。
2.  请遵守 [小红书用户协议](https://www.xiaohongshu.com/protocal/user) 和 [Robots协议](https://www.xiaohongshu.com/robots.txt)。
3.  使用者应对使用本项目产生的一切后果负责，作者不承担任何法律责任。
4.  如需大规模采集数据，请联系小红书官方获取商业授权 API。

---

## 📝 更新日志

*   **v2.0 (Mimic-Red)**:
    *   重构为 DrissionPage 架构，移除 Playwright。
    *   新增“新标签页模式”，大幅降低反爬风险。
    *   新增视频笔记自动过滤功能。
    *   优化文本清洗算法，支持 RAG 数据格式导出。
*   **v1.0 (Spider-XHS)**:
    *   基于 Playwright 的初始版本 (已停止维护)。

---

**Star ⭐ if you like it!**
