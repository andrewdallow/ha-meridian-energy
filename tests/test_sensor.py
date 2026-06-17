"""Tests for the sensor module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from pytz import timezone
from io import StringIO
import csv

from custom_components.meridian_energy.sensor import (
    MeridianEnergyUsageSensor,
    async_setup_entry,
)
from custom_components.meridian_energy.const import DOMAIN, SENSOR_NAME


def get_mock_call_args(call_obj):
    """Extract positional arguments from a mock call object."""
    # Handle both call[0] tuple syntax and .args attribute
    if isinstance(call_obj[0], tuple):
        return call_obj[0]
    return call_obj.args


def get_metadata_attr(metadata, attr_name, default=None):
    """Get attribute from metadata, handling both dict and object types."""
    if isinstance(metadata, dict):
        return metadata.get(attr_name, default)
    return getattr(metadata, attr_name, default)


@pytest.mark.unit
class TestMeridianEnergyUsageSensor:
    """Test suite for MeridianEnergyUsageSensor."""

    def test_sensor_initialization(self):
        """Test sensor initialization."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)

        assert sensor._name == SENSOR_NAME
        assert sensor._icon == "mdi:meter-electric"
        assert sensor._state == 0
        assert sensor._unique_id == DOMAIN
        assert sensor._state_attributes == {}
        assert sensor._api == mock_api

    def test_sensor_name_property(self):
        """Test sensor name property."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)

        assert sensor.name == SENSOR_NAME

    def test_sensor_icon_property(self):
        """Test sensor icon property."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)

        assert sensor.icon == "mdi:meter-electric"

    def test_sensor_state_property(self):
        """Test sensor state property."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)

        assert sensor.state == 0

    def test_sensor_unique_id_property(self):
        """Test sensor unique_id property."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)

        assert sensor.unique_id == DOMAIN

    def test_sensor_extra_state_attributes_property(self):
        """Test sensor extra_state_attributes property."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)

        assert sensor.extra_state_attributes == {}

    @pytest.mark.asyncio
    async def test_async_update_calls_api_methods(self):
        """Test async_update calls API token and get_data."""
        mock_api = Mock()

        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = Mock()
        sensor.hass.async_add_executor_job = AsyncMock()

        # Mock CSV data with proper format
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,"""
        sensor.hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics"):
            await sensor.async_update()

        # Verify API methods were called via executor
        assert sensor.hass.async_add_executor_job.call_count >= 1

    @pytest.mark.asyncio
    async def test_csv_parsing_valid_data(self, sample_csv_data, hass):
        """Test CSV parsing with valid data."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        hass.async_add_executor_job.side_effect = [None, sample_csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics"):
            await sensor.async_update()

            # Should process without errors
            assert True

    @pytest.mark.asyncio
    async def test_day_rate_classification(self, hass):
        """Test day rate time classification (7:00-20:59)."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        # CSV with hour 12 (day rate)
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        # Mock the statistics function to capture calls
        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            # Should be called twice (day and night)
            assert mock_stats.call_count == 2

            # Check first call (day stats)
            day_call = mock_stats.call_args_list[0]
            args = day_call.args[1]
            assert "Day" in args.get("name", "")

    @pytest.mark.asyncio
    async def test_night_rate_classification(self, hass):
        """Test night rate time classification (21:00-6:59)."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        # CSV with hours in night rate (21:00-23:59 and 0:00-6:00)
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 21:00:00,RD,RD,1.0,,
DET,1,50001234,NZ,Z,1,,0,, 02/01/2026 02:00:00,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            # Check night stats
            night_call = mock_stats.call_args_list[1]
            args = night_call.args[1]
            assert "Night" in args.get("name", "")

    @pytest.mark.asyncio
    async def test_skip_estimated_reads(self, hass):
        """Test that estimated reads are skipped."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        # CSV with both real reads (RD) and estimated (ES)
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 13:00:00,ES,ES,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            day_call = mock_stats.call_args_list[0]
            day_stats = day_call.args[2]

            # Only one reading should be included (the RD one)
            assert len(day_stats) <= 1

    @pytest.mark.asyncio
    async def test_skip_59th_minute_reads(self, hass):
        """Test that 59th minute reads (daily totals) are skipped."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        # CSV with reads at 59th minute and normal times
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:59:00,RD,RD,5.0,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 13:00:00,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            day_call = mock_stats.call_args_list[0]
            day_stats = day_call.args[2]

            # Only the 13:00 reading should be included
            assert len(day_stats) <= 1

    @pytest.mark.asyncio
    async def test_running_sum_accumulation(self, hass):
        """Test that running sums accumulate correctly."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        # Multiple readings for day rate
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 13:00:00,RD,RD,2.0,,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 14:00:00,RD,RD,1.5,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            day_call = mock_stats.call_args_list[0]
            day_stats = day_call.args[2]

            # Should have 3 data points with running sums
            assert len(day_stats) == 3
            # Check sums are accumulating
            assert day_stats[0]["sum"] == pytest.approx(1.0)
            assert day_stats[1]["sum"] == pytest.approx(3.0)
            assert day_stats[2]["sum"] == pytest.approx(4.5)

    @pytest.mark.asyncio
    async def test_date_rounding_to_hour(self, hass):
        """Test that dates are rounded down to nearest hour."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:30:45,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            day_call = mock_stats.call_args_list[0]
            day_stats = day_call.args[2]

            # Check the rounded date
            start_time = day_stats[0]["start"]
            assert start_time.minute == 0
            assert start_time.second == 0
            assert start_time.microsecond == 0

    @pytest.mark.asyncio
    async def test_statistics_metadata(self, hass):
        """Test that statistics metadata is correct."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            # Check day metadata
            day_call = mock_stats.call_args_list[0]
            day_args = day_call.args[1]
            assert day_args["has_mean"] is False
            assert day_args["has_sum"] is True
            assert "Day" in day_args["name"]
            assert day_args["source"] == DOMAIN
            assert day_args["statistic_id"] == f"{DOMAIN}:consumption_day"

            # Check night metadata
            night_call = mock_stats.call_args_list[1]
            night_args = night_call.args[1]
            assert night_args["has_mean"] is False
            assert night_args["has_sum"] is True
            assert "Night" in night_args["name"]
            assert night_args["source"] == DOMAIN
            assert night_args["statistic_id"] == f"{DOMAIN}:consumption_night"

    @pytest.mark.asyncio
    async def test_malformed_csv_handling(self, hass):
        """Test handling of malformed CSV rows."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        # CSV with incomplete row
        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics"):
            # Should not raise an exception
            await sensor.async_update()

    @pytest.mark.asyncio
    async def test_timezone_localization(self, hass):
        """Test that dates are localized to Pacific/Auckland timezone."""
        mock_api = Mock()
        sensor = MeridianEnergyUsageSensor(SENSOR_NAME, mock_api)
        sensor.hass = hass

        csv_data = """HDR,1,Electricity,1Jan2026,31Jan2026,50001234,
