from django.core.management.base import BaseCommand
from accounts.models import InterestTag

class Command(BaseCommand):
    help = '初始化兴趣标签数据'

    def handle(self, *args, **options):
        tags = [
            # 学习类
            {'name': '编程技术', 'category': '学习', 'color': '#007bff', 'description': '编程、开发、代码相关内容'},
            {'name': '数据科学', 'category': '学习', 'color': '#28a745', 'description': '数据分析、机器学习、统计学'},
            {'name': '前端开发', 'category': '学习', 'color': '#fd7e14', 'description': 'HTML、CSS、JavaScript、前端框架'},
            {'name': '后端开发', 'category': '学习', 'color': '#6f42c1', 'description': '服务器开发、数据库、API设计'},
            {'name': '人工智能', 'category': '学习', 'color': '#e83e8c', 'description': 'AI、深度学习、神经网络'},
            {'name': '算法数据结构', 'category': '学习', 'color': '#20c997', 'description': '算法、数据结构、竞赛编程'},
            {'name': '系统设计', 'category': '学习', 'color': '#17a2b8', 'description': '架构设计、系统优化、分布式'},
            {'name': '数学', 'category': '学习', 'color': '#ffc107', 'description': '高等数学、线性代数、概率统计'},
            {'name': '英语', 'category': '学习', 'color': '#dc3545', 'description': '英语学习、口语、阅读写作'},
            
            # 技术工具类
            {'name': 'Git版本控制', 'category': '工具', 'color': '#f8f9fa', 'description': 'Git、GitHub、版本管理'},
            {'name': 'Docker容器', 'category': '工具', 'color': '#495057', 'description': 'Docker、容器化、部署'},
            {'name': 'Linux系统', 'category': '工具', 'color': '#343a40', 'description': 'Linux、Shell、服务器运维'},
            {'name': '数据库', 'category': '工具', 'color': '#6c757d', 'description': 'MySQL、PostgreSQL、MongoDB'},
            
            # 生活类
            {'name': '健身运动', 'category': '生活', 'color': '#28a745', 'description': '健身、跑步、运动相关'},
            {'name': '美食烹饪', 'category': '生活', 'color': '#fd7e14', 'description': '烹饪、美食、食谱分享'},
            {'name': '旅行摄影', 'category': '生活', 'color': '#17a2b8', 'description': '旅行、摄影、风景记录'},
            {'name': '音乐', 'category': '生活', 'color': '#e83e8c', 'description': '音乐、乐器、音乐制作'},
            {'name': '阅读', 'category': '生活', 'color': '#6f42c1', 'description': '读书、文学、知识分享'},
            {'name': '电影电视', 'category': '生活', 'color': '#dc3545', 'description': '电影、电视剧、影评'},
            
            # 兴趣爱好类
            {'name': '游戏', 'category': '娱乐', 'color': '#007bff', 'description': '电子游戏、手游、游戏开发'},
            {'name': '动漫', 'category': '娱乐', 'color': '#fd7e14', 'description': '动画、漫画、二次元文化'},
            {'name': '设计', 'category': '创作', 'color': '#e83e8c', 'description': 'UI设计、平面设计、创意设计'},
            {'name': '写作', 'category': '创作', 'color': '#6f42c1', 'description': '创作写作、小说、文章'},
            {'name': '绘画', 'category': '创作', 'color': '#20c997', 'description': '绘画、插画、数字艺术'},
            
            # 职业发展类
            {'name': '求职面试', 'category': '职业', 'color': '#495057', 'description': '求职技巧、面试经验、职场规划'},
            {'name': '创业', 'category': '职业', 'color': '#ffc107', 'description': '创业经验、商业模式、投资'},
            {'name': '职场技能', 'category': '职业', 'color': '#6c757d', 'description': '沟通技巧、团队协作、领导力'},
            
            # 其他
            {'name': '科技资讯', 'category': '资讯', 'color': '#17a2b8', 'description': '科技新闻、行业动态、产品评测'},
            {'name': '学术研究', 'category': '学术', 'color': '#343a40', 'description': '学术论文、研究方法、科研经验'},
        ]
        
        created_count = 0
        for tag_data in tags:
            tag, created = InterestTag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'category': tag_data['category'],
                    'color': tag_data['color'],
                    'description': tag_data['description']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'创建兴趣标签: {tag.name}'))
            else:
                self.stdout.write(f'标签已存在: {tag.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'初始化完成！共创建 {created_count} 个新标签')
        ) 