import uuid

from django.db import models
from django.db.models.functions import Lower
from pgvector.django import VectorField


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


class Naming(models.Model):
    """내가 붙인 이름 (P2). 이름이 바뀌어 온 과정은 NamingVersion에 쌓인다.

    label은 가장 최근 NamingVersion의 값을 그대로 담아 둔 것이다 (목록·검색용).
    이름을 바꿀 때는 덮어쓰지 않고 NamingVersion을 추가한 뒤 label을 맞춘다.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    label = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label"]
        # 같은 이름이 두 개 생기면 "어느 쪽에 붙일까"가 애매해진다. 대소문자는 구분하지 않는다.
        constraints = [models.UniqueConstraint(Lower("label"), name="naming_label_unique_ci")]

    def __str__(self) -> str:
        return self.label


class NamingVersion(models.Model):
    """이름의 변천. 추가만 하고 고치거나 지우지 않는다."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    naming = models.ForeignKey(Naming, on_delete=models.CASCADE, related_name="versions")
    label = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.label} ({self.created_at:%Y-%m-%d})"


class NamingLink(models.Model):
    """기록과 이름의 연결 (PLAN.md §5의 Link 중 Entry–Naming).

    지금은 내가 직접 붙인 것만 있다 (author=user, status=accepted).
    Step 8에서 AI 제안은 author=ai, status=proposed로 들어오고, 거절도 지우지 않고 남긴다.
    """

    class Author(models.TextChoices):
        USER = "user"
        AI = "ai"

    class Status(models.TextChoices):
        PROPOSED = "proposed"
        ACCEPTED = "accepted"
        REJECTED = "rejected"

    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="naming_links")
    naming = models.ForeignKey(Naming, on_delete=models.CASCADE, related_name="links")
    author = models.CharField(max_length=8, choices=Author.choices, default=Author.USER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACCEPTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["entry", "naming"], name="naminglink_entry_naming")]


# 임베딩 차원. 모델을 바꿔도 이 값이 같으면 마이그레이션 없이 다시 임베딩만 하면 된다 (ADR 0004)
EMBEDDING_DIMENSIONS = 1024


class EntryEmbedding(models.Model):
    """기록 하나의 의미 벡터 (Step 8, 검색 계층용).

    Entry와 따로 둔다. Entry는 불변이지만 임베딩은 모델을 바꾸면 다시 만들어야 하기 때문이다.
    어떤 모델로 만든 벡터인지 함께 저장하고, 지금 모델과 다르면 다시 만든다.
    """

    entry = models.OneToOneField(Entry, on_delete=models.CASCADE, primary_key=True, related_name="embedding")
    model = models.CharField(max_length=64)
    vector = VectorField(dimensions=EMBEDDING_DIMENSIONS)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.entry_id} ({self.model})"
