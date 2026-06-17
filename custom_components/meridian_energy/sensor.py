"""Meridian Energy sensors."""

from datetime import datetime, timedelta

import csv
from io import StringIO
from pytz import timezone
import logging
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.components.sensor import SensorEntity

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
    StatisticMeanType,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
)

from .api import MeridianEnergyApi

from .const import DOMAIN, SENSOR_NAME

NAME = DOMAIN
ISSUEURL = "https://github.com/andrewdallow/ha-meridian-energy/issues"

STARTUP = f"""
-------------------------------------------------------------------
{NAME}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUEURL}
-------------------------------------------------------------------
"""

_LOGGER = logging.getLogger(__name__)

# YAML platform configuration is deprecated for this integration; config_flow is used instead.

SCAN_INTERVAL = timedelta(hours=3)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Asynchronously set up the entry."""
    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)

    api = MeridianEnergyApi(email, password)

    _LOGGER.debug("Setting up sensor(s)...")

    sensors = [MeridianEnergyUsageSensor(SENSOR_NAME, api)]
    async_add_entities(sensors, True)


class MeridianEnergyUsageSensor(SensorEntity):
    """Define Meridian Energy Usage sensor."""

    def __init__(self, name, api):
        """Initialise Meridian Energy Usage sensor."""
        self._name = name
        self._icon = "mdi:meter-electric"
        self._state = 0
        self._unique_id = DOMAIN
        self._state_attributes = {}
        self._api = api

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._state_attributes

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    async def async_update(self) -> None:
        """Asynchronously update the sensor data."""
        _LOGGER.debug("Beginning usage update")

        day_statistics = []
        day_running_sum = 0

        night_statistics = []
        night_running_sum = 0

        # Login to the website (blocking IO) — run in executor
        await self.hass.async_add_executor_job(self._api.token)

        # Get the latest usage data (blocking IO) — run in executor
        response = await self.hass.async_add_executor_job(self._api.get_data)

        # Process the CSV consumption file
        csv_file = csv.reader(StringIO(response))

        for row in csv_file:
            # Accessing columns by index in each row
            if len(row) < 13:  # Checking if there are at least 13 columns (indices 0-12)
                _LOGGER.warning("Not enough columns in this row, expected at least 13")
                continue

            if row[0] == "HDR":
                _LOGGER.debug("HDR line arrived")
                continue
            elif row[0] == "DET":
                _LOGGER.debug("DET line arrived")

            # Skip any estimated reads
            read_status = row[11].strip()
            if read_status != "RD":
                _LOGGER.debug("HDR line skipped as its estimated")
                continue

            # Assuming row[9] contains the date in the format 'dd/mm/YYYY HH:MM:SS'
            read_period_start_date_time = row[9].strip()

            # Assuming tz is your timezone (e.g., pytz.timezone('Your/Timezone'))
            tz = timezone("Pacific/Auckland")

            # Parse the date string into a datetime object
            start_date = datetime.strptime(
                read_period_start_date_time, "%d/%m/%Y %H:%M:%S"
            )

            # Exclude any readings that are at the 59th minute (summarised daily totals)
            if start_date.minute == 59:
                continue

            # Localize the datetime object
            start_date = tz.localize(start_date)

            # Round down to the nearest hour as HA can only handle hourly
            rounded_date = start_date.replace(minute=0, second=0, microsecond=0)

            # Only calculate the energy after all checks are complete
            unit_quantity_active_energy_volume = row[12].strip()

            # Night rate channel
            if (
                start_date.hour >= 21 or
                start_date.hour <= 6
            ):
                night_running_sum = night_running_sum + float(
                    unit_quantity_active_energy_volume
                )
                night_statistics.append(
                    StatisticData(start=rounded_date, sum=night_running_sum)
                )

            # Day rate channel
            else:
                day_running_sum = day_running_sum + float(
                    unit_quantity_active_energy_volume
                )
                day_statistics.append(
                    StatisticData(start=rounded_date, sum=day_running_sum)
                )

        day_metadata = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"{SENSOR_NAME} (Day)",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:consumption_day",
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            unit_class="energy"
        )
        async_add_external_statistics(self.hass, day_metadata, day_statistics)

        night_metadata = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"{SENSOR_NAME} (Night)",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:consumption_night",
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            unit_class="energy"
        )
        async_add_external_statistics(self.hass, night_metadata, night_statistics)
