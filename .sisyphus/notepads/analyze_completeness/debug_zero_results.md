# 搜索结果为0的问题排查

## 问题描述
您提到 "悉尼留学" 不可能没有笔记，但爬虫返回0条结果。这通常不是反爬虫封禁（否则会返回403/429或验证码），而是 **数据过滤** 或 **API响应结构** 的问题。

## 刚刚完成的修改
我已更新 `australia_spider_optimized.py`：
1.  **降低日志级别**：笔记无法访问时不再报 `WARNING`，而是 `INFO`，减少误报焦虑。
2.  **增加调试信息**：现在会打印 `API原始返回 X 条数据`。
    - 如果原始返回有数据，但过滤后为0 -> 说明是代码中的过滤逻辑太严格。
    - 如果原始返回就是0 -> 说明是账号/Cookie问题或API参数问题。

## 可能的原因与验证方法

### 1. 过滤逻辑过严
代码中有一行：
```python
notes = [n for n in notes if n.get('model_type') == 'note']
```
**嫌疑**：小红书API可能返回了 `model_type` 为 `video` 或 `normal` 或其他值的数据，导致被这行代码误删。
**验证**：请重新运行 `python run.py --spider --keywords 悉尼留学`，查看日志中的 "API原始返回" 数量。

### 2. 搜索接口参数问题
`apis/xhs_pc_apis.py` 中的 `search_note` 使用了：
```python
"sort": "general"
```
有时候默认排序可能会因为个性化推荐算法返回较少结果。

### 3. Cookie/账号问题
如果账号被"软封禁"（Shadowban），搜索接口可能返回空结果，但首页推荐还能看。
**建议**：尝试在浏览器中用同一个Cookie访问 `https://www.xiaohongshu.com/search_result?keyword=悉尼留学`，看是否有结果。

## 下一步建议
请再次运行：
```bash
python run.py --spider --keywords "悉尼留学"
```
观察控制台输出的 `[DEBUG] API原始返回...`。
- 如果原始返回 > 0，我将帮您调整过滤逻辑。
- 如果原始返回 = 0，我们需要检查Cookie或更换API端点。
