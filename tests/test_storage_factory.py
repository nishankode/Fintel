import unittest

from app.core.settings import Settings
from app.storage.factory import build_document_storage
from app.storage.local import LocalDocumentStorage


class StorageFactoryTests(unittest.TestCase):
    def test_builds_local_storage_by_default(self):
        storage = build_document_storage(
            self._settings()
        )

        self.assertIsInstance(
            storage,
            LocalDocumentStorage,
        )

    def test_requires_bucket_for_s3_storage(self):
        settings = self._settings(
            document_storage_provider="s3",
            s3_bucket_name=None,
        )

        with self.assertRaises(ValueError):
            build_document_storage(settings)

    def _settings(
        self,
        **overrides,
    ) -> Settings:
        values = {
            "app_name": "Fintel",
            "app_version": "0.1.0",
            "environment": "development",
            "debug": False,
            "database_url": "postgresql+psycopg://user:pass@localhost/db",
            "jwt_secret_key": "secret",
            "sec_user_agent": "Fintel tests contact@example.com",
        }
        values.update(overrides)

        return Settings(**values)


if __name__ == "__main__":
    unittest.main()
