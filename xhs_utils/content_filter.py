#!/usr/bin/env python3

import re
from typing import Dict, List, Tuple


class ContentQualityFilter:
    
    LOW_QUALITY_KEYWORDS = {
        '自拍', 'OOTD', 'ootd', '穿搭', '今日穿搭', '打卡', 'vlog', 'VLOG',
        '日常', '分享日常', '随手拍', '美照', '自拍分享', '今日份',
        '颜值', '美女', '长腿', '身材', '化妆', '护肤', '种草',
        '探店', '美食', '下午茶', '咖啡', '奶茶'
    }
    
    HIGH_QUALITY_KEYWORDS = {
        '攻略', '经验', '分享经验', '建议', '推荐', '总结', '详解',
        '申请', '签证', '租房', '找房', '兼职', '实习', '求职',
        '选课', '课程', '专业', '教授', '导师', '论文', '考试',
        '生活', '适应', '文化', '交流', '社交', '朋友', '心得',
        '费用', '预算', '省钱', '开销', '账单', '税', '保险',
        '行前', '准备', '清单', '注意', '避坑', '踩坑', '提醒',
        '问答', 'Q&A', 'QA', '求助', '咨询', '请教', '有人知道'
    }
    
    USELESS_COMMENT_PATTERNS = [
        r'^[好哇哦啊呀嗯是的对耶额哈]+$',
        r'^[!！？?。.]+$',
        r'^赞+$',
        r'^👍+$',
        r'^❤️+$',
        r'^美+$',
        r'^好看+$',
        r'^羡慕+$',
        r'^加油+$',
        r'^哇+$',
        r'^可以+$',
    ]
    
    @classmethod
    def classify_note(cls, note: Dict) -> Dict:
        title = note.get('title', '')
        desc = note.get('desc', '')
        tags = note.get('tags', [])
        liked_count = note.get('liked_count', 0)
        comment_count = note.get('comment_count', 0)
        
        full_text = f"{title} {desc} {' '.join(tags)}"
        
        quality_score = 50
        category = '日常'
        reason = []
        
        high_keyword_count = sum(1 for kw in cls.HIGH_QUALITY_KEYWORDS if kw in full_text)
        low_keyword_count = sum(1 for kw in cls.LOW_QUALITY_KEYWORDS if kw in full_text)
        
        if high_keyword_count >= 2:
            quality_score += 25
            category = '攻略' if any(kw in full_text for kw in ['攻略', '经验', '总结', '详解']) else '讨论'
            reason.append(f'高价值关键词×{high_keyword_count}')
        
        if low_keyword_count >= 2:
            quality_score -= 25
            category = '自拍'
            reason.append(f'低价值关键词×{low_keyword_count}')
        
        desc_len = len(desc)
        if desc_len >= 500:
            quality_score += 15
            reason.append(f'长文本({desc_len}字)')
        elif desc_len >= 200:
            quality_score += 5
        elif desc_len < 50:
            quality_score -= 20
            reason.append(f'短文本({desc_len}字)')
        
        if comment_count > 0 and liked_count > 0:
            engagement_ratio = comment_count / liked_count
            if engagement_ratio > 0.1:
                quality_score += 10
                reason.append(f'高讨论度(评论率{engagement_ratio:.1%})')
        
        if any(tag in ['留学', '澳洲留学', 'UQ', '昆士兰大学', '布里斯班'] for tag in tags):
            quality_score += 10
            reason.append('相关标签')
        
        if re.search(r'[？?]', title):
            quality_score += 5
            category = '讨论'
            reason.append('疑问句')
        
        if re.search(r'(第\d+|Day\d+|\d+天)', title):
            quality_score -= 10
            category = '日常'
            reason.append('连载日常')
        
        comment_target = {
            '自拍': 30,
            '日常': 60,
            '讨论': 120,
            '攻略': 200
        }.get(category, 80)
        
        should_skip = quality_score < 30
        
        return {
            'quality_score': max(0, min(100, quality_score)),
            'category': category,
            'should_skip': should_skip,
            'comment_target': comment_target,
            'reason': ' | '.join(reason) if reason else '默认'
        }
    
    @classmethod
    def is_valuable_comment(cls, comment: Dict) -> Tuple[bool, str]:
        content = comment.get('content', '').strip()
        like_count = comment.get('like_count', 0)
        
        if not content:
            return False, '空内容'
        
        content_clean = re.sub(r'[^\w\s]', '', content)
        
        for pattern in cls.USELESS_COMMENT_PATTERNS:
            if re.match(pattern, content):
                return False, '无意义短语'
        
        emoji_count = len(re.findall(r'[\U0001F000-\U0001F9FF]', content))
        text_count = len(content_clean)
        
        if emoji_count > 0 and text_count == 0:
            return False, '纯emoji'
        
        repeat_char = re.findall(r'(.)\1{6,}', content)
        if repeat_char:
            return False, '重复字符'
        
        if like_count >= 3:
            return True, f'高赞({like_count})'
        
        if len(content) >= 10:
            return True, f'有效评论({len(content)}字)'
        
        if any(kw in content for kw in ['推荐', '建议', '可以试试', '我觉得', '个人经验', '分享', '补充', '同意', '谢谢', '感谢', '有用', '赞同']):
            return True, '有价值关键词'
        
        if re.search(r'[？?]', content):
            return True, '疑问句'
        
        if re.search(r'[！!]', content) and len(content) >= 5:
            return True, '感叹句'
        
        return True, '保留'
    
    @classmethod
    def filter_comments(cls, comments: List[Dict], target_count: int = 50) -> Tuple[List[Dict], Dict]:
        if not comments:
            return [], {'total': 0, 'kept': 0, 'filtered': 0}
        
        filtered_comments = []
        
        for comment in comments:
            is_valuable, reason = cls.is_valuable_comment(comment)
            
            if is_valuable:
                filtered_comments.append(comment)
        
        filtered_comments.sort(
            key=lambda c: (c.get('like_count', 0), len(c.get('content', ''))),
            reverse=True
        )
        
        final_comments = filtered_comments[:target_count]
        
        return final_comments, {
            'total': len(comments),
            'kept': len(final_comments),
            'filtered': len(comments) - len(final_comments)
        }
