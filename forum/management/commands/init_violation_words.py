"""
初始化违规词库的Django管理命令
"""
from django.core.management.base import BaseCommand
from forum.models import ViolationWord


class Command(BaseCommand):
    help = '初始化违规词库数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有违规词后重新初始化',
        )

    def handle(self, *args, **options):
        if options['clear']:
            ViolationWord.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('已清除现有违规词库')
            )

        # 初始违规词数据
        initial_words = [
            # 政治敏感类
            {
                'word': '测试政治词',
                'category': 'political',
                'severity': 3,
                'match_type': 'contains',
                'pattern': ''
            },
            
            # 成人内容类
            {
                'word': '测试成人词',
                'category': 'adult',
                'severity': 3,
                'match_type': 'contains',
                'pattern': ''
            },
            
            # 暴力血腥类
            {
                'word': '暴力',
                'category': 'violence',
                'severity': 2,
                'match_type': 'contains',
                'pattern': ''
            },
            {
                'word': '血腥',
                'category': 'violence',
                'severity': 2,
                'match_type': 'contains',
                'pattern': ''
            },
            
            # 垃圾广告类（正则表达式示例）
            {
                'word': '微信号广告',
                'category': 'advertisement',
                'severity': 2,
                'match_type': 'regex',
                'pattern': r'.*微信.*\d{5,}.*'
            },
            {
                'word': 'QQ号广告',
                'category': 'advertisement',
                'severity': 2,
                'match_type': 'regex',
                'pattern': r'.*QQ.*\d{5,}.*'
            },
            {
                'word': '加群',
                'category': 'advertisement',
                'severity': 2,
                'match_type': 'contains',
                'pattern': ''
            },
            
            # 恶意谩骂类
            {
                'word': '笨蛋',
                'category': 'abuse',
                'severity': 1,  # 轻微违规，只警告
                'match_type': 'contains',
                'pattern': ''
            },
            {
                'word': '傻瓜',
                'category': 'abuse',
                'severity': 1,
                'match_type': 'contains',
                'pattern': ''
            },
            {
                'word': '垃圾',
                'category': 'abuse',
                'severity': 2,
                'match_type': 'exact',  # 精确匹配，避免误伤"垃圾分类"等正常内容
                'pattern': ''
            },
            
            # 其他违规内容
            {
                'word': '刷单',
                'category': 'other',
                'severity': 2,
                'match_type': 'contains',
                'pattern': ''
            },
            {
                'word': '代写',
                'category': 'other',
                'severity': 2,
                'match_type': 'contains',
                'pattern': ''
            },
            {
                'word': '代考',
                'category': 'other',
                'severity': 3,
                'match_type': 'contains',
                'pattern': ''
            },
            
            # 模糊匹配示例（处理变形词）
            {
                'word': '广告',
                'category': 'advertisement',
                'severity': 2,
                'match_type': 'fuzzy',
                'pattern': ''
            }
        ]

        created_count = 0
        updated_count = 0
        
        for word_data in initial_words:
            word_obj, created = ViolationWord.objects.get_or_create(
                word=word_data['word'],
                defaults={
                    'category': word_data['category'],
                    'severity': word_data['severity'],
                    'match_type': word_data['match_type'],
                    'pattern': word_data['pattern'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✓ 创建违规词: {word_data['word']}")
            else:
                # 更新现有记录
                word_obj.category = word_data['category']
                word_obj.severity = word_data['severity']
                word_obj.match_type = word_data['match_type']
                word_obj.pattern = word_data['pattern']
                word_obj.is_active = True
                word_obj.save()
                updated_count += 1
                self.stdout.write(f"↻ 更新违规词: {word_data['word']}")

        self.stdout.write(
            self.style.SUCCESS(
                f'\n初始化完成！'
                f'\n创建新违规词: {created_count} 个'
                f'\n更新违规词: {updated_count} 个'
                f'\n总计违规词: {ViolationWord.objects.filter(is_active=True).count()} 个'
            )
        )
        
        # 清除违规词缓存
        from forum.moderation import TextModerationService
        TextModerationService.refresh_cache()
        self.stdout.write(
            self.style.SUCCESS('已刷新违规词缓存')
        ) 