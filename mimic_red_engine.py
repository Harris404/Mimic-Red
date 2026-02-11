# -*- coding: utf-8 -*-
"""
DrissionPage 版小红书批量爬虫 (多格式存储版)
核心策略：移除所有 API 监听 (降低特征) -> 纯 DOM 交互 (点击/滚动) -> 被动 SSR/DOM 提取
支持存储格式：CSV、JSON、Excel、SQLite
"""
import sys
import time
import random
import json
import os
import hashlib
import argparse
from datetime import datetime
from typing import List, Dict, Optional

from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

# 配置日志轮转
logger.add(
    "logs/spider_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜轮转
    retention="7 days", # 保留7天
    level="INFO",
    encoding="utf-8"
)

# 加载 CSS 选择器配置
SELECTORS = {}
try:
    with open('selectors.json', 'r', encoding='utf-8') as f:
        SELECTORS = json.load(f)
except Exception as e:
    logger.warning(f"⚠️ 未找到 selectors.json 或加载失败 ({e})，将使用默认硬编码选择器")

# 导入新的存储管理器
try:
    from xhs_utils.storage_manager import StorageManager
except ImportError as e:
    logger.error(f"导入依赖失败: {e}")
    sys.exit(1)

class DataDeduplicator:
    def __init__(self, storage_manager: StorageManager = None):
        self.storage = storage_manager
        self.local_seen = set()
    
    def is_duplicate(self, note_id: str) -> bool:
        # 1. 检查本次运行的内存缓存
        if note_id in self.local_seen:
            return True
            
        # 2. 检查持久化存储 (SQLite)
        if self.storage and self.storage.note_exists(note_id):
            self.local_seen.add(note_id) # 更新本地缓存
            return True
            
        self.local_seen.add(note_id)
        return False

import re

