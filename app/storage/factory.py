from app.core.settings import Settings
from app.storage.base import DocumentStorage
from app.storage.local import LocalDocumentStorage
from app.storage.s3 import S3DocumentStorage


def build_document_storage(
    settings: Settings,
) -> DocumentStorage:
    if settings.document_storage_provider == "local":
        return LocalDocumentStorage(
            base_path=settings.document_storage_path,
        )

    if settings.s3_bucket_name is None:
        raise ValueError(
            "S3_BUCKET_NAME is required when "
            "DOCUMENT_STORAGE_PROVIDER=s3"
        )

    return S3DocumentStorage(
        bucket_name=settings.s3_bucket_name,
        key_prefix=settings.s3_key_prefix,
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region_name,
    )
