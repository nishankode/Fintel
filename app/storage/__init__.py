from app.storage.base import DocumentStorage
from app.storage.factory import build_document_storage
from app.storage.local import LocalDocumentStorage
from app.storage.s3 import S3DocumentStorage

__all__ = [
    "DocumentStorage",
    "LocalDocumentStorage",
    "S3DocumentStorage",
    "build_document_storage",
]
