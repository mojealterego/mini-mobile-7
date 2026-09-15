from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock
from typing import Any, Mapping


class EsimArtifactConflictError(RuntimeError):
    """Raised when an eSIM artifact conflicts with existing authoritative state."""


class EsimArtifactNotFoundError(KeyError):
    """Raised when an eSIM artifact is absent from the artifact store."""


@dataclass(frozen=True, slots=True)
class StoredEsimArtifact:
    subscriber_id: str
    profile_id: str
    smdp_address: str
    activation_code_ref: str
    activation_uri_sha256: str
    status: str
    version: int


class EsimArtifactRepository(ABC):
    """Store only non-secret eSIM provisioning metadata and fingerprints."""

    @abstractmethod
    def get(self, subscriber_id: str) -> StoredEsimArtifact:
        raise NotImplementedError

    @abstractmethod
    def put(self, artifact: StoredEsimArtifact, *, expected_version: int) -> StoredEsimArtifact:
        raise NotImplementedError


class InMemoryEsimArtifactRepository(EsimArtifactRepository):
    def __init__(self) -> None:
        self._items: dict[str, StoredEsimArtifact] = {}
        self._lock = Lock()

    def get(self, subscriber_id: str) -> StoredEsimArtifact:
        with self._lock:
            try:
                return self._items[subscriber_id]
            except KeyError as exc:
                raise EsimArtifactNotFoundError(subscriber_id) from exc

    def put(self, artifact: StoredEsimArtifact, *, expected_version: int) -> StoredEsimArtifact:
        with self._lock:
            current = self._items.get(artifact.subscriber_id)
            if current is not None and current.version != expected_version:
                raise EsimArtifactConflictError(
                    f"eSIM artifact version conflict for {artifact.subscriber_id}: "
                    f"expected {expected_version}, current {current.version}"
                )
            if current is not None and _same_artifact(current, artifact):
                return current
            if current is not None:
                raise EsimArtifactConflictError(
                    f"eSIM artifact already exists with different state: {artifact.subscriber_id}"
                )
            if expected_version != 0:
                raise EsimArtifactConflictError("eSIM artifact does not exist; expected_version must be 0")
            self._items[artifact.subscriber_id] = artifact
            return artifact


class MongoEsimArtifactRepository(EsimArtifactRepository):
    """Mongo projection for eSIM metadata; raw activation codes are never persisted."""

    def __init__(self, mongodb_uri: str, *, database: str = "mini_mobile_7") -> None:
        from pymongo import MongoClient

        self._client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        self._collection = self._client[database]["esim_artifacts"]
        self._collection.create_index("subscriber_id", unique=True)

    def get(self, subscriber_id: str) -> StoredEsimArtifact:
        document = self._collection.find_one({"subscriber_id": subscriber_id})
        if document is None:
            raise EsimArtifactNotFoundError(subscriber_id)
        return _from_document(document)

    def put(self, artifact: StoredEsimArtifact, *, expected_version: int) -> StoredEsimArtifact:
        from pymongo import ReturnDocument

        replacement = _to_document(artifact)
        result = self._collection.find_one_and_update(
            {"subscriber_id": artifact.subscriber_id, "version": expected_version},
            {"$set": replacement},
            upsert=expected_version == 0,
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            current = self.get(artifact.subscriber_id)
            if _same_artifact(current, artifact):
                return current
            raise EsimArtifactConflictError(
                f"eSIM artifact version conflict for {artifact.subscriber_id}"
            )
        return _from_document(result)


def _same_artifact(left: StoredEsimArtifact, right: StoredEsimArtifact) -> bool:
    return left == right


def _to_document(artifact: StoredEsimArtifact) -> dict[str, Any]:
    return {
        "subscriber_id": artifact.subscriber_id,
        "profile_id": artifact.profile_id,
        "smdp_address": artifact.smdp_address,
        "activation_code_ref": artifact.activation_code_ref,
        "activation_uri_sha256": artifact.activation_uri_sha256,
        "status": artifact.status,
        "version": artifact.version,
    }


def _from_document(document: Mapping[str, Any]) -> StoredEsimArtifact:
    return StoredEsimArtifact(
        subscriber_id=str(document["subscriber_id"]),
        profile_id=str(document["profile_id"]),
        smdp_address=str(document["smdp_address"]),
        activation_code_ref=str(document["activation_code_ref"]),
        activation_uri_sha256=str(document["activation_uri_sha256"]),
        status=str(document["status"]),
        version=int(document["version"]),
    )
