"""기록을 의미 벡터로 바꾼다 (Step 8, ADR 0004).

공급사는 이 파일 안에만 있다. 다른 곳은 embed_texts()만 부른다.
기록 원문이 공급사로 전송되므로, 원문을 로그에 남기지 않는다.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings

from .models import EMBEDDING_DIMENSIONS

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
BATCH_SIZE = 128
TIMEOUT_SECONDS = 30


class EmbeddingUnavailable(Exception):
    """키가 없거나 공급사에 닿지 않을 때. 쓰기·읽기는 이것과 무관하게 계속된다."""


def current_model() -> str:
    return settings.EMBEDDING_MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """텍스트 여러 개를 같은 순서의 벡터로. 기록끼리 비교하므로 모두 document로 임베딩한다."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_voyage(texts[start : start + BATCH_SIZE]))
    return vectors


def _voyage(texts: list[str]) -> list[list[float]]:
    key = settings.VOYAGE_API_KEY
    if not key:
        raise EmbeddingUnavailable("VOYAGE_API_KEY가 설정되지 않았습니다")
    body = json.dumps(
        {
            "input": texts,
            "model": current_model(),
            "input_type": "document",
            "output_dimension": EMBEDDING_DIMENSIONS,
        }
    ).encode()
    request = urllib.request.Request(
        VOYAGE_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        # 응답 본문에 입력이 되비칠 수 있어 상태 코드만 남긴다
        raise EmbeddingUnavailable(f"임베딩 공급사 오류 (HTTP {exc.code})") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise EmbeddingUnavailable("임베딩 공급사에 연결하지 못했습니다") from exc

    items = sorted(data.get("data", []), key=lambda d: d["index"])
    vectors = [item["embedding"] for item in items]
    if len(vectors) != len(texts) or any(len(v) != EMBEDDING_DIMENSIONS for v in vectors):
        raise EmbeddingUnavailable("임베딩 응답의 개수나 차원이 맞지 않습니다")
    return vectors
