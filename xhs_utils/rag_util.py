#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, List


def extract_rag_fields(note_info: Dict) -> Dict:
    """
    为RAG需求精简笔记字段，只保留文本和元数据
    
    保留字段:
    - 文本内容: title, desc, tags
    - 元数据: note_id, user_id, nickname, upload_time
    - 互动数据: liked_count, collected_count, comment_count
    - 分类信息: keyword_source, city_category, domain_category
    - 评论内容: comments_text (用于RAG检索)
    
    剔除字段:
    - 媒体文件: image_list, video_addr, video_cover, avatar
    - URL: note_url, home_url
    - 次要数据: share_count, ip_location
    """
    rag_optimized = {
        "note_id": note_info.get("note_id", ""),
        "title": note_info.get("title", ""),
        "desc": note_info.get("desc", ""),
        "tags": note_info.get("tags", []),
        
        "user_id": note_info.get("user_id", ""),
        "nickname": note_info.get("nickname", ""),
        "upload_time": note_info.get("upload_time", ""),
        
        "liked_count": note_info.get("liked_count", 0),
        "collected_count": note_info.get("collected_count", 0),
        "comment_count": note_info.get("comment_count", 0),
        "total_interaction": note_info.get("total_interaction", 0),
        
        "keyword_source": note_info.get("keyword_source", ""),
        "matrix_category": note_info.get("matrix_category", ""),
        "city_category": note_info.get("city_category", ""),
        "domain_category": note_info.get("domain_category", ""),
        "traffic_level": note_info.get("traffic_level", ""),
        
        "note_type": note_info.get("note_type", ""),
        
        "comments_data": note_info.get("comments_data", []),
        "comments_text": note_info.get("comments_text", ""),
        "high_quality_comments_count": note_info.get("high_quality_comments_count", 0),
    }
    
    return rag_optimized


def filter_high_quality_comments(comments: List[Dict], min_like_count: int = 5) -> List[Dict]:
    """
    筛选高质量评论
    
    高质量标准:
    1. 点赞数 >= min_like_count
    2. 或者评论长度 >= 20字（说明有实质内容）
    3. 限制前20条
    
    Args:
        comments: 原始评论列表
        min_like_count: 最小点赞数阈值
        
    Returns:
        高质量评论列表
    """
    quality_comments = []
    
    for comment in comments:
        try:
            like_count = int(comment.get("like_count", 0))
        except (ValueError, TypeError):
            like_count = 0
            
        content = comment.get("content", "")
        
        is_high_quality = (
            like_count >= min_like_count or 
            len(content) >= 20
        )
        
        if is_high_quality:
            quality_comments.append({
                "content": content,
                "like_count": like_count,
                "author_name": comment.get("author_name", ""),
                "create_time": comment.get("create_time", ""),
            })
    
    return quality_comments[:20]


def aggregate_comments_text(comments: List[Dict]) -> str:
    """
    将评论内容聚合为一段文本，用于RAG检索和关键词发现
    
    格式: [评论者]评论内容 | [评论者]评论内容 | ...
    """
    if not comments:
        return ""
    
    comment_parts = []
    for comment in comments:
        author = comment.get("author_name", "匿名")
        content = comment.get("content", "")
        if content:
            comment_parts.append(f"[{author}]{content}")
    
    return " | ".join(comment_parts)
