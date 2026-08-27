import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from app.storage.s3 import S3DocumentStorage


class S3DocumentStorageTests(unittest.TestCase):
    def test_saves_filing_under_logical_key(self):
        client = Mock()

        with patch(
            "app.storage.s3.boto3.client",
            return_value=client,
        ):
            storage = S3DocumentStorage(
                bucket_name="filings",
                key_prefix="raw",
            )

        key = storage.save_filing(
            ticker="aapl",
            accession_number="0000320193-26-000001",
            source_url="https://www.sec.gov/report.htm",
            content="<html></html>",
        )

        self.assertEqual(
            key,
            "raw/filings/AAPL/000032019326000001/report.htm",
        )
        client.put_object.assert_called_once_with(
            Bucket="filings",
            Key=key,
            Body=b"<html></html>",
            ContentType="text/html; charset=utf-8",
        )

    def test_exists_returns_false_for_not_found(self):
        client = Mock()
        client.head_object.side_effect = ClientError(
            error_response={
                "ResponseMetadata": {
                    "HTTPStatusCode": 404
                }
            },
            operation_name="HeadObject",
        )

        with patch(
            "app.storage.s3.boto3.client",
            return_value=client,
        ):
            storage = S3DocumentStorage(
                bucket_name="filings",
            )

        self.assertFalse(
            storage.exists("missing")
        )

    def test_read_text_decodes_s3_body(self):
        client = Mock()
        body = Mock()
        body.read.return_value = b"hello"
        client.get_object.return_value = {
            "Body": body
        }

        with patch(
            "app.storage.s3.boto3.client",
            return_value=client,
        ):
            storage = S3DocumentStorage(
                bucket_name="filings",
            )

        self.assertEqual(
            storage.read_text("key"),
            "hello",
        )


if __name__ == "__main__":
    unittest.main()
