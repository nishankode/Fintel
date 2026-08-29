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

    def test_filters_filings_by_selected_years(self):
        client = StubSECClient(
            submissions={
                "filings": {
                    "recent": {
                        "accessionNumber": [
                            "0000000000-26-000001",
                            "0000000000-25-000001",
                        ],
                        "form": ["10-K", "10-K"],
                        "filingDate": ["2026-01-31", "2025-01-31"],
                        "reportDate": ["2025-12-31", "2024-12-31"],
                        "primaryDocument": ["report-2026.htm", "report-2025.htm"],
                    }
                }
            }
        )
        service = SECDiscoveryService(client)

        filings = service.get_recent_filings(
            cik="1",
            filing_types={"10-K"},
            filing_years={2025},
        )

        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0].accession_number, "0000000000-25-000001")


class StubSECClient:
    def __init__(self, submissions):
        self.submissions = submissions

    def get_company_submissions(self, cik):
        return self.submissions


if __name__ == "__main__":
    unittest.main()
