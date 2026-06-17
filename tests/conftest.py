"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
import requests


@pytest.fixture
def hass():
    """Return a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def config_entry():
    """Return a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "email": "test@example.com",
        "password": "test_password",
    }
    return entry


@pytest.fixture
def mock_session():
    """Return a mock requests.Session."""
    session = Mock(spec=requests.Session)
    session.get = Mock()
    session.post = Mock()
    return session


@pytest.fixture
def sample_csv_data():
    """Return sample CSV consumption data."""
    return """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 00:00:00,RD,RD,0.5,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 01:00:00,RD,RD,0.6,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 07:00:00,RD,RD,0.7,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 08:00:00,RD,RD,0.8,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 21:00:00,RD,RD,0.9,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 22:00:00,RD,RD,1.0,,"""


@pytest.fixture
def sample_csv_data_with_edge_cases():
    """Return CSV data with edge cases."""
    return """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 06:00:00,RD,RD,0.5,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 06:30:00,ES,ES,0.6,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 07:59:00,RD,RD,0.7,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,0.8,,"""


@pytest.fixture
def mock_auth_token_html():
    """Return HTML with authenticity token."""
    return """
    <html>
        <form>
            <input name="authenticity_token" value="test_token_12345"/>
        </form>
    </html>
    """

