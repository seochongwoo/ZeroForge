from django.contrib import admin
from django.urls import path, re_path

from core.api import api
from core.views import healthz, web_app

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("healthz", healthz),
    # 그 외 모든 경로는 앱 화면 (api/, admin/, static/은 제외)
    re_path(r"^(?!api(?:/|$)|admin(?:/|$)|static/|healthz$)(?P<path>.*)$", web_app),
]
