from django.urls import path, include
from .views import ProfileViewSet, ChatViewSet, MessageViewSet
from rest_framework_nested import routers
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="VinduChat API",
      default_version='v1',
      description="Description of app",
      license=openapi.License(
         name="MIT License",
         url="https://github.com/Ubaidullah-M/VinduChatApp/blob/main/LICENSE",
      ),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register('profiles', ProfileViewSet)
router.register('chats', ChatViewSet, basename="chats")

chat_router = routers.NestedDefaultRouter(router, "chats", lookup="chat")
chat_router.register("messages", MessageViewSet, basename="chat-messages")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(chat_router.urls)),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]