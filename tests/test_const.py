"""Tests for the constants module."""

import pytest
from homeassistant.const import Platform

from custom_components.meridian_energy.const import DOMAIN, SENSOR_NAME, PLATFORMS


@pytest.mark.unit
class TestConstants:
    """Test suite for constants."""

    def test_domain_constant(self):
        """Test domain constant."""
        assert DOMAIN == "meridian_energy"

    def test_sensor_name_constant(self):
        """Test sensor name constant."""
        assert SENSOR_NAME == "Meridian Energy"

    def test_platforms_constant(self):
        """Test platforms constant."""
        assert isinstance(PLATFORMS, list)
        assert len(PLATFORMS) > 0
        assert Platform.SENSOR in PLATFORMS

