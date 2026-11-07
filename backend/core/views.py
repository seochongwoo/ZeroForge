from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


# GET과 HEAD 모두 받는다. 웹의 NetInfo와 일부 헬스체크는 HEAD로 연결을 확인한다.
@require_safe
@never_cache
def healthz(request):
    """호스팅 헬스체크용. 인증 없이 DB 연결만 확인한다."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"ok": False}, status=503)
    return JsonResponse({"ok": True})


@require_safe
@never_cache
def web_app(request, path=""):
    """Expo 웹 빌드의 index.html. /settings 같은 화면 경로도 여기로 온다 (SPA).

    번들 파일(/_expo/static/...)은 WhiteNoise가 먼저 응답하므로 여기까지 오지 않는다.
    """
    # 없는 파일 요청에 index.html을 주면 브라우저가 JS 자리에 HTML을 받아 화면이 하얘진다
    last_segment = path.rsplit("/", 1)[-1]
    if path.startswith("_expo/") or "." in last_segment:
        raise Http404
    index = settings.WEB_BUILD_DIR / "index.html"
    if not index.is_file():
        return HttpResponse(
            "웹 빌드가 없습니다. app/에서 `npx expo export --platform web` 후 "
            "결과(dist/)를 ZF_WEB_BUILD_DIR에 두세요.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )
    return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
