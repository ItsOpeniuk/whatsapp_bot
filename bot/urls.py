from django.urls import path
from bot.views import WhatsAppBotView

urlpatterns = [
    path('incoming/', WhatsAppBotView.as_view(), name='incoming_message'),
]
