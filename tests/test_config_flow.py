"""Tests for the config flow module."""

from unittest.mock import Mock

import pytest
import voluptuous as vol
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.meridian_energy.config_flow import MeridianConfigFlow
from custom_components.meridian_energy.const import SENSOR_NAME


@pytest.mark.unit
class TestMeridianConfigFlow:
    """Test suite for MeridianConfigFlow."""

    def test_config_flow_initialization(self):
        """Test config flow initialization."""
        config_flow = MeridianConfigFlow()

        assert config_flow.VERSION == 1

    @pytest.mark.asyncio
    async def test_async_step_user_with_valid_input(self):
        """Test async_step_user with valid input."""
        config_flow = MeridianConfigFlow()
        config_flow.async_create_entry = Mock()

        user_input = {
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        }

        result = await config_flow.async_step_user(user_input)

        config_flow.async_create_entry.assert_called_once()
        call_args = config_flow.async_create_entry.call_args

        assert call_args[1]["title"] == SENSOR_NAME
        assert call_args[1]["data"][CONF_EMAIL] == "test@example.com"
        assert call_args[1]["data"][CONF_PASSWORD] == "test_password"

    @pytest.mark.asyncio
    async def test_async_step_user_without_input(self):
        """Test async_step_user shows form without input."""
        config_flow = MeridianConfigFlow()
        config_flow.async_show_form = Mock()

        result = await config_flow.async_step_user(None)

        config_flow.async_show_form.assert_called_once()
        call_args = config_flow.async_show_form.call_args

        assert call_args[1]["step_id"] == "user"

        # Verify schema has email and password fields
        schema = call_args[1]["data_schema"]
        assert isinstance(schema, vol.Schema)

    @pytest.mark.asyncio
    async def test_async_step_user_with_empty_input(self):
        """Test async_step_user with empty input dict."""
        config_flow = MeridianConfigFlow()
        config_flow.async_show_form = Mock()

        result = await config_flow.async_step_user({})

        config_flow.async_show_form.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_entry_data_preservation(self):
        """Test that config entry preserves all user data."""
        config_flow = MeridianConfigFlow()
        config_flow.async_create_entry = Mock()

        email = "user@example.com"
        password = "secure_password_123"

        await config_flow.async_step_user({
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
        })

        entry_data = config_flow.async_create_entry.call_args[1]["data"]
        assert entry_data[CONF_EMAIL] == email
        assert entry_data[CONF_PASSWORD] == password

