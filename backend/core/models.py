from django.db import models


class Entry(models.Model):
    """원문. 불변이다. 수정은 새 Entry로 한다.

    점수·상태 필드는 두지 않는다 (P1, P4).
    """

    class Source(models.TextChoices):
        WEB = "web"
        IOS = "ios"
        ANDROID = "android"

    # 클라이언트가 생성한다. 오프라인에서 쓴 기록을 다시 보내도 중복 저장되지 않게 하기 위해서다.
    id = models.UUIDField(primary_key=True)
    content = models.TextField()
    source = models.CharField(max_length=16, choices=Source.choices)
    # 기기에서 실제로 쓴 시각. 늦게 동기화돼도 기록의 시간은 쓴 순간이다.
    written_at = models.DateTimeField()
    # 서버에 도착한 시각
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-written_at", "-id"]
        indexes = [models.Index(fields=["-written_at", "-id"], name="entry_written_desc")]

    def __str__(self) -> str:
        return f"{self.written_at:%Y-%m-%d %H:%M} ({self.source})"
