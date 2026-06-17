"""Tests for the integration initialization module."""

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.meridian_energy import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.meridian_energy.const import DOMAIN, PLATFORMS


@pytest.mark.unit
class TestIntegrationSetup:
    """Test suite for integration setup/unload."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, hass, config_entry):
        """Test successful setup entry."""
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        result = await async_setup_entry(hass, config_entry)

        assert result is True
        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            config_entry, PLATFORMS
        )

    @pytest.mark.asyncio
    async def test_async_setup_entry_stores_data(self, hass, config_entry):
        """Test that setup entry stores config data in hass.data."""
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        await async_setup_entry(hass, config_entry)

        # Verify data is stored
        assert DOMAIN in hass.data
        assert config_entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][config_entry.entry_id] == config_entry.data

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(self, hass, config_entry):
        """Test successful unload entry."""
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        result = await async_unload_entry(hass, config_entry)

        assert result is True
        hass.config_entries.async_unload_platforms.assert_called_once_with(
            config_entry, PLATFORMS
        )

    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(self, hass, config_entry):
        """Test unload entry failure."""
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        result = await async_unload_entry(hass, config_entry)

        assert result is False

    @pytest.mark.asyncio
    async def test_async_reload_entry(self, hass, config_entry):
        """Test reload entry calls unloading and setup."""
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        await async_reload_entry(hass, config_entry)

        hass.config_entries.async_unload_platforms.assert_called_once()
        hass.config_entries.async_forward_entry_setups.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_entry_with_multiple_entries(self, hass, config_entry):
        """Test setup entry with multiple configuration entries."""
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        # Create multiple entries
        entry1 = config_entry
        entry2 = Mock()
        entry2.entry_id = "test_entry_id_2"
        entry2.data = {"email": "test2@example.com", "password": "password2"}

        await async_setup_entry(hass, entry1)
        await async_setup_entry(hass, entry2)

        # Both should be stored
        assert entry1.entry_id in hass.data[DOMAIN]
        assert entry2.entry_id in hass.data[DOMAIN]
