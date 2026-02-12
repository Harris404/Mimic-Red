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
*   🧹 **数据清洗**: 自动去除 Emoji、无意义标签，格式化为纯文本格式。
*   💾 **多格式存储**: 支持 **SQLite、CSV、JSON、Excel** 四种存储格式，满足不同使用场景。
*   🔄 **增量更新**: 自动去重，支持断点续爬。

## 🛡️ 风控与频率说明 (重要)

**⚠️ 严正警告：请勿尝试无限制的大规模爬取！**

小红书的反爬策略非常严格（2026年最新），本项目虽然使用了浏览器接管技术来降低特征，但**高频的访问行为**本身就是最大的特征。

### ✅ 推荐配置（基于2026年实测数据）

| 使用场景 | 每日上限 | 持续时间 | 风险等级 | 备注 |
|---------|---------|---------|---------|------|
| **新账号/测试期** | 50-100条/天 | 30-60分钟 | 🟢 低 | 建立信任基线 |
| **稳定运行期** | 100-150条/天 | 1-1.5小时 | 🟡 中 | **推荐配置** |
| **数据紧急需求** | 200-300条/天 | 2-2.5小时 | 🟠 高 | 需IP轮换+监控 |

*   **间隔设置**: 默认的随机延迟（10-20秒）是经过测试的安全范围，**不要刻意缩短**。
*   **时段建议**: 避开晚高峰（19:00-23:00）和午休时段（12:00-14:00），系统风控更严格。
*   **长期使用**: 建议每周至少休息1-2天，模拟真实用户行为。

### 🚫 为什么不能无限爬取？

1.  **账号安全**: 过于频繁的请求会导致账号被暂时风控（无法查看详情、搜索无结果），严重时可能封号。
2.  **IP 限制**: 同一 IP 短时间内请求过多会触发验证码或直接 403。数据中心IP（云服务器）会被立即标记。
3.  **法律风险**: 根据《中国刑法第285条》，爬取超过**100万条记录**可能构成刑事案件（3-7年有期徒刑）。
4.  **可持续性**: 细水长流。本项目旨在辅助个人研究和小规模数据收集，而非商业级的大规模采集。

### 🔴 已知检测机制（2026年）

*   **设备指纹**: IMEI、CPU频率、屏幕分辨率、已安装APP列表
*   **网络指纹**: TLS握手特征、HTTP/2请求头顺序、IP信誉评分
*   **行为分析**: 鼠标轨迹完美度、滚动速度均匀性、点击时序（<100ms触发警报）
*   **请求签名**: X-S、X-T、X-B3-Traceid等多层加密验证

**本项目优势**: 使用CDP接管真实浏览器，继承浏览器原生指纹，自动通过签名验证。但IP轮换仍需用户自行配置。

---

## 🛠️ 技术架构

| 模块 | 技术栈 | 说明 |
| :--- | :--- | :--- |
| **浏览器控制** | `DrissionPage` | 基于 CDP 协议，比 Selenium/Playwright 更快、更隐蔽 |
| **数据提取** | `SSR + DOM` | 优先提取 `__INITIAL_STATE__` JSON 数据，DOM 作为兜底 |
| **反爬对抗** | `Mimicry` | 真实浏览器接管 + 拟人化操作 + 随机延迟 |
| **数据存储** | `多格式` | 支持 SQLite/CSV/JSON/Excel 四种格式 |
| **文本处理** | `Regex` | 清洗 Emoji 和特殊字符，优化数据质量 |

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
直接双击运行 `start_chrome.bat` 脚本即可。
脚本会自动查找 Chrome 安装路径并开启调试端口。

> **⚠️ 注意**：启动后，请在浏览器中打开 `https://www.xiaohongshu.com` 并扫码登录。登录成功后，**不要关闭浏览器窗口**。

> **🍪 Cookie 说明**：
> - 本项目使用 CDP 协议接管浏览器，会自动从浏览器会话中获取 Cookie，**无需手动配置** `cookies_fresh.json` 文件。


