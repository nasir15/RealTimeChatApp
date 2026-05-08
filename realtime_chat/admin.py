from django.contrib import admin

from .models import ChatGroup, Message


@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_by', 'created_at')
    search_fields = ('name', 'slug', 'description', 'created_by__username')
    filter_horizontal = ('members',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'group', 'short_content', 'timestamp')
    list_filter = ('timestamp', 'group')
    search_fields = ('content', 'sender__username', 'receiver__username', 'group__name')

    @staticmethod
    def short_content(obj):
        return obj.content[:50]
