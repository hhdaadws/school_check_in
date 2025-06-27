"""
文本内容审核服务
用于检测帖子内容中的违规词汇
"""
import re
import json
from django.core.cache import cache
from django.conf import settings
from .models import ViolationWord, ModerationLog


class TextModerationService:
    """文本内容审核服务"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'MODERATION_CACHE_TIMEOUT', 3600)
        self.cache_key = 'violation_words_cache'
    
    def check_post(self, user, title, content):
        """
        检查帖子内容，返回审核结果
        
        Args:
            user: 发帖用户
            title: 帖子标题
            content: 帖子内容
            
        Returns:
            tuple: (is_valid, error_message, violations_info)
        """
        # 检查标题
        title_valid, title_violations = self.check_text(title, 'title')
        
        # 检查内容
        content_valid, content_violations = self.check_text(content, 'content')
        
        # 合并检测结果
        all_violations = title_violations + content_violations
        is_valid = title_valid and content_valid
        
        # 确定内容类型
        if title_violations and content_violations:
            content_type = 'both'
        elif title_violations:
            content_type = 'title'
        elif content_violations:
            content_type = 'content'
        else:
            content_type = 'title'  # 默认值
        
        # 记录审核日志
        action = 'approved' if is_valid else 'blocked'
        violation_category = self._get_primary_violation_category(all_violations)
        
        self._log_moderation(
            user=user,
            content_type=content_type,
            original_content=f"标题: {title}\n内容: {content[:200]}...",
            detected_words=all_violations,
            action=action,
            violation_category=violation_category
        )
        
        if not is_valid:
            error_message = self._generate_error_message(all_violations)
            return False, error_message, {
                'title_violations': title_violations,
                'content_violations': content_violations,
                'violation_category': violation_category
            }
        
        return True, "", {}
    
    def check_text(self, text, content_type='content'):
        """
        检查单个文本内容
        
        Args:
            text: 要检查的文本
            content_type: 内容类型 ('title' 或 'content')
            
        Returns:
            tuple: (is_valid, violations_list)
        """
        if not text or not text.strip():
            return True, []
        
        # 文本预处理
        normalized_text = self._normalize_text(text)
        
        # 获取违规词库
        violation_words = self._get_violation_words()
        
        violations = []
        
        for word_data in violation_words:
            is_violation = False
            word = word_data['word']
            match_type = word_data['match_type']
            pattern = word_data.get('pattern', '')
            
            try:
                if match_type == 'exact':
                    is_violation = self._exact_match(normalized_text, word)
                elif match_type == 'contains':
                    is_violation = self._contains_match(normalized_text, word)
                elif match_type == 'regex' and pattern:
                    is_violation = self._regex_match(normalized_text, pattern)
                elif match_type == 'fuzzy':
                    is_violation = self._fuzzy_match(normalized_text, word)
                
                if is_violation:
                    violations.append({
                        'word': word,
                        'category': word_data['category'],
                        'severity': word_data['severity'],
                        'match_type': match_type
                    })
                    
            except Exception as e:
                # 记录检测错误，但不阻止发帖
                print(f"检测违规词时发生错误: {word} - {str(e)}")
                continue
        
        # 根据严重程度判断是否拒绝
        is_valid = not any(v['severity'] >= 2 for v in violations)
        
        return is_valid, violations
    
    def _get_violation_words(self):
        """获取违规词库（带缓存）"""
        cached_words = cache.get(self.cache_key)
        if cached_words is not None:
            return cached_words
        
        # 从数据库获取激活的违规词
        words = ViolationWord.objects.filter(is_active=True).values(
            'word', 'pattern', 'category', 'severity', 'match_type'
        )
        words_list = list(words)
        
        # 缓存结果
        cache.set(self.cache_key, words_list, self.cache_timeout)
        
        return words_list
    
    def _normalize_text(self, text):
        """文本标准化处理"""
        if not text:
            return ""
        
        # 转换为小写
        text = text.lower()
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除常见的干扰字符
        text = re.sub(r'[\.。,，!！?？;；:：\-_\+\*#@&%\$]', '', text)
        
        return text.strip()
    
    def _exact_match(self, text, word):
        """精确匹配"""
        return word.lower() == text
    
    def _contains_match(self, text, word):
        """包含匹配"""
        return word.lower() in text
    
    def _regex_match(self, text, pattern):
        """正则表达式匹配"""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return False
    
    def _fuzzy_match(self, text, word):
        """模糊匹配（处理变形词）"""
        # 移除可能的干扰字符后再匹配
        fuzzy_text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        fuzzy_word = re.sub(r'[^\w\u4e00-\u9fff]', '', word.lower())
        
        return fuzzy_word in fuzzy_text
    
    def _get_primary_violation_category(self, violations):
        """获取主要违规类别（按严重程度）"""
        if not violations:
            return ""
        
        # 按严重程度排序，取最严重的
        sorted_violations = sorted(violations, key=lambda x: x['severity'], reverse=True)
        return sorted_violations[0]['category']
    
    def _generate_error_message(self, violations):
        """生成用户友好的错误信息"""
        if not violations:
            return "内容检测失败，请稍后重试"
        
        # 按类别分组
        categories = {}
        for v in violations:
            category = v['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(v['word'])
        
        # 生成错误信息
        messages = []
        category_names = {
            'political': '政治敏感',
            'adult': '成人内容',
            'violence': '暴力血腥',
            'advertisement': '广告推广',
            'abuse': '恶意谩骂',
            'other': '违规内容'
        }
        
        for category, words in categories.items():
            category_name = category_names.get(category, '违规内容')
            messages.append(f"检测到{category_name}相关内容")
        
        return f"发布失败：{', '.join(messages)}。请修改后重新发布。"
    
    def _log_moderation(self, user, content_type, original_content, detected_words, action, violation_category):
        """记录审核日志"""
        try:
            log = ModerationLog.objects.create(
                user=user,
                content_type=content_type,
                original_content=original_content,
                action=action,
                violation_category=violation_category
            )
            # 设置检测到的违规词
            log.set_detected_words_list(detected_words)
            log.save()
        except Exception as e:
            print(f"记录审核日志失败: {str(e)}")
    
    def clear_cache(self):
        """清除违规词缓存"""
        cache.delete(self.cache_key)
    
    @classmethod
    def refresh_cache(cls):
        """刷新违规词缓存"""
        service = cls()
        service.clear_cache()
        service._get_violation_words()


# 全局审核服务实例
moderation_service = TextModerationService() 