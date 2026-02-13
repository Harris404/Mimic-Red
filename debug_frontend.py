#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查小红书前端 DOM 结构和 CSS 选择器
用于诊断详情页空白问题
"""
import time
from DrissionPage import ChromiumPage

def check_selectors():
    print("🔍 开始检查小红书前端结构...")
    
    # 连接到已启动的 Chrome (端口 9222)
    try:
        page = ChromiumPage(addr_or_opts='127.0.0.1:9222')
        print(f"✅ 成功连接到 Chrome，当前页面: {page.url}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("请先运行 ./start_chrome.sh 启动 Chrome")
        return
    
    # 1. 访问小红书首页
    print("\n📍 步骤 1: 访问小红书首页")
    page.get('https://www.xiaohongshu.com')
    time.sleep(3)
    
    # 2. 搜索测试关键词
    print("\n📍 步骤 2: 搜索关键词 '昆士兰大学'")
    search_url = 'https://www.xiaohongshu.com/search_result?keyword=昆士兰大学&source=web_search_result_notes'
    page.get(search_url)
    time.sleep(3)
    
    # 3. 提取第一条笔记链接
    print("\n📍 步骤 3: 提取第一条笔记链接")
    first_note_js = """
    return (function() {
        const items = document.querySelectorAll('section.note-item');
        if (items.length === 0) return null;
        
        const firstItem = items[0];
        const searchLink = firstItem.querySelector('a[href*="/search_result/"]');
        const exploreLink = firstItem.querySelector('a[href*="/explore/"]');
        
        const link = searchLink || exploreLink;
        if (!link) return null;
        
        return {
            href: link.getAttribute('href'),
            title: firstItem.innerText.split('\\n')[0]
        };
    })();
    """
    
    note_info = page.run_js(first_note_js)
    if not note_info:
        print("❌ 搜索结果页没有找到笔记卡片")
        print("可能原因：")
        print("  1. 需要登录")
        print("  2. 网页结构已变化")
        print("  3. 触发了反爬验证")
        return
    
    print(f"✅ 找到笔记: {note_info['title']}")
    print(f"   链接: {note_info['href']}")
    
    # 4. 打开详情页
    print("\n📍 步骤 4: 打开笔记详情页")
    detail_url = f"https://www.xiaohongshu.com{note_info['href']}" if note_info['href'].startswith('/') else note_info['href']
    tab = page.new_tab(detail_url)
    time.sleep(4)
    
    # 5. 检查页面状态
    print("\n📍 步骤 5: 检查详情页状态")
    current_url = tab.url
    print(f"   当前 URL: {current_url}")
    
    if '404' in current_url or 'error' in current_url:
        print("❌ 详情页返回 404 错误")
        print("   原因: 缺少 xsec_token 或链接已失效")
        tab.close()
        return
    
    # 检查页面是否为空白
    body_text = tab.run_js('return document.body.innerText.substring(0, 200);')
    print(f"   页面文本前200字: {body_text}")
    
    if not body_text or len(body_text.strip()) < 10:
        print("❌ 详情页为空白")
    
    # 6. 检查 SSR 数据
    print("\n📍 步骤 6: 检查 SSR 数据 (__INITIAL_STATE__)")
    ssr_check = tab.run_js("""
    return (function() {
        if (!window.__INITIAL_STATE__) return {exists: false};
        
        const state = window.__INITIAL_STATE__;
        return {
            exists: true,
            hasNote: !!state.note,
            hasNoteDetailMap: !!(state.note && state.note.noteDetailMap),
            keys: state.note ? Object.keys(state.note.noteDetailMap || {}) : []
        };
    })();
    """)
    
    print(f"   SSR 数据存在: {ssr_check.get('exists')}")
    print(f"   note 数据: {ssr_check.get('hasNote')}")
    print(f"   noteDetailMap: {ssr_check.get('hasNoteDetailMap')}")
    print(f"   noteDetailMap keys: {ssr_check.get('keys', [])}")
    
    # 7. 检查 DOM 选择器
    print("\n📍 步骤 7: 测试现有 CSS 选择器")
    selectors_to_test = {
        '标题 (#detail-title)': '#detail-title',
        '标题 (.title)': '.title',
        '标题 ([class*="title"])': '[class*="title"]',
        '正文 (#detail-desc)': '#detail-desc',
        '正文 (.note-text)': '.note-text',
        '正文 ([class*="desc"])': '[class*="desc"]',
        '标签 (.tag-item)': '.tag-item',
        '标签 ([class*="tag"])': '[class*="tag"]',
        '评论 (.comment-item)': '.comment-item',
        '评论 ([class*="comment"])': '[class*="comment"]',
    }
    
    working_selectors = {}
    for name, selector in selectors_to_test.items():
        try:
            result = tab.run_js(f"""
            return (function() {{
                const el = document.querySelector('{selector}');
                if (!el) return null;
                return {{
                    exists: true,
                    text: el.innerText ? el.innerText.substring(0, 50) : '',
                    className: el.className,
                    id: el.id
                }};
            }})();
            """)
            
            if result:
                print(f"   ✅ {name}: 找到元素")
                print(f"      文本: {result.get('text', '')}")
                print(f"      class: {result.get('className', '')}")
                working_selectors[name] = selector
            else:
                print(f"   ❌ {name}: 未找到元素")
        except Exception as e:
            print(f"   ❌ {name}: 检测失败 ({e})")
    
    # 8. 查找所有可能的标题元素
    print("\n📍 步骤 8: 查找所有可能的标题元素")
    title_search = tab.run_js("""
    return (function() {
        const results = [];
        
        // 查找所有可能包含标题的元素
        const candidates = document.querySelectorAll('h1, h2, [class*="title"], [id*="title"]');
        
        candidates.forEach((el, idx) => {
            const text = el.innerText.trim();
            if (text && text.length > 5 && text.length < 200) {
                results.push({
                    index: idx,
                    tag: el.tagName,
                    className: el.className,
                    id: el.id,
                    text: text.substring(0, 50)
                });
            }
        });
        
        return results;
    })();
    """)
    
    if title_search:
        print(f"   找到 {len(title_search)} 个可能的标题元素:")
        for item in title_search[:5]:  # 只显示前5个
            print(f"      <{item['tag']}> class='{item['className']}' id='{item['id']}'")
            print(f"      文本: {item['text']}")
    
    # 9. 查找所有可能的正文元素
    print("\n📍 步骤 9: 查找所有可能的正文元素")
    desc_search = tab.run_js("""
    return (function() {
        const results = [];
        
        // 查找所有可能包含正文的元素
        const candidates = document.querySelectorAll('p, div[class*="desc"], div[class*="content"], div[class*="text"]');
        
        candidates.forEach((el, idx) => {
            const text = el.innerText.trim();
            if (text && text.length > 50) {  // 正文通常较长
                results.push({
                    index: idx,
                    tag: el.tagName,
                    className: el.className,
                    id: el.id,
                    textLength: text.length,
                    preview: text.substring(0, 100)
                });
            }
        });
        
        // 按文本长度降序排序
        return results.sort((a, b) => b.textLength - a.textLength);
    })();
    """)
    
    if desc_search:
        print(f"   找到 {len(desc_search)} 个可能的正文元素 (按长度排序):")
        for item in desc_search[:3]:  # 只显示前3个最长的
            print(f"      <{item['tag']}> class='{item['className']}' ({item['textLength']}字)")
            print(f"      预览: {item['preview']}...")
    
    # 10. 总结
    print("\n" + "="*60)
    print("📊 检查结果总结")
    print("="*60)
    print(f"✅ 有效选择器数量: {len(working_selectors)}")
    if working_selectors:
        print("有效的选择器:")
        for name, selector in working_selectors.items():
            print(f"  - {name}: {selector}")
    else:
        print("⚠️ 所有现有选择器都失效了")
        print("\n建议:")
        print("  1. 检查上面找到的标题和正文元素，更新选择器")
        print("  2. 优先使用 SSR 数据提取 (window.__INITIAL_STATE__)")
        print("  3. 如果 SSR 数据也没有，可能需要登录或触发了反爬")
    
    # 清理
    tab.close()
    print("\n✅ 检查完成")

if __name__ == "__main__":
    check_selectors()
