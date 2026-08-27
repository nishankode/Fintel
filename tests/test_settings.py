import unittest

from app.core.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_accepts_release_as_false_debug_value(self):
        settings = Settings(
            app_name="Fintel",
            app_version="0.1.0",
            environment="development",
            debug="release",
            database_url="postgresql+psycopg://user:pass@localhost/db",
            jwt_secret_key="secret",
            sec_user_agent="Fintel tests contact@example.com",
        )

        self.assertFalse(settings.debug)


if __name__ == "__main__":
    unittest.main()
