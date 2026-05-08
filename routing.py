from django.urls import path

from . import consumers


websocket_urlpatterns = [
    path('ws/chat/private/<str:username>/', consumers.PrivateChatConsumer.as_asgi(), name='ws-private-chat'),
    path('ws/chat/group/<slug:slug>/', consumers.GroupChatConsumer.as_asgi(), name='ws-group-chat'),
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi(), name='ws-notifications'),
]
