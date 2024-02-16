import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import output
from esphome.const import CONF_CHANNEL, CONF_ID
from . import therm_ns, ThermComponent, CONF_THERM_ID

DEPENDENCIES = ["therm"]

ThermOutput = therm_ns.class_("ThermOutput", output.FloatOutput)

OutputType = therm_ns.enum("OutputType")
TYPE = {
    "valve": OutputType.VALVE,
    "fan": OutputType.FAN,
}

CONF_TYPE = "type"

CONFIG_SCHEMA = output.FLOAT_OUTPUT_SCHEMA.extend(
    {
        cv.Required(CONF_ID): cv.declare_id(ThermOutput),
        cv.Required(CONF_THERM_ID): cv.use_id(ThermComponent),
        cv.Required(CONF_TYPE): cv.enum(TYPE, lower=True),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await output.register_output(var, config)

    parent = await cg.get_variable(config[CONF_THERM_ID])
    cg.add(var.set_parent(parent))

    cg.add(var.set_type(TYPE[config[CONF_TYPE]]))