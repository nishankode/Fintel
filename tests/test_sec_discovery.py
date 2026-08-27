import unittest

from app.ingestion.discovery import SECDiscoveryService


class SECDiscoveryServiceTests(unittest.TestCase):
    def test_allows_blank_report_date(self):
        client = StubSECClient(
            submissions={
                "filings": {
                    "recent": {
                        "accessionNumber": [
                            "0000000000-26-000001"
                        ],
                        "form": ["10-K"],
                        "filingDate": ["2026-01-31"],
                        "reportDate": [""],
                        "primaryDocument": ["report.htm"],
                    }
                }
            }
        )
        service = SECDiscoveryService(client)

        filings = service.get_recent_filings(
            cik="1",
            filing_types={"10-K"},
        )

        self.assertEqual(len(filings), 1)
        self.assertIsNone(filings[0].reporting_period)


class StubSECClient:
    def __init__(self, submissions):
        self.submissions = submissions

    def get_company_submissions(self, cik):
        return self.submissions


if __name__ == "__main__":
    unittest.main()
