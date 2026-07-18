import pytest


@pytest.fixture(autouse=True)
def reset_genai_client_caches():
    """The cached Gemini clients must not leak between mocked tests."""
    import utils.transcriber
    import utils.translator

    utils.translator._client = None
    utils.transcriber._client = None
    yield
    utils.translator._client = None
    utils.transcriber._client = None
