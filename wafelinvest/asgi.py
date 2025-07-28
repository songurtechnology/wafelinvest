import os
import django

# Django ortamı başlatılmadan hiçbir şey import etme
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wafelinvest.settings')
django.setup()

# Bundan sonra importlar güvenli
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from core.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
