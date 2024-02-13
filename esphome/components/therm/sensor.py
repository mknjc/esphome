import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import i2c, sensor
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
    STATE_CLASS_MEASUREMENT,
    UNIT_VOLT,
    UNIT_AMPERE,
    UNIT_WATT,
)

DEPENDENCIES = ["therm"]

CONF_VALVE = "valve"
CONF_FAN = "fan"
CONF_CONTINUOUS = "continuous"

CHANNEL_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_BUS_VOLTAGE): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_SHUNT_VOLTAGE): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=3,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_CURRENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_AMPERE,
            accuracy_decimals=3,
            device_class=DEVICE_CLASS_CURRENT,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_POWER): sensor.sensor_schema(
            unit_of_measurement=UNIT_WATT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_POWER,
            state_class=STATE_CLASS_MEASUREMENT,
        )
    }
)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(CONF_THERM_ID): cv.use_id(ThermComponent),
            cv.Optional(CONF_VALVE): CHANNEL_SCHEMA,
            cv.Optional(CONF_FAN): CHANNEL_SCHEMA,
            cv.Optional(CONF_CONTINUOUS): CHANNEL_SCHEMA,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)

    for i, channel in enumerate([CONF_VALVE, CONF_FAN, CONF_CONTINUOUS]):
        if channel not in config:
            continue
        conf = config[channel]
        if CONF_BUS_VOLTAGE in conf:
            sens = await sensor.new_sensor(conf[CONF_BUS_VOLTAGE])
            cg.add(var.set_bus_voltage_sensor(i, sens))
        if CONF_SHUNT_VOLTAGE in conf:
            sens = await sensor.new_sensor(conf[CONF_SHUNT_VOLTAGE])
            cg.add(var.set_shunt_voltage_sensor(i, sens))
        if CONF_CURRENT in conf:
            sens = await sensor.new_sensor(conf[CONF_CURRENT])
            cg.add(var.set_current_sensor(i, sens))
        if CONF_POWER in conf:
            sens = await sensor.new_sensor(conf[CONF_POWER])
            cg.add(var.set_power_sensor(i, sens))
