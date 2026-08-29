from langchain_huggingface import HuggingFaceEmbeddings
import torch


BGE_QUERY_INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)


class EmbeddingService:
    def __init__(
        self,
        model_name: str,
        expected_dimension: int,
        device: str = "cpu",
        document_batch_size: int = 128,
        cpu_threads: int | None = None,
    ) -> None:
        self.expected_dimension = expected_dimension
        self.document_batch_size = document_batch_size

        if cpu_threads is not None and cpu_threads > 0:
            torch.set_num_threads(cpu_threads)

        self.model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={
                "device": device,
            },
            encode_kwargs={
                "batch_size": document_batch_size,
                "normalize_embeddings": True,
            },
            query_encode_kwargs={
                "normalize_embeddings": True,
                "prompt": BGE_QUERY_INSTRUCTION,
            },
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        embeddings = self.model.embed_documents(texts)

        for embedding in embeddings:
            self._validate_dimension(embedding)

        return embeddings

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        embedding = self.model.embed_query(query)

        self._validate_dimension(embedding)

        return embedding

    def _validate_dimension(
        self,
        embedding: list[float],
    ) -> None:
        if len(embedding) != self.expected_dimension:
            raise ValueError(
                "Unexpected embedding dimension: "
                f"expected={self.expected_dimension}, "
                f"actual={len(embedding)}"
            )
