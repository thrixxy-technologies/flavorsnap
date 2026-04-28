import pytest

@pytest.fixture(scope="session")
def setup_env():
    # Could load env vars or test configs
    return True