class DrissionXHSSpider:
    def __init__(self, storage_type: str = "sqlite", output_dir: str = "datas", takeover: bool = True):
        self.storage_type = storage_type
        self.output_dir = output_dir
        self.takeover = takeover
        self.page = None
        self.storage = None
        self.deduplicator = None
        self.stats = {"total_notes": 0, "failed_keywords": 0, "start_time": None}
        
        # 反爬控制
        self._consecutive_failures = 0
        self._request_count = 0
        self._blocked_count = 0

    def init_browser(self):
        """初始化浏览器"""
        if not self.takeover:
            logger.error("❌ 推荐使用接管模式 (takeover=True) 以降低风险")
            sys.exit(1)
            
        logger.info("🚀 尝试接管 Chrome (9222)...")
        try:
            self.page = ChromiumPage(addr_or_opts='127.0.0.1:9222')
            current_url = self.page.url or ''
            logger.info(f"   ✅ 接管成功，当前页面: {current_url[:60]}...")
            
            if 'xiaohongshu.com' not in current_url:
                self.page.get('https://www.xiaohongshu.com')
                time.sleep(2)
        except Exception as e:
            logger.error(f"   ❌ 接管失败: {e}")
            sys.exit(1)
        
        try:
            self.storage = StorageManager(self.storage_type, self.output_dir)
            self.deduplicator = DataDeduplicator(self.storage)
            logger.info(f"   ✅ 存储管理器已初始化 ({self.storage_type.upper()})")
        except Exception as e:
            logger.error(f"   ❌ 存储管理器初始化失败: {e}")


    def _warmup_session(self):
        """
        会话预热：模拟真实用户先随意浏览再开始爬取
        建立正常的行为基线，降低被风控检测的概率
        """
        logger.info("🎯 会话预热中（模拟正常浏览 30-60秒）...")
        try:
            # 1. 访问首页并滚动浏览
            self.page.get('https://www.xiaohongshu.com')
            time.sleep(random.uniform(3, 5))
            
            # 2. 随意滚动首页 feed
            for _ in range(random.randint(2, 4)):
                self._random_mouse_move()
                self._human_like_scroll('down', random.randint(300, 600))
                time.sleep(random.uniform(2, 4))
            
            # 3. 随机点击一篇推荐笔记看看（建立“正常用户”模式）
            try:
                feed_link = self.page.run_js("""
                    const links = document.querySelectorAll('section.note-item a[href*="/explore/"]');
                    if (links.length > 0) {
                        const idx = Math.floor(Math.random() * Math.min(links.length, 5));
                        return links[idx].href;
                    }
                    return null;
                """)
                if feed_link:
                    self.page.get(feed_link)
                    time.sleep(random.uniform(4, 8))  # “阅读”几秒
                    self._human_like_scroll('down', random.randint(200, 500))
                    time.sleep(random.uniform(2, 4))
            except:
                pass
            
            # 4. 回到首页
            self.page.get('https://www.xiaohongshu.com')
            time.sleep(random.uniform(2, 4))
            
            logger.info("✅ 预热完成，开始爬取")
        except Exception as e:
            logger.debug(f"预热异常: {e}")

    def _load_progress(self) -> tuple[set, int]:
        """加载已完成的关键词和今日爬取计数（支持断点续爬）"""
        progress_file = 'datas/crawl_progress.json'
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    data = json.load(f)
                # 只保留当天的进度
                today = datetime.now().strftime('%Y-%m-%d')
                if data.get('date') == today:
                    return set(data.get('done_keywords', [])), data.get('daily_count', 0)
            except:
                pass
        return set(), 0

    def _save_progress(self, done_keywords: set, daily_count: int):
        """保存爬取进度"""
        progress_file = 'datas/crawl_progress.json'
        try:
            with open(progress_file, 'w') as f:
                json.dump({
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'done_keywords': list(done_keywords),
                    'daily_count': daily_count,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False)
        except:
            pass

    def _random_mouse_move(self):
        """模拟人类随机鼠标移动（贝塞尔曲线轨迹）"""
        try:
            # 获取当前鼠标位置（或随机起点）
            start_x = random.randint(200, 600)
            start_y = random.randint(200, 500)
            end_x = random.randint(300, 900)
            end_y = random.randint(200, 600)
            
            # 模拟贝塞尔曲线移动（分多步）
            steps = random.randint(5, 12)
            for i in range(steps):
                t = i / steps
                # 简化的二次贝塞尔曲线
                ctrl_x = (start_x + end_x) / 2 + random.randint(-50, 50)
                ctrl_y = (start_y + end_y) / 2 + random.randint(-80, 80)
                x = int((1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * end_x)
                y = int((1-t)**2 * start_y + 2*(1-t)*t * ctrl_y + t**2 * end_y)
                
                try:
                    self.page.actions.move_to((x, y), duration=random.uniform(0.02, 0.08))
                except: pass
                time.sleep(random.uniform(0.01, 0.05))
        except: pass

    def _human_like_scroll(self, direction: str = 'down', distance: int = None):
        """模拟人类滚动行为"""
        try:
            if distance is None:
                distance = random.randint(300, 600)
            
            # 分多次小滚动
            scroll_times = random.randint(2, 4)
            per_scroll = distance // scroll_times
            
            for _ in range(scroll_times):
                if direction == 'down':
                    self.page.scroll.down(per_scroll + random.randint(-30, 30))
                else:
                    self.page.scroll.up(per_scroll + random.randint(-30, 30))
                time.sleep(random.uniform(0.1, 0.3))
        except: pass

    def _smart_delay(self, action: str = 'detail'):
        """智能延迟：根据时段、请求次数、连续失败动态调节"""
        self._request_count += 1
        
        # 基础延迟（秒）
        delays = {
            'detail': (10, 15),      # 笔记详情间隔
            'search': (3, 6),       # 搜索页滚动间隔
            'keyword': (20, 40),    # 关键词切换间隔
        }
        low, high = delays.get(action, (5, 10))
        
        # 时段系数：晚高峰加倍，凌晨减少
        hour = time.localtime().tm_hour
        if 19 <= hour <= 23:
            low, high = int(low * 1.8), int(high * 1.8)
        elif 0 <= hour <= 7:
            low, high = int(low * 0.7), int(high * 0.7)
        
        # 每 20 次请求强制长休息
        if self._request_count % 20 == 0:
            rest = random.uniform(45, 90)
            logger.info(f"   ⏸️ 已访问 {self._request_count} 次，强制休息 {rest:.0f}秒...")
            time.sleep(rest)
            return
        
        # 连续失败指数退避
        if self._consecutive_failures > 0:
            backoff = min(self._consecutive_failures * 10, 120)
            low += backoff
            high += backoff
        
        delay = random.uniform(low, high)
        time.sleep(delay)

    def _check_blocked(self) -> bool:
        """检测是否被反爬拦截"""
        try:
            url = self.page.url or ''
            text = self.page.run_js('return document.body.innerText.substring(0, 500);') or ''
            
            if any(kw in text for kw in ['验证', '安全检查', '操作频繁', '请稍后再试']):
                self._blocked_count += 1
                self._consecutive_failures += 1
                logger.warning(f"   🛑 检测到反爬限制×{self._blocked_count}！暂停 2-4 分钟...")
                time.sleep(random.uniform(120, 240))
                # 尝试返回首页重建会话
                self.page.get('https://www.xiaohongshu.com')
                time.sleep(random.uniform(5, 10))
                return True
            
            if '404' in url or 'error' in url:
                return True
        except:
            pass
        return False

    def _safe_int(self, value) -> int:
        try:
            if isinstance(value, int): return value
            if isinstance(value, str):
                v = value.strip()
                if '万' in v: return int(float(v.replace('万', '')) * 10000)
                if 'w' in v.lower(): return int(float(v.lower().replace('w', '')) * 10000)
                return int(v)
            return 0
        except: return 0

    def search_notes(self, keyword: str, max_count: int = 20) -> List[Dict]:
        """搜索列表 - 提取带 xsec_token 的链接"""
        logger.info(f"🔍 搜索: {keyword}")
        
        from urllib.parse import quote
        self.page.get(f'https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_search_result_notes')
        time.sleep(3)
        
        collected = []
        seen_ids = set()  # 本次搜索的去重
        page_num = 1
        
        while len(collected) < max_count and page_num <= 8:
            # 提取笔记卡片信息 - 关键：获取带 xsec_token 的 search_result 链接
            # 动态注入选择器
            search_item_sel = SELECTORS.get('search_note_item', 'section.note-item')
            title_sels = SELECTORS.get('search_note_title', '.title, .note-title, [class*="title"]')
            author_sels = SELECTORS.get('search_note_author', '.author, .nickname, [class*="name"]')
            
            js_extract = f"""
            return (function() {{
                const items = document.querySelectorAll('{search_item_sel}');
                const results = [];
                
                items.forEach((item, index) => {{
                    // 优先获取带 xsec_token 的 search_result 链接（反爬必要）
                    const searchLink = item.querySelector('a[href*="/search_result/"]');
                    const exploreLink = item.querySelector('a[href*="/explore/"]');
                    
                    if (!searchLink && !exploreLink) return;
                    
                    // 优先使用 search_result 链接（带 xsec_token）
                    const primaryLink = searchLink || exploreLink;
                    const href = primaryLink.getAttribute('href');
                    const exploreHref = exploreLink ? exploreLink.getAttribute('href') : null;
                    
                    // 提取标题
                    let title = '';
                    const titleSels = '{title_sels}'.split(', ');
                    for (const sel of titleSels) {{
                        const titleEl = item.querySelector(sel);
                        if (titleEl) {{
                            title = titleEl.innerText;
                            break;
                        }}
                    }}
                    if (!title) title = (item.innerText || '').split('\\n')[0];
                    
                    // 提取作者
                    let author = '';
                    const authorSels = '{author_sels}'.split(', ');
                    for (const sel of authorSels) {{
                        const authorEl = item.querySelector(sel);
                        if (authorEl) {{
                            author = authorEl.innerText;
                            break;
                        }}
                    }}
                    
                    results.push({{
                        index: index,
                        href: href,
                        exploreHref: exploreHref,
                        title: title.substring(0, 100),
                        author: author
                    }});
                }});
                return JSON.stringify(results);
            }})();
            """
            
            try:
                res = self.page.run_js(js_extract)
                if res:
                    items = json.loads(res)
                    new_this_round = 0
                    for item in items:
                        href = item.get('href', '')
                        # 从 href 提取 note_id（兼容 explore 和 search_result 格式）
                        note_id = href.split('/')[-1].split('?')[0]
                        if note_id and note_id not in seen_ids:
                            seen_ids.add(note_id)
                            if not self.deduplicator.is_duplicate(note_id):
                                # 构建完整 URL（优先带 xsec_token 的 search_result）
                                full_url = f"https://www.xiaohongshu.com{href}" if href.startswith('/') else href
                                collected.append({
                                    'note_id': note_id,
                                    'title': item['title'],
                                    'author_name': item['author'],
                                    'url': full_url,
                                    'explore_url': f"https://www.xiaohongshu.com{item['exploreHref']}" if item.get('exploreHref') else None,
                                })
                                new_this_round += 1
                    if new_this_round > 0:
                        logger.info(f"   📊 第{page_num}轮收集: +{new_this_round} 条 (总计: {len(collected)})")
            except Exception as e:
                logger.debug(f"提取异常: {e}")
            
            if len(collected) >= max_count: break
            
            # 模拟人类：随机鼠标移动 + 滚动
            self._random_mouse_move()
            self._human_like_scroll('down', random.randint(400, 700))
            time.sleep(random.uniform(1.5, 3))
            page_num += 1
            
        return collected[:max_count]

    def get_note_detail_pure(self, note_info: Dict) -> Optional[Dict]:
        """获取笔记详情 - 直接访问带 xsec_token 的URL（最可靠方式）"""
        note_id = note_info['note_id']
        logger.info(f"   📖 获取详情: {note_info['title'][:25]}...")
        
        # ========== 核心策略：直接访问带 xsec_token 的URL ==========
        # 小红书现在要求所有访问都携带 xsec_token，否则返回404
        detail_url = note_info['url']
        
        # 模拟人类：先随机移动鼠标
        self._random_mouse_move()
        time.sleep(random.uniform(0.3, 0.8))
        
        # 直接导航到详情页 (新标签页模式)
        tab = self.page.new_tab(detail_url)
        time.sleep(random.uniform(2, 3.5))
        
        # 检查是否被拦截
        current_url = tab.url or ''
        if '404' in current_url or 'error' in current_url:
            logger.warning(f"   ⚠️ 详情页被拦截(404)，尝试explore链接")
            # 如果有备用的 explore URL，尝试使用
            explore_url = note_info.get('explore_url')
            if explore_url:
                tab.get(explore_url)
                time.sleep(3)
                current_url = tab.url or ''
                if '404' in current_url:
                    logger.warning(f"   ❌ explore链接也被拦截，跳过此笔记")
                    tab.close()
                    return note_info  # 返回基础信息
            else:
                logger.warning(f"   ❌ 无备用链接，跳过此笔记")
                tab.close()
                return note_info

        # 等待详情页加载
        time.sleep(2)
        
        detail_data = {}
        comments = []

        # ====== 第一步：SSR 提取（必须在任何DOM操作之前！）======
        # 关闭弹窗的JS会误触发笔记关闭按钮，导致Vue组件卸载、SSR数据清空
        # 所以必须先提取SSR数据，再做其他DOM操作
        try:
            ssr_js = f"""
            return (function() {{
                try {{
                    const state = window.__INITIAL_STATE__;
                    if (!state || !state.note || !state.note.noteDetailMap) return null;
                    
                    // 1. 精确查找
                    let entry = state.note.noteDetailMap['{note_id}'];
                    
                    // 2. 模糊查找（页面可能用不同的key）
                    if (!entry || !(entry.note || entry.desc)) {{
                        const keys = Object.keys(state.note.noteDetailMap);
                        for (const k of keys) {{
                            const e = state.note.noteDetailMap[k];
                            if (e && (e.note?.desc || e.desc)) {{
                                entry = e;
                                break;
                            }}
                        }}
                    }}
                    
                    if (!entry) return null;
                    const note = entry.note || entry;
                    
                    // 手动提取字段（避免 Vue Proxy 序列化问题）
                    const result = {{
                        title: note.title || '',
                        desc: note.desc || '',
                        type: note.type || 'normal',
                        noteId: note.noteId || '',
                        time: note.time || 0,
                        lastUpdateTime: note.lastUpdateTime || 0,
                        tagList: [],
                        interactInfo: {{}}
                    }};
                    
                    // 提取标签
                    if (note.tagList && note.tagList.length) {{
                        note.tagList.forEach(t => {{
                            result.tagList.push({{name: t.name || '', id: t.id || ''}});
                        }});
                    }}
                    
                    // 提取互动数据
                    const interact = note.interactInfo || {{}};
                    result.interactInfo = {{
                        likedCount: interact.likedCount || '0',
                        collectedCount: interact.collectedCount || '0',
                        commentCount: interact.commentCount || '0',
                        shareCount: interact.shareCount || '0'
                    }};
                    
                    // 提取用户信息
                    if (note.user) {{
                        result.user = {{
                            nickname: note.user.nickname || '',
                            userId: note.user.userId || note.user.id || ''
                        }};
                    }}
                    
                    // 提取图片列表
                    if (note.imageList && note.imageList.length) {{
                        result.imageCount = note.imageList.length;
                    }}
                    
                    return JSON.stringify(result);
                }} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
            }})();
            """
            res = tab.run_js(ssr_js)
            if res:
                data = json.loads(res)
                detail_data = data
                logger.info(f"   ✅ SSR 被动提取: desc={len(data.get('desc', ''))}字")
                
                # 过滤视频笔记
                if detail_data.get('type') == 'video':
                    tab.close()
                    return {'skipped': True, 'reason': 'video'}
        except: pass
        
        # ====== 第二步：DOM操作（关闭弹窗、展开全文、滚动加载评论）======
        # 这些操作可能导致Vue组件状态变化，必须在SSR提取之后
        
        # 关闭可能的遮罩/登录弹窗（排除笔记详情的关闭按钮）
        try:
            tab.run_js("""
                document.querySelectorAll('.login-close, [class*="login"] [class*="close"]').forEach(e => {
                    if (e.offsetWidth > 0) e.click();
                });
            """)
        except: pass
        
        # 展开全文
        try:
            tab.run_js("""
                const expand = document.querySelector('#detail-desc span.expand');
                if (expand) expand.click();
            """)
            time.sleep(0.5)
        except: pass
        
        # 滚动加载评论（多次渐进滚动，尝试多种滚动容器）
        try:
            for scroll_pos in [600, 1200, 1800, 2500, 3500]:
                tab.run_js(f"""
                    // 尝试多种可能的滚动容器
                    const scrollers = [
                        document.querySelector('.note-scroller'),
                        document.querySelector('.note-container'),
                        document.querySelector('#noteContainer'),
                        document.querySelector('[class*="detail"] [class*="scroll"]'),
                        document.querySelector('[class*="comment"]')?.closest('[style*="overflow"]'),
                        document.documentElement
                    ];
                    for (const scroller of scrollers) {{
                        if (scroller) {{
                            scroller.scrollTop = {scroll_pos};
                            break;
                        }}
                    }}
                    // 同时尝试 window 滚动
                    window.scrollTo(0, {scroll_pos});
                """)
                time.sleep(random.uniform(1.0, 2.0))
        except: pass

        # ====== 第三步：DOM 提取（SSR失败时的保底）======
        if not detail_data.get('desc'):
            try:
                dom_extract = """
                return (function() {
                    const res = {};
                    // 正文
                    const descEl = document.querySelector('#detail-desc') || document.querySelector('.note-text');
                    res.desc = descEl ? descEl.innerText : '';
                    // 标题
                    const titleEl = document.querySelector('.note-detail-mask .title') || document.querySelector('#detail-title');
                    res.title = titleEl ? titleEl.innerText : '';
                    // 标签
                    res.tags = Array.from(document.querySelectorAll('.tag-item')).map(e => e.innerText.replace('#',''));
                    // 时间
                    const dateEl = document.querySelector('.date');
                    res.time = dateEl ? dateEl.innerText : '';
                    return JSON.stringify(res);
                })();
                """
                dom_res = tab.run_js(dom_extract)
                if dom_res:
                    dom_data = json.loads(dom_res)
                    if dom_data.get('desc'):
                        detail_data.update(dom_data)
                        logger.info(f"   ✅ DOM 提取: desc={len(dom_data['desc'])}字")
            except: pass
            
        # ====== 第四步：评论提取（SSR优先 + DOM兜底）======
        
        # 4a. SSR 评论提取（最可靠 - 从 __INITIAL_STATE__ 获取）
        try:
            ssr_comments_js = f"""
            return (function() {{
                try {{
                    const state = window.__INITIAL_STATE__;
                    if (!state) return null;
                    
                    const coms = [];
                    
                    // 方式1：从 comment.commentsMap 提取
                    if (state.comment) {{
                        let commentData = null;
                        
                        // 尝试不同的数据路径
                        if (state.comment.commentsMap) {{
                            commentData = state.comment.commentsMap['{note_id}'];
                            if (!commentData) {{
                                const keys = Object.keys(state.comment.commentsMap);
                                if (keys.length > 0) commentData = state.comment.commentsMap[keys[0]];
                            }}
                        }}
                        
                        // 尝试 comments 数组
                        if (!commentData && state.comment.comments) {{
                            commentData = state.comment.comments;
                        }}
                        
                        if (commentData) {{
                            const commentList = Array.isArray(commentData) ? commentData : (commentData.comments || []);
                            commentList.forEach((c, idx) => {{
                                const content = c.content || c.text || '';
                                const author = c.userInfo?.nickname || c.user?.nickname || c.nickname || '匿名';
                                const likeCount = parseInt(c.likeCount || c.like_count || c.likes || 0);
                                const commentId = c.id || c.commentId || c.comment_id || '';
                                const contentLen = content.length;
                                
                                // 只保留有价值的评论（≥10字 或 点赞≥3）
                                if (content && (contentLen >= 10 || likeCount >= 3)) {{
                                    coms.push({{content, author_name: author, like_count: likeCount, comment_id: commentId, is_sub: false}});
                                }}
                                
                                // 提取子评论/回复（更有价值，往往是补充信息）
                                const subComments = c.subComments || c.subCommentList || c.replies || c.sub_comment_list || [];
                                subComments.forEach(sc => {{
                                    const subContent = sc.content || sc.text || '';
                                    const subAuthor = sc.userInfo?.nickname || sc.user?.nickname || sc.nickname || '匿名';
                                    const subLike = parseInt(sc.likeCount || sc.like_count || 0);
                                    const subId = sc.id || sc.commentId || '';
                                    const subLen = subContent.length;
                                    // 二级评论更宽松：≥8字或点赞≥2
                                    if (subContent && (subLen >= 8 || subLike >= 2)) {{
                                        coms.push({{content: subContent, author_name: subAuthor, like_count: subLike, comment_id: subId, is_sub: true}});
                                    }}
                                }});
                            }});
                        }}
                    }}
                    
                    // 方式2：从 noteDetailMap 中提取评论相关数据
                    if (coms.length === 0 && state.note && state.note.noteDetailMap) {{
                        const keys = Object.keys(state.note.noteDetailMap);
                        for (const k of keys) {{
                            const entry = state.note.noteDetailMap[k];
                            const note = entry?.note || entry;
                            if (note && note.comments) {{
                                note.comments.forEach(c => {{
                                    const content = c.content || c.text || '';
                                    const author = c.userInfo?.nickname || c.nickname || '匿名';
                                    if (content) {{
                                        coms.push({{content, author_name: author, like_count: parseInt(c.likeCount || 0), comment_id: c.id || ''}});
                                    }}
                                }});
                            }}
                        }}
                    }}
                    
                    return coms.length > 0 ? JSON.stringify(coms) : null;
                }} catch(e) {{ return null; }}
            }})();
            """
            ssr_c_res = tab.run_js(ssr_comments_js)
            if ssr_c_res:
                ssr_comments = json.loads(ssr_c_res)
                if ssr_comments:
                    # 统计一级和二级评论
                    primary = sum(1 for c in ssr_comments if not c.get('is_sub'))
                    sub = sum(1 for c in ssr_comments if c.get('is_sub'))
                    comments = ssr_comments
                    logger.info(f"   💬 SSR评论提取: {len(comments)}条 (一级{primary}+二级{sub})")
        except Exception as e:
            logger.debug(f"SSR评论提取异常: {e}")
        
        # 4b. DOM 评论提取（SSR失败时的兜底，使用多种选择器）
        if not comments:
            try:
                comments_js = """
                return (function() {
                    const coms = [];
                    const seen = new Set();
                    
                    // 多种评论选择器（兼容不同版本的小红书前端）
                    const selectors = [
                        '.comment-item',
                        '.comment-inner-container',
                        '[class*="commentItem"]',
                        '[class*="comment-item"]',
                        '.parent-comment',
                        '[class*="CommentItem"]'
                    ];
                    
                    let commentEls = [];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {
                            commentEls = els;
                            break;
                        }
                    }
                    
                    commentEls.forEach((el, idx) => {
                        // 多种内容选择器
                        let content = '';
                        const contentSels = ['.content', '.note-text', '[class*="content"]', '[class*="text"]', 'p'];
                        for (const sel of contentSels) {
                            const contentEl = el.querySelector(sel);
                            if (contentEl && contentEl.innerText.trim()) {
                                content = contentEl.innerText.trim();
                                break;
                            }
                        }
                        
                        // 多种作者选择器
                        let author = '匿名';
                        const authorSels = ['.name', '.author', '.nickname', '.user-name', '[class*="name"]', '[class*="author"]'];
                        for (const sel of authorSels) {
                            const authorEl = el.querySelector(sel);
                            if (authorEl && authorEl.innerText.trim()) {
                                author = authorEl.innerText.trim();
                                break;
                            }
                        }
                        
                        // 多种点赞数选择器
                        let likeNum = 0;
                        const likeSels = ['.like-count', '.like span', '[class*="like"] span', '[class*="count"]'];
                        for (const sel of likeSels) {
                            const likeEl = el.querySelector(sel);
                            if (likeEl) {
                                const likeText = likeEl.innerText.trim();
                                if (likeText.includes('万')) {
                                    likeNum = Math.round(parseFloat(likeText) * 10000);
                                } else {
                                    likeNum = parseInt(likeText) || 0;
                                }
                                break;
                            }
                        }
                        
                        // 去重 + 质量过滤（基于内容）
                        if (content && !seen.has(content)) {
                            // 只保留有价值的评论：≥10字 或 点赞≥3
                            if (content.length >= 10 || likeNum >= 3) {
                                seen.add(content);
                                coms.push({content, author_name: author, like_count: likeNum});
                            }
                        }
                    });
                    
                    // 按点赞数降序
                    coms.sort((a, b) => b.like_count - a.like_count);
                    return JSON.stringify(coms);
                })();
                """
                c_res = tab.run_js(comments_js)
                if c_res:
                    dom_comments = json.loads(c_res)
                    if dom_comments:
                        comments = dom_comments
                        avg_len = sum(len(c.get('content', '')) for c in comments) / len(comments) if comments else 0
                        logger.info(f"   💬 DOM评论提取: {len(comments)}条 (平均{avg_len:.0f}字)")
            except Exception as e:
                logger.debug(f"DOM评论提取异常: {e}")

        # 退出详情
        try:
            tab.close()
        except: pass
        time.sleep(0.5)
        
        # 组装
        full_note = note_info.copy()
        full_note['desc'] = detail_data.get('desc', '')
        full_note['title'] = detail_data.get('title', full_note.get('title', ''))
        
        # 提取标签（兼容 tagList 和 tags 两种格式）
        raw_tags = detail_data.get('tagList', detail_data.get('tags', []))
        if raw_tags and isinstance(raw_tags[0], dict):
            full_note['tags'] = [t.get('name', '') for t in raw_tags if t.get('name')]
        elif raw_tags:
            full_note['tags'] = raw_tags
        else:
            full_note['tags'] = []
             
        full_note['time'] = str(detail_data.get('time', detail_data.get('lastUpdateTime', detail_data.get('last_update_time', ''))))
        
        # 互动数据（兼容 interactInfo 和 interact_info）
        interact = detail_data.get('interactInfo', detail_data.get('interact_info', {}))
        full_note['liked_count'] = self._safe_int(interact.get('likedCount', interact.get('liked_count', 0)))
        full_note['collected_count'] = self._safe_int(interact.get('collectedCount', interact.get('collected_count', 0)))
        full_note['comment_count'] = self._safe_int(interact.get('commentCount', interact.get('comment_count', 0)))
        
        # 计算总互动量和流量等级（用于RAG筛选优质内容）
        total_interaction = full_note['liked_count'] + full_note['collected_count'] + full_note['comment_count']
        full_note['total_interaction'] = total_interaction
        
        # 流量等级分类（爆款/优质/普通/低质）
        if total_interaction >= 10000:
            full_note['traffic_level'] = '爆款'
        elif total_interaction >= 1000:
            full_note['traffic_level'] = '优质'
        elif total_interaction >= 100:
            full_note['traffic_level'] = '普通'
        else:
            full_note['traffic_level'] = '低质'
        
        # 提取作者信息（author_id）
        user_info = detail_data.get('user', {})
        if user_info:
            full_note['author_id'] = user_info.get('userId', '')
            full_note['author_name'] = user_info.get('nickname', full_note.get('author_name', ''))
        
        # 评论后处理：质量筛选 + 生成唯一ID
        if comments:
            # 按价值排序：优先长评论和高赞评论
            comments_sorted = sorted(comments, key=lambda c: (len(c.get('content', '')), c.get('like_count', 0)), reverse=True)
            # 保留前50条最有价值的（避免过多低质量评论）
            comments = comments_sorted[:50]
            
            # 为每条评论生成唯一ID
            for idx, c in enumerate(comments):
                if not c.get('comment_id'):
                    content_hash = hashlib.md5(f"{note_id}_{c.get('content', '')}_{idx}".encode()).hexdigest()[:12]
                    c['comment_id'] = f"{note_id}_{content_hash}"
        
        full_note['comments_data'] = comments
        full_note['full_text'] = f"{full_note['title']} {full_note['desc']} {' '.join(full_note['tags'])}"
        
        return full_note

    def _clean_text(self, text: str) -> str:
        """清洗文本：去除Emoji、无意义标签、多余空格"""
        if not text:
            return ""
            
        # 1. 去除Emoji (保留常见标点)
        # 这是一个简单的范围，覆盖大多数Emoji
        try:
            # 过滤掉非BMP字符（通常是Emoji）
            text = "".join(c for c in text if c <= "\uFFFF")
        except: pass
        
        # 2. 规范化标签格式: #标签 -> [标签]
        text = re.sub(r'#(\S+)', r'[\1]', text)
        
        # 3. 去除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _to_storage_note(self, note: Dict) -> Dict:
        """转换为标准存储格式"""
        clean_title = self._clean_text(note.get('title', ''))
        clean_desc = self._clean_text(note.get('desc', ''))
        clean_tags = [self._clean_text(t) for t in note.get('tags', [])]
        
        # 重新组合 full_text
        full_text = f"{clean_title} {clean_desc} {' '.join(clean_tags)}"
        
        return {
            'note_id': note.get('note_id', ''),
            'url': note.get('url', ''),
            'title': note.get('title', ''),
            'desc': note.get('desc', ''),
            'note_type': note.get('type', 'normal'),
            'author_name': note.get('author_name', ''),
            'author_id': note.get('author_id', ''),
            'liked_count': note.get('liked_count', 0),
            'collected_count': note.get('collected_count', 0),
            'comment_count': note.get('comment_count', 0),
            'total_interaction': note.get('total_interaction', 0),
            'traffic_level': note.get('traffic_level', ''),
            'tags': note.get('tags', []),
            'upload_time': str(note.get('time', '')),
            'full_text': full_text,
            'keyword_source': note.get('keyword_source', '')
        }

    def crawl(self, keywords: List[str], limit: int = 20, daily_limit: int = 0,
              min_likes: int = 0, warmup: bool = True, shuffle: bool = True):
        """
        批量爬取
        
        Args:
            keywords: 关键词列表
            limit: 每个关键词最多爬取笔记数
            daily_limit: 每日最多爮取总数（0=无限制）
            min_likes: 最少点赞数过滤（跳过低互动笔记减少请求）
            warmup: 是否预热会话
            shuffle: 是否随机打乱关键词顺序
        """
        self.stats["start_time"] = datetime.now()
        self.init_browser()
        
        # 加载进度（支持断点续爬）
        done_keywords, loaded_daily_count = self._load_progress()
        if done_keywords:
            original_count = len(keywords)
            keywords = [kw for kw in keywords if kw not in done_keywords]
            if original_count > len(keywords):
                logger.info(f"📂 断点续爬: 跳过已完成的 {original_count - len(keywords)} 个关键词")
        
        if not keywords:
            logger.info("✅ 所有关键词已完成，无需重复爬取")
            return
        
        # 随机打乱关键词顺序（避免系统性扫描特征）
        if shuffle:
            random.shuffle(keywords)
            logger.info(f"🎲 已随机打乱 {len(keywords)} 个关键词顺序")
        
        # 会话预热
        if warmup:
            self._warmup_session()
        
        daily_count = loaded_daily_count  # 恢复当日已爬取数
        if daily_count > 0:
            logger.info(f"📊 今日已爬取 {daily_count} 条，继续累计...")
        
        for i, kw in enumerate(keywords):
            # 每日上限检查
            if daily_limit > 0 and daily_count >= daily_limit:
                logger.info(f"\n📊 已达到每日上限 {daily_limit} 条，今日爬取结束")
                logger.info(f"   剩余 {len(keywords) - i} 个关键词将在下次运行时继续")
                break
            
            logger.info(f"\n📍 进度: {i+1}/{len(keywords)} | 关键词: {kw} | 今日已爬: {daily_count}")
            
            # 关键词间冷却（第一个关键词不等）
            if i > 0:
                self._smart_delay('keyword')
            
            # 熔断检查：连续失败太多则暂停
            if self._consecutive_failures >= 5:
                pause = random.uniform(180, 300)
                logger.warning(f"   🛑 连续失败 {self._consecutive_failures} 次，熔断休息 {pause:.0f}秒...")
                time.sleep(pause)
                self._consecutive_failures = 0
                # 重建会话
                self.page.get('https://www.xiaohongshu.com')
                time.sleep(5)
            
            notes = self.search_notes(kw, limit)
            
            if not notes:
                self._consecutive_failures += 1
                self.stats["failed_keywords"] += 1
                logger.warning(f"   ⚠️ 无搜索结果，跳过")
                continue
            
            self._consecutive_failures = 0  # 搜索成功则重置
            
            kw_note_count = 0
            for j, note in enumerate(notes):
                # 每日上限检查
                if daily_limit > 0 and daily_count >= daily_limit:
                    break
                
                logger.info(f"   📖 [{j+1}/{len(notes)}] {note['title'][:30]}...")
                
                # 反爬检测
                if self._check_blocked():
                    logger.warning(f"   ⚠️ 触发反爬，本关键词剩余笔记跳过")
                    break
                
                # 访问详情页获取完整数据
                full_note = self.get_note_detail_pure(note)
                
                # 跳过被标记的笔记（如视频）
                if full_note and full_note.get('skipped'):
                    logger.info(f"      ⏭️ 跳过视频笔记")
                    continue
                
                if full_note and self.storage:
                    # 最少点赞过滤（减少无效请求）
                    liked = full_note.get('liked_count', 0)
                    if min_likes > 0 and liked < min_likes:
                        logger.debug(f"      ⏭️ 点赞{liked}<{min_likes}，跳过低互动笔记")
                        continue
                    
                    # 记录关键词来源
                    full_note['keyword_source'] = kw
                    
                    storage_note = self._to_storage_note(full_note)
                    self.storage.add_note(storage_note)
                    if full_note.get('comments_data'):
                        self.storage.add_comments(full_note['note_id'], full_note['comments_data'])
                    self.stats["total_notes"] += 1
                    daily_count += 1
                    kw_note_count += 1
                    desc_len = len(full_note.get('desc', ''))
                    comment_cnt = len(full_note.get('comments_data', []))
                    if desc_len > 0:
                        self._consecutive_failures = 0
                        logger.info(f"      ✅ 正文: {desc_len}字 | ❤️{liked} | 💬{comment_cnt}条")
                    else:
                        self._consecutive_failures += 1
                        comment_cnt = len(full_note.get('comments_data', []))
                        logger.warning(f"      ⚠️ 未获取到正文 | 💬{comment_cnt}条评论")
                else:
                    self._consecutive_failures += 1
                
                # 智能延迟（根据时段/请求次数/失败率动态调节）
                self._smart_delay('detail')
            
            # 标记关键词完成并保存进度
            done_keywords.add(kw)
            self._save_progress(done_keywords, daily_count)
            
            logger.info(f"   ✅ 关键词「{kw}」完成: 收录 {kw_note_count} 条")
            
            # 每 3 个关键词后额外休息
            if (i + 1) % 3 == 0 and i + 1 < len(keywords):
                rest = random.uniform(30, 60)
                logger.info(f"   ☕ 每3个关键词休息 {rest:.0f}秒...")
                time.sleep(rest)

        self._print_stats(daily_count, daily_limit)
        
        # 完成存储（JSON/Excel 需要最终写入）
        if self.storage:
            self.storage.finalize()
        
        
    def _print_stats(self, daily_count: int = 0, daily_limit: int = 0):
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()
        limit_info = f"  每日上限: {daily_count}/{daily_limit}\n" if daily_limit > 0 else ""
        logger.info(
            f"\n{'#'*60}\n"
            f"# 📊 爬取结束\n"
            f"  收录笔记数: {self.stats['total_notes']}\n"
            f"{limit_info}"
            f"  失败关键词: {self.stats['failed_keywords']}\n"
            f"  触发反爬: {self._blocked_count} 次\n"
            f"  总耗时: {duration/60:.1f} 分钟\n"
            f"{'#'*60}"
        )

def main():
    parser = argparse.ArgumentParser(description='DrissionPage 小红书爬虫 (多格式存储版)')
    parser.add_argument('--keywords', '-k', nargs='+', help='关键词列表')
    parser.add_argument('--limit', '-l', type=int, default=20, help='每个关键词最多爬取数量')
    parser.add_argument('--daily-limit', '-d', type=int, default=0,
                        help='每日最多爬取总数（0=无限制，推荐 50-100）')
    parser.add_argument('--min-likes', type=int, default=0,
                        help='最少点赞数过滤（跳过低互动笔记，减少请求）')
    parser.add_argument('--storage', '-s', type=str, default='sqlite',
                        choices=['csv', 'json', 'excel', 'sqlite'],
                        help='存储格式 (csv/json/excel/sqlite，默认: sqlite)')
    parser.add_argument('--output', '-o', type=str, default='datas',
                        help='输出目录（默认: datas）')
    parser.add_argument('--no-warmup', action='store_true', help='跳过会话预热')
    parser.add_argument('--no-shuffle', action='store_true', help='不打乱关键词顺序')
    args = parser.parse_args()
    
    spider = DrissionXHSSpider(storage_type=args.storage, output_dir=args.output)
    keywords = args.keywords if args.keywords else ["澳洲留学"]
    
    logger.info(f"📦 存储格式: {args.storage.upper()}")
    logger.info(f"📂 输出目录: {args.output}")
        
    spider.crawl(
        keywords, limit=args.limit,
        daily_limit=args.daily_limit,
        min_likes=args.min_likes,
        warmup=not args.no_warmup,
        shuffle=not args.no_shuffle
    )

if __name__ == "__main__":
    main()
