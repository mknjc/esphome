import esphome.codegen as cg
from esphome.components import select
import esphome.config_validation as cv
from esphome.const import (
    ENTITY_CATEGORY_CONFIG
)

from . import therm_ns, CONF_THERM_ID, ThermComponent

CONF_VALVE_FORCE = "valve_force"

ValveForceSelect = therm_ns.class_("ValveForceSelect", select.Select)


CONFIG_SCHEMA = {
    cv.GenerateID(CONF_THERM_ID): cv.use_id(ThermComponent),
    cv.Optional(CONF_VALVE_FORCE): select.select_schema(
        ValveForceSelect,
        entity_category=ENTITY_CATEGORY_CONFIG,
        icon="mdi:valve",
    ),
}


async def to_code(config):
    therm_component = await cg.get_variable(config[CONF_THERM_ID])
    if valve_force_config := config.get(CONF_VALVE_FORCE):
        s = await select.new_select(
            valve_force_config, options=["none", "open", "close"]
        )
        await cg.register_parented(s, config[CONF_THERM_ID])
