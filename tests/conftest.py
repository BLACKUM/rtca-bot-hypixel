import pytest
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture
def mock_aiofiles(mocker):
    mock_open = mocker.patch("aiofiles.open")
    mock_file = mocker.AsyncMock()
    mock_open.return_value.__aenter__.return_value = mock_file
    return mock_file

@pytest.fixture
def mock_session(mocker):
    mock = mocker.patch("aiohttp.ClientSession")
    session = mocker.AsyncMock()
    mock.return_value = session
    return session
