from channels.generic.websocket import AsyncWebsocketConsumer
import json
from accounts.models import User
from django.utils import timezone
from .models import ChatMessage
import logging
from urllib.parse import parse_qs
from asgiref.sync import sync_to_async

# 获取logger
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 从URL路径获取房间名
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        logger.info(f"收到WebSocket连接请求: room_name={self.room_name}, room_group_name={self.room_group_name}")
        
        # 从查询字符串获取用户名
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['匿名用户'])[0]
        
        logger.info(f"用户 {self.username} 正在连接到房间 {self.room_name}")
        
        # 加入聊天室组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket连接成功: {self.channel_name} 加入 {self.room_group_name}")
        await self.accept()
        
    async def disconnect(self, close_code):
        logger.info(f"WebSocket断开连接: code={close_code}, room_name={self.room_name}")
        
        # 通知房间有用户离开
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': f"{self.username} 离开了聊天室",
                    'sender': 'system',
                    'timestamp': timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"发送离开消息失败: {str(e)}")
        
        # 离开聊天室组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
            sender = text_data_json['sender']
            
            # 生成当前时间戳
            timestamp = timezone.now()
            message_id = None
            
            logger.info(f"收到消息: sender={sender}, message={message[:30]}...(截断), room={self.room_name}")
            
            # 保存消息到数据库
            if sender != 'system':
                try:
                    # 保存消息并获取消息ID
                    saved_message = await self.save_message(sender, message, self.room_name, timestamp)
                    message_id = saved_message.id
                    logger.info(f"消息已保存到数据库: id={message_id}, sender={sender}, room={self.room_name}")
                except Exception as e:
                    logger.error(f"保存消息失败: {str(e)}")
            
            # 发送消息到聊天室组
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': sender,
                    'timestamp': timestamp.isoformat(),
                    'id': message_id
                }
            )
            logger.info(f"消息已发送到群组: {self.room_group_name}")
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
            await self.send(text_data=json.dumps({
                'message': '消息处理失败，请重试',
                'sender': 'system',
                'timestamp': timezone.now().isoformat()
            }))
    
    @sync_to_async
    def save_message(self, sender_username, content, room_name, timestamp):
        try:
            user = User.objects.get(username=sender_username)
            message = ChatMessage.objects.create(
                sender=user,
                content=content,
                room_name=room_name,
                timestamp=timestamp
            )
            return message
        except User.DoesNotExist:
            logger.error(f"用户不存在: {sender_username}")
            raise
    
    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']
        timestamp = event.get('timestamp', timezone.now().isoformat())
        message_id = event.get('id', None)  # 获取消息ID，如果有的话
        
        logger.info(f"广播消息: sender={sender}, message={message[:30]}...(截断)")
        
        # 发送消息到WebSocket
        response_data = {
            'message': message,
            'sender': sender,
            'timestamp': timestamp
        }
        
        # 如果有消息ID，则添加到响应中
        if message_id:
            response_data['id'] = message_id
            
        await self.send(text_data=json.dumps(response_data))
