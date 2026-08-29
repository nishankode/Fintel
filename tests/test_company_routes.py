import unittest
from unittest.mock import Mock

from fastapi import HTTPException

from app.api.routes.companies import delete_company
from app.models import Company


class CompanyRouteTests(unittest.TestCase):
    def test_delete_company_removes_existing_company(self):
        company = Company(
            id=1,
            cik="0000320193",
            ticker="AAPL",
            name="Apple Inc.",
        )
        db = Mock()
        db.scalar.return_value = company
        current_user = Mock(id=7)

        result = delete_company(
            ticker="aapl",
            db=db,
            current_user=current_user,
        )

        db.delete.assert_called_once_with(company)
        db.commit.assert_called_once()
        self.assertIsNone(result)

    def test_delete_company_returns_not_found_for_missing_company(self):
        db = Mock()
        db.scalar.return_value = None
        current_user = Mock(id=7)

        with self.assertRaises(HTTPException) as context:
            delete_company(
                ticker="missing",
                db=db,
                current_user=current_user,
            )

        self.assertEqual(context.exception.status_code, 404)
        db.delete.assert_not_called()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
