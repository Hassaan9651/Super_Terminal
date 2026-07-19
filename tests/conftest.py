import pytest


@pytest.fixture(autouse=True)
def reset_genai_client_caches():
    """Cached Gemini clients must not leak between mocked tests."""
    import utils.translator

    utils.translator._client = None
    yield
    utils.translator._client = None
