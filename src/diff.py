from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiffResult:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def upload_ids(self) -> list[str]:
        return [*self.added, *self.updated]


def classify_changes(
    local_hashes: dict[str, str],
    remote_hashes: dict[str, str],
) -> DiffResult:
    result = DiffResult()
    for article_id, content_hash in local_hashes.items():
        remote_hash = remote_hashes.get(article_id)
        if remote_hash is None:
            result.added.append(article_id)
        elif remote_hash != content_hash:
            result.updated.append(article_id)
        else:
            result.skipped.append(article_id)
    return result
