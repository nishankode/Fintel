import unittest
from unittest.mock import Mock

from app.retrieval.semantic import SemanticRetriever


class SemanticRetrieverTests(unittest.TestCase):
    def test_rejects_blank_query(self):
        db = Mock()
        embedding_service = Mock()

        retriever = SemanticRetriever(
            db=db,
            embedding_service=embedding_service,
        )

        with self.assertRaises(ValueError):
            retriever.search("   ")

        embedding_service.embed_query.assert_not_called()
        db.execute.assert_not_called()

    def test_rejects_non_positive_top_k(self):
        db = Mock()
        embedding_service = Mock()

        retriever = SemanticRetriever(
            db=db,
            embedding_service=embedding_service,
        )

        with self.assertRaises(ValueError):
            retriever.search(
                query="revenue growth",
                top_k=0,
            )

        embedding_service.embed_query.assert_not_called()
        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
