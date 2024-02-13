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
        cv.GenerateID(CONF_THERM_ID): cv.use_id(ThermComponent),
        cv.Required(CONF_TYPE): cv.enum(TYPE, lower=True),
    }
)


async def to_code(config):
    paren = await cg.get_variable(config[CONF_THERM_ID])
    var = cg.new_Pvariable(config[CONF_ID])
    var.set_parent(paren)
    var.set_type(TYPE[config[CONF_TYPE]])
    await output.register_output(var, config)
    return var