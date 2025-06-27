"""
从文件批量导入违规词的Django管理命令
"""
import json
import csv
from django.core.management.base import BaseCommand
from forum.models import ViolationWord


class Command(BaseCommand):
    help = '从文件批量导入违规词'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='违规词文件路径（支持CSV或JSON格式）',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            default='csv',
            help='文件格式（csv或json）',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        file_format = options['format']
        
        try:
            if file_format == 'csv':
                self.import_from_csv(file_path)
            elif file_format == 'json':
                self.import_from_json(file_path)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'文件不存在: {file_path}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'导入失败: {str(e)}')
            )

    def import_from_csv(self, file_path):
        """从CSV文件导入违规词"""
        self.stdout.write(f'正在从CSV文件导入: {file_path}')
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # CSV格式：word,category,severity,match_type,pattern
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                try:
                    word = row['word'].strip()
                    category = row.get('category', 'other')
                    severity = int(row.get('severity', 2))
                    match_type = row.get('match_type', 'contains')
                    pattern = row.get('pattern', '')
                    
                    word_obj, created = ViolationWord.objects.get_or_create(
                        word=word,
                        defaults={
                            'category': category,
                            'severity': severity,
                            'match_type': match_type,
                            'pattern': pattern,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(f'✓ 创建: {word}')
                    else:
                        word_obj.category = category
                        word_obj.severity = severity
                        word_obj.match_type = match_type
                        word_obj.pattern = pattern
                        word_obj.save()
                        updated_count += 1
                        self.stdout.write(f'↻ 更新: {word}')
                        
                except (ValueError, KeyError) as e:
                    error_count += 1
                    self.stdout.write(f'✗ 错误: {row} - {str(e)}')
        
        self.print_summary(created_count, updated_count, error_count)

    def import_from_json(self, file_path):
        """从JSON文件导入违规词"""
        self.stdout.write(f'正在从JSON文件导入: {file_path}')
        
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for item in data:
            try:
                word = item['word'].strip()
                category = item.get('category', 'other')
                severity = int(item.get('severity', 2))
                match_type = item.get('match_type', 'contains')
                pattern = item.get('pattern', '')
                
                word_obj, created = ViolationWord.objects.get_or_create(
                    word=word,
                    defaults={
                        'category': category,
                        'severity': severity,
                        'match_type': match_type,
                        'pattern': pattern,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'✓ 创建: {word}')
                else:
                    word_obj.category = category
                    word_obj.severity = severity
                    word_obj.match_type = match_type
                    word_obj.pattern = pattern
                    word_obj.save()
                    updated_count += 1
                    self.stdout.write(f'↻ 更新: {word}')
                    
            except (ValueError, KeyError) as e:
                error_count += 1
                self.stdout.write(f'✗ 错误: {item} - {str(e)}')
        
        self.print_summary(created_count, updated_count, error_count)

    def print_summary(self, created_count, updated_count, error_count):
        """打印导入摘要"""
        self.stdout.write(
            self.style.SUCCESS(
                f'\n导入完成！'
                f'\n创建新违规词: {created_count} 个'
                f'\n更新违规词: {updated_count} 个'
                f'\n错误记录: {error_count} 个'
                f'\n总计违规词: {ViolationWord.objects.filter(is_active=True).count()} 个'
            )
        )
        
        # 刷新缓存
        from forum.moderation import TextModerationService
        TextModerationService.refresh_cache()
        self.stdout.write(
            self.style.SUCCESS('已刷新违规词缓存')
        )
