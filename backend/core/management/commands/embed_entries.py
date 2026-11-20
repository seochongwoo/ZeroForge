from django.core.management.base import BaseCommand, CommandError

from core.embeddings import EmbeddingUnavailable
from core.retrieval import ensure_embeddings


class Command(BaseCommand):
    help = "임베딩이 없거나 지금 모델과 다른 기록을 임베딩한다 (원문은 출력하지 않는다)"

    def handle(self, *args, **options):
        try:
            count = ensure_embeddings()
        except EmbeddingUnavailable as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"임베딩한 기록: {count}개")
