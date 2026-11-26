import pytest

from backend.ai.chunking import ChunkTooLongError, chunk_document, chunk_documents
from backend.ai.config import ChunkingConfig
from backend.ai.documents import SourceDocument
from backend.ai.embeddings import HashingEmbedder
from backend.ai.tests.fixture_data import EXPERT_SENTENCES

count = HashingEmbedder().count_tokens
CONFIG = ChunkingConfig(chunk_size=400, chunk_overlap=120, max_tokens=256)


def _doc(text, doc_type="explanation", doc_id="explanation:38:expert"):
    return SourceDocument(doc_id=doc_id, doc_type=doc_type, title="Photoelectric Effect - Expert explanation",
                          text=text, metadata={"laureate_ids": [249], "level": "Expert"})


def _body(chunk):
    return chunk.text.split(":\n", 1)[1]


def test_short_record_stays_intact():
    doc = _doc("Albert Einstein (Nobel laureate, person).", doc_type="laureate_record", doc_id="laureate:nobel-26")
    chunks = chunk_document(doc, count, CONFIG)
    assert len(chunks) == 1
    assert chunks[0].text == doc.text
    assert chunks[0].chunk_id == "laureate:nobel-26#c0"


def test_long_text_is_split_within_size_and_token_limits():
    chunks = chunk_document(_doc(" ".join(EXPERT_SENTENCES)), count, CONFIG)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(_body(chunk)) <= CONFIG.chunk_size
        assert chunk.token_count <= CONFIG.max_tokens
        assert chunk.text.startswith("Photoelectric Effect - Expert explanation:\n")


def test_chunks_respect_sentence_boundaries_and_cover_all_text():
    chunks = chunk_document(_doc(" ".join(EXPERT_SENTENCES)), count, CONFIG)
    joined = " ".join(_body(c) for c in chunks)
    for sentence in EXPERT_SENTENCES:
        assert sentence in joined
    for chunk in chunks:
        assert _body(chunk)[0].isupper()  # starts at a sentence boundary
        assert _body(chunk).endswith(".")


def test_consecutive_chunks_overlap():
    chunks = chunk_document(_doc(" ".join(EXPERT_SENTENCES)), count, CONFIG)
    for previous, current in zip(chunks, chunks[1:]):
        first_sentence = _body(current).split(". ")[0]
        assert first_sentence in _body(previous)


def test_word_level_overlap_when_sentences_exceed_overlap_budget():
    long_sentence = "word " * 60
    text = ". ".join(long_sentence.strip() + f" end{i}" for i in range(4)) + "."
    config = ChunkingConfig(chunk_size=400, chunk_overlap=60, max_tokens=256)
    chunks = chunk_document(_doc(text), count, config)
    assert len(chunks) > 1
    for previous, current in zip(chunks, chunks[1:]):
        assert _body(current).split(" ")[0] in _body(previous).split(" ")


def test_chunking_is_deterministic():
    doc = _doc(" ".join(EXPERT_SENTENCES))
    first = chunk_document(doc, count, CONFIG)
    second = chunk_document(doc, count, CONFIG)
    assert [(c.chunk_id, c.text, c.metadata["content_hash"]) for c in first] == \
           [(c.chunk_id, c.text, c.metadata["content_hash"]) for c in second]


def test_metadata_and_parent_ids_are_preserved():
    chunks = chunk_document(_doc(" ".join(EXPERT_SENTENCES)), count, CONFIG)
    for index, chunk in enumerate(chunks):
        assert chunk.parent_doc_id == "explanation:38:expert"
        assert chunk.chunk_id == f"explanation:38:expert#c{index}"
        assert chunk.metadata["parent_doc_id"] == "explanation:38:expert"
        assert chunk.metadata["laureate_ids"] == [249]
        assert chunk.metadata["level"] == "Expert"
        assert chunk.metadata["chunk_index"] == index
        assert chunk.metadata["chunk_count"] == len(chunks)
        assert chunk.metadata["token_count"] == chunk.token_count


def test_token_dense_text_shrinks_chunks_instead_of_truncating():
    # A counter that charges 1 token per character forces the budget down.
    dense = lambda text: len(text)  # noqa: E731
    config = ChunkingConfig(chunk_size=900, chunk_overlap=100, max_tokens=256)
    chunks = chunk_document(_doc(" ".join(EXPERT_SENTENCES)), dense, config)
    assert all(dense(c.text) <= 256 for c in chunks)
    assert " ".join(_body(c) for c in chunks).count("Millikan") >= 1


def test_continuation_header_tokens_are_counted_while_packing():
    # Regression: the "(continued)" header of non-explanation chunks must be
    # included in the token budget, otherwise packing accepts chunks that the
    # final guard then rejects.
    doc = SourceDocument(
        doc_id="contribution:609", doc_type="contribution",
        title="Nucleoside Base Modifications and mRNA Vaccines " * 2,
        text=" ".join(EXPERT_SENTENCES), metadata={"laureate_ids": [1]},
    )
    half = lambda value: len(value) // 2  # noqa: E731
    chunks = chunk_document(doc, half, ChunkingConfig(chunk_size=900, chunk_overlap=100, max_tokens=256))
    assert len(chunks) > 1
    assert chunks[1].text.startswith(doc.title + " (continued):\n")
    assert all(half(c.text) <= 256 for c in chunks)


def test_impossible_token_limit_raises_instead_of_silent_truncation():
    impossible = lambda text: 10_000  # noqa: E731
    with pytest.raises(ChunkTooLongError):
        chunk_document(_doc(" ".join(EXPERT_SENTENCES)), impossible, CONFIG)


def test_short_text_over_token_limit_is_split_not_kept():
    # 600 chars is under chunk_size (900) but 300 "tokens" exceeds the limit.
    text = " ".join(f"Sentence number {i} has some filler words in it to pad it out." for i in range(10))[:600]
    doc = _doc(text, doc_type="laureate_record", doc_id="laureate:nobel-1")
    counter = lambda value: len(value) // 2  # noqa: E731
    assert counter(text) > 256
    chunks = chunk_document(doc, counter, ChunkingConfig(chunk_size=900, chunk_overlap=0, max_tokens=256))
    assert len(chunks) > 1
    assert all(counter(c.text) <= 256 for c in chunks)


def test_empty_document_produces_no_chunks():
    assert chunk_document(_doc("   "), count, CONFIG) == []


@pytest.mark.parametrize("kwargs", [
    {"chunk_size": 0}, {"chunk_size": 100, "chunk_overlap": 100}, {"chunk_overlap": -1}, {"max_tokens": 4},
])
def test_invalid_chunking_config_rejected(kwargs):
    with pytest.raises(ValueError):
        ChunkingConfig(**{"chunk_size": 900, "chunk_overlap": 150, "max_tokens": 256, **kwargs})


def test_real_fixture_documents_chunk_cleanly(documents):
    chunks = chunk_documents(documents, count, ChunkingConfig())
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert {c.parent_doc_id for c in chunks} == {d.doc_id for d in documents}
