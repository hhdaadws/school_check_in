from django.db import models
from accounts.models import User
# Create your models here.
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    room_name = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        verbose_name = '聊天消息'
        verbose_name_plural = '聊天消息'

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"

