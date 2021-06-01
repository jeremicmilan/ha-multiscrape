"""Support for multiscrape binary sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.const import CONF_FORCE_UPDATE
from homeassistant.const import CONF_NAME
from homeassistant.const import CONF_RESOURCE_TEMPLATE
from homeassistant.const import CONF_VALUE_TEMPLATE
from homeassistant.exceptions import PlatformNotReady

from . import async_get_config_and_coordinator
from .const import CONF_ATTR
from .const import CONF_INDEX
from .const import CONF_SELECT
from .entity import MultiscrapeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the multiscrape binary sensor."""
    # Must update the sensor now (including fetching the rest resource) to
    # ensure it's updating its state.
    if discovery_info is not None:
        conf, coordinator, rest = await async_get_config_and_coordinator(
            hass, BINARY_SENSOR_DOMAIN, discovery_info
        )
    else:
        _LOGGER.error("Could not find sensor configuration")

    if rest.data is None:
        if rest.last_exception:
            raise PlatformNotReady from rest.last_exception
        raise PlatformNotReady

    name = conf.get(CONF_NAME)
    device_class = conf.get(CONF_DEVICE_CLASS)
    select = conf.get(CONF_SELECT)
    attribute = conf.get(CONF_ATTR)
    index = conf.get(CONF_INDEX)
    value_template = conf.get(CONF_VALUE_TEMPLATE)
    force_update = conf.get(CONF_FORCE_UPDATE)
    resource_template = conf.get(CONF_RESOURCE_TEMPLATE)

    if value_template is not None:
        value_template.hass = hass

    async_add_entities(
        [
            RestBinarySensor(
                hass,
                coordinator,
                rest,
                name,
                device_class,
                value_template,
                force_update,
                resource_template,
                select,
                attribute,
                index,
            )
        ],
    )


class RestBinarySensor(MultiscrapeEntity, BinarySensorEntity):
    """Representation of a multiscrape binary sensor."""

    def __init__(
        self,
        hass,
        coordinator,
        rest,
        name,
        device_class,
        value_template,
        force_update,
        resource_template,
        select_template,
        attribute,
        index,
    ):
        """Initialize a multiscrape binary sensor."""
        super().__init__(
            coordinator, rest, name, device_class, resource_template, force_update
        )
        self._state = False
        self._previous_data = None
        self._value_template = value_template
        self._is_on = None
        self._hass = hass
        self._select_template = select_template
        self._attribute = attribute
        self._index = index

        if self._select_template is not None:
            self._select_template.hass = self._hass
            self._select = self._select_template.async_render()
            _LOGGER.debug("Parsed select template: %s", self._select)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_on

    def _update_from_rest_data(self):
        """Update state from the scraped data."""

        if self.rest.soup is None:
            self._is_on = False

        # _LOGGER.debug("Data fetched from resource: %s", value)
        value = self._scrape(self.rest.soup, self._select, self._attribute, self._index)

        try:
            self._is_on = bool(int(value))
        except ValueError:
            self._is_on = {"true": True, "on": True, "open": True, "yes": True}.get(
                value.lower(), False
            )