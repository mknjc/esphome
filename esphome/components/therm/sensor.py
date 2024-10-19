import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from . import therm_ns, ThermComponent, CONF_THERM_ID

from esphome.const import (
    CONF_BUS_VOLTAGE,
    CONF_CURRENT,
    CONF_ID,
    CONF_POWER,
    CONF_SHUNT_VOLTAGE,
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    UNIT_VOLT,
    UNIT_AMPERE,
    UNIT_WATT,
)

DEPENDENCIES = ["therm"]

CONF_VALVE = "valve"
CONF_VALVE_POSITION = "valve_position"
CONF_FAN = "fan"
CONF_CONTINUOUS = "continuous"

CHANNEL_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_BUS_VOLTAGE): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
        cv.Optional(CONF_SHUNT_VOLTAGE): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=3,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
        cv.Optional(CONF_CURRENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_AMPERE,
            accuracy_decimals=3,
            device_class=DEVICE_CLASS_CURRENT,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
        cv.Optional(CONF_POWER): sensor.sensor_schema(
            unit_of_measurement=UNIT_WATT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_POWER,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
    }
)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(CONF_THERM_ID): cv.use_id(ThermComponent),
            cv.Optional(CONF_VALVE): CHANNEL_SCHEMA,
            cv.Optional(CONF_FAN): CHANNEL_SCHEMA,
            cv.Optional(CONF_CONTINUOUS): CHANNEL_SCHEMA,

            cv.Optional(CONF_VALVE_POSITION): sensor.sensor_schema(
                unit_of_measurement="%",
                accuracy_decimals=0,
                state_class=STATE_CLASS_MEASUREMENT,
                icon="mdi:valve",
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            ),
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    paren = await cg.get_variable(config[CONF_THERM_ID])

    for i, channel in enumerate([CONF_CONTINUOUS, CONF_VALVE, CONF_FAN]):
        if channel not in config:
            continue
        conf = config[channel]
        if CONF_BUS_VOLTAGE in conf:
            sens = await sensor.new_sensor(conf[CONF_BUS_VOLTAGE])
            cg.add(paren.set_bus_voltage_sensor(i, sens))
        if CONF_SHUNT_VOLTAGE in conf:
            sens = await sensor.new_sensor(conf[CONF_SHUNT_VOLTAGE])
            cg.add(paren.set_shunt_voltage_sensor(i, sens))
        if CONF_CURRENT in conf:
            sens = await sensor.new_sensor(conf[CONF_CURRENT])
            cg.add(paren.set_current_sensor(i, sens))
        if CONF_POWER in conf:
            sens = await sensor.new_sensor(conf[CONF_POWER])
            cg.add(paren.set_power_sensor(i, sens))
    
    if CONF_VALVE_POSITION in config:
        sens = await sensor.new_sensor(config[CONF_VALVE_POSITION])
        cg.add(paren.set_valve_position_sensor(sens))
