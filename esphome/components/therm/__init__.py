from esphome import pins
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import i2c
from esphome.components.ledc.output import LEDCOutput

from esphome.const import (
    CONF_BLUE,
    CONF_GREEN,
    CONF_ID,
    CONF_RED,
    CONF_PERIOD,
)

MULTI_CONF = True

CODEOWNERS = ["@mknjc"]
DEPENDENCIES = ["i2c"]

CONF_THERM_ID = "therm_id"

CONF_VALVE_OUTPUT = "valve_output"
CONF_FAN_OUTPUT = "fan_output"

CONF_VALVE_SHUNT_RESISTANCE = "valve_shunt_resistance"
CONF_FAN_SHUNT_RESISTANCE = "fan_shunt_resistance"
CONF_CONTINUOUS_SHUNT_RESISTANCE = "continuous_shunt_resistance"

CONF_MEASURE_INTERVAL = "measure_interval"

therm_ns = cg.esphome_ns.namespace("therm")
ThermComponent = therm_ns.class_("ThermComponent", cg.Component, i2c.I2CDevice)


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.Required(CONF_ID): cv.declare_id(ThermComponent),

            cv.Required(CONF_VALVE_OUTPUT): pins.gpio_output_pin_schema,
            cv.Optional(CONF_FAN_OUTPUT): cv.use_id(LEDCOutput),

            cv.Optional(CONF_RED): pins.gpio_output_pin_schema,
            cv.Optional(CONF_GREEN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_BLUE): pins.gpio_output_pin_schema,

            cv.Required(CONF_VALVE_SHUNT_RESISTANCE): cv.positive_float,
            cv.Optional(CONF_FAN_SHUNT_RESISTANCE): cv.positive_float,
            cv.Optional(CONF_CONTINUOUS_SHUNT_RESISTANCE): cv.positive_float,

            cv.Optional(CONF_MEASURE_INTERVAL, default=10): cv.positive_not_null_int,
            cv.Optional(CONF_PERIOD, default="1s"): cv.positive_not_null_time_period,
        }
    )
    .extend(i2c.i2c_device_schema(0x40))
    .extend(cv.COMPONENT_SCHEMA),
    cv.has_none_or_all_keys(CONF_FAN_OUTPUT, CONF_FAN_SHUNT_RESISTANCE)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)

    pin = await cg.gpio_pin_expression(config[CONF_VALVE_OUTPUT])
    cg.add(var.set_valve_output(pin))

    if CONF_FAN_OUTPUT in config:
        fan_out = await cg.get_variable(config[CONF_FAN_OUTPUT])
        cg.add(var.set_fan_output(fan_out))

    if CONF_RED in config:
        pin = await cg.gpio_pin_expression(config[CONF_RED])
        cg.add(var.set_r_output(pin))
    
    if CONF_GREEN in config:
        pin = await cg.gpio_pin_expression(config[CONF_GREEN])
        cg.add(var.set_g_output(pin))
    
    if CONF_BLUE in config:
        pin = await cg.gpio_pin_expression(config[CONF_BLUE])
        cg.add(var.set_b_output(pin))

    cg.add(var.set_shunt_resistance(1, config[CONF_VALVE_SHUNT_RESISTANCE]))
    
    if CONF_FAN_SHUNT_RESISTANCE in config:
        cg.add(var.set_shunt_resistance(2, config[CONF_FAN_SHUNT_RESISTANCE]))
    
    if CONF_CONTINUOUS_SHUNT_RESISTANCE in config:
        cg.add(var.set_shunt_resistance(0, config[CONF_CONTINUOUS_SHUNT_RESISTANCE]))

    cg.add(var.set_period(config[CONF_PERIOD]))
    cg.add(var.set_measure_interval(config[CONF_MEASURE_INTERVAL]))