### 3. 运行爬虫

```bash
# 基础用法：使用默认 SQLite 存储
python3 mimic_red_engine.py -k "澳洲留学"

# 使用 CSV 格式存储
python3 mimic_red_engine.py -k "澳洲留学" -s csv

# 使用 JSON 格式存储
python3 mimic_red_engine.py -k "澳洲留学" -s json

# 使用 Excel 格式存储
python3 mimic_red_engine.py -k "澳洲留学" -s excel

# 进阶用法：指定数量、每日上限、最少点赞数过滤
python3 mimic_red_engine.py -k "澳洲留学" "悉尼生活" -l 50 -d 200 --min-likes 10 -s csv

# 参数说明：
# -k, --keywords    关键词列表 (支持多个)
# -s, --storage     存储格式 (sqlite/csv/json/excel，默认: sqlite)
# -o, --output      输出目录 (默认: datas)
# -l, --limit       每个关键词爬取数量 (默认: 20)
# -d, --daily-limit 每日总爬取上限 (默认: 0 无限制)
# --min-likes       最少点赞数过滤 (跳过低质量笔记)
```

> 📖 **详细使用说明**：请查看 [使用说明](./使用说明.md) 了解更多存储格式说明和使用技巧。

---

## 📁 项目结构

```text
Mimic-Red/
├── mimic_red_engine.py      # [核心] 主爬虫引擎
├── selectors.json           # [配置] CSS选择器配置（支持热更新）
├── start_chrome.sh          # [工具] Mac/Linux 启动脚本
├── start_chrome.bat         # [工具] Windows 启动脚本
├── requirements.txt         # [依赖] 项目依赖
├── 使用说明.md               # [文档] 详细使用说明
├── sqlite_datas/            # [数据] SQLite 数据库输出
├── csv_datas/               # [数据] CSV 格式输出
├── json_datas/              # [数据] JSON 格式输出
├── excel_datas/             # [数据] Excel 格式输出
├── datas/                   # [数据] 进度和报告文件
│   ├── crawl_progress.json  # 断点续爬进度
│   └── reports/             # 爬取报告（可选）
└── xhs_utils/               # [模块] 工具库
    └── storage_manager.py   # 多格式存储管理 (SQLite/CSV/JSON/Excel)
```

---

## ⚠️ 免责声明

1.  本项目仅供 **学习和研究** 使用，请勿用于商业用途。
2.  请遵守 [小红书用户协议](https://www.xiaohongshu.com/protocal/user) 和 [Robots协议](https://www.xiaohongshu.com/robots.txt)。
3.  使用者应对使用本项目产生的一切后果负责，作者不承担任何法律责任。
4.  如需大规模采集数据，请联系小红书官方获取商业授权 API。

### 法律合规（2026年中国法规）

*   ❌ **小红书无官方API**，爬虫行为违反用户服务条款
*   ⚠️ **刑法第285条**: 非法获取计算机信息系统数据罪
*   🔴 **刑事立案红线**: 累计爬取超过 **100万条记录** 可能面临刑事追诉
*   💰 **处罚**: 罚款 + 3-7年有期徒刑（商业用途量刑更重）

**合规建议**:
*   仅用于个人学习/学术研究
*   控制总量 < 10万条
*   不得用于商业盈利、数据转售
*   不得爬取用户隐私数据（联系方式、位置等）

### 2026年代码改进说明

本版本已修复以下问题（基于健康度分析报告）：
*   ✅ 修复 21处裸 `except:` 语句，添加具体异常类型和日志
*   ✅ 锁定依赖版本 → `requirements-lock.txt`（生产环境推荐）
*   ✅ 增强 CSV/JSON 去重功能，支持跨运行加载历史文件
*   ✅ 更新反爬策略说明，基于2026年最新研究

**推荐升级**：
```bash
# 更新到最新版本
git pull origin main

# 安装锁定版本依赖（推荐）
pip install -r requirements-lock.txt
```


---

**Star ⭐ if you like it!**