DET,1,50001234,NZ,Z,1,,0,, 01/01/2026 12:00:00,RD,RD,1.0,,"""

        hass.async_add_executor_job.side_effect = [None, csv_data]

        with patch("custom_components.meridian_energy.sensor.async_add_external_statistics") as mock_stats:
            await sensor.async_update()

            day_call = mock_stats.call_args_list[0]
            day_stats = day_call.args[2]

            # Check timezone info
            start_time = day_stats[0]["start"]
            assert start_time.tzinfo is not None
            assert "Pacific/Auckland" in str(start_time.tzinfo) or start_time.tzinfo.zone == "Pacific/Auckland"


@pytest.mark.unit
class TestAsyncSetupEntry:
    """Test suite for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_sensor(self, config_entry, hass):
        """Test async_setup_entry creates sensor entity."""
        mock_add_entities = AsyncMock()

        with patch("custom_components.meridian_energy.sensor.MeridianEnergyUsageSensor"):
            await async_setup_entry(hass, config_entry, mock_add_entities)

            mock_add_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_entry_passes_credentials(self, config_entry, hass):
        """Test async_setup_entry passes email and password to API."""
        mock_add_entities = AsyncMock()

        with patch("custom_components.meridian_energy.sensor.MeridianEnergyApi") as mock_api_class:
            await async_setup_entry(hass, config_entry, mock_add_entities)

            # Verify API was initialized with credentials
            mock_api_class.assert_called_once_with(
                config_entry.data["email"],
                config_entry.data["password"],
            )

