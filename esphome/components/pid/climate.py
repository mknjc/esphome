import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.components import climate, sensor, output
from esphome.const import (
    CONF_ID,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_TEMPERATURE,
    CONF_MODE,
    CONF_NAME,
    CONF_PRESET,
    CONF_SENSOR,
    CONF_VISUAL,
)

CONF_PRESET_CHANGE = "preset_change"
CONF_DEFAULT_PRESET = "default_preset"

pid_ns = cg.esphome_ns.namespace("pid")
PIDClimate = pid_ns.class_("PIDClimate", climate.Climate, cg.Component)
PIDClimateTargetTempConfig = pid_ns.struct("PIDClimateTargetTempConfig")
PIDAutotuneAction = pid_ns.class_("PIDAutotuneAction", automation.Action)
PIDResetIntegralTermAction = pid_ns.class_(
    "PIDResetIntegralTermAction", automation.Action
)
PIDSetControlParametersAction = pid_ns.class_(
    "PIDSetControlParametersAction", automation.Action
)

CONF_DEFAULT_TARGET_TEMPERATURE = "default_target_temperature"

CONF_KP = "kp"
CONF_KI = "ki"
CONF_STARTING_INTEGRAL_TERM = "starting_integral_term"
CONF_KD = "kd"
CONF_CONTROL_PARAMETERS = "control_parameters"
CONF_COOL_OUTPUT = "cool_output"
CONF_HEAT_OUTPUT = "heat_output"
CONF_NOISEBAND = "noiseband"
CONF_POSITIVE_OUTPUT = "positive_output"
CONF_NEGATIVE_OUTPUT = "negative_output"
CONF_MIN_INTEGRAL = "min_integral"
CONF_MAX_INTEGRAL = "max_integral"
CONF_OUTPUT_AVERAGING_SAMPLES = "output_averaging_samples"
CONF_DERIVATIVE_AVERAGING_SAMPLES = "derivative_averaging_samples"

# Deadband parameters
CONF_DEADBAND_PARAMETERS = "deadband_parameters"
CONF_THRESHOLD_HIGH = "threshold_high"
CONF_THRESHOLD_LOW = "threshold_low"
CONF_DEADBAND_OUTPUT_AVERAGING_SAMPLES = "deadband_output_averaging_samples"
CONF_KP_MULTIPLIER = "kp_multiplier"
CONF_KI_MULTIPLIER = "ki_multiplier"
CONF_KD_MULTIPLIER = "kd_multiplier"

PRESET_CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(PIDClimateTargetTempConfig),
        cv.Required(CONF_NAME): cv.string_strict,
        cv.Optional(CONF_MODE): climate.validate_climate_mode,
        cv.Optional(CONF_DEFAULT_TARGET_TEMPERATURE): cv.temperature,
    }
)

def validate_pid_climate(config):
    # Verify that the modes for presets are valid given the configuration
    if CONF_PRESET in config:
        # Preset temperature vs Visual temperature validation

        # Default visual configuration from climate_traits.h
        visual_min_temperature = 10.0
        visual_max_temperature = 30.0
        if CONF_VISUAL in config:
            visual_config = config[CONF_VISUAL]

            if CONF_MIN_TEMPERATURE in visual_config:
                visual_min_temperature = visual_config[CONF_MIN_TEMPERATURE]

            if CONF_MAX_TEMPERATURE in visual_config:
                visual_max_temperature = visual_config[CONF_MAX_TEMPERATURE]

        for preset_config in config[CONF_PRESET]:
            if CONF_DEFAULT_TARGET_TEMPERATURE in preset_config:
                preset_temperature = preset_config[
                    CONF_DEFAULT_TARGET_TEMPERATURE
                ]
                if preset_temperature < visual_min_temperature:
                    raise cv.Invalid(
                        f"{CONF_DEFAULT_TARGET_TEMPERATURE} for {preset_config[CONF_NAME]} is set to {preset_temperature} which is less than the visual minimum temperature of {visual_min_temperature}"
                    )
                if preset_temperature > visual_max_temperature:
                    raise cv.Invalid(
                        f"{CONF_DEFAULT_TARGET_TEMPERATURE} for {preset_config[CONF_NAME]} is set to {preset_temperature} which is more than the visual maximum temperature of {visual_max_temperature}"
                    )

        # Mode validation
        for preset_config in config[CONF_PRESET]:
            if CONF_MODE not in preset_config:
                continue

            mode = preset_config[CONF_MODE]

 #           for req in requirements[mode]:
 #               if req not in config:
 #                   raise cv.Invalid(
 #                       f"{CONF_MODE} is set to {mode} for {preset_config[CONF_NAME]} but {req} is not present in the configuration"
 #                   )

    if CONF_DEFAULT_PRESET in config:
        default_preset = config[CONF_DEFAULT_PRESET]

        if CONF_PRESET not in config:
            raise cv.Invalid(
                f"{CONF_DEFAULT_PRESET} is specified but no presets are defined"
            )

        presets = config[CONF_PRESET]
        found_preset = False

        for preset in presets:
            if preset[CONF_NAME] == default_preset:
                found_preset = True
                break

        if found_preset is False:
            raise cv.Invalid(
                f"{CONF_DEFAULT_PRESET} set to '{default_preset}' but no such preset has been defined. Available presets: {[preset[CONF_NAME] for preset in presets]}"
            )
    return config


CONFIG_SCHEMA = cv.All(
    climate.CLIMATE_SCHEMA.extend(
        {
            cv.GenerateID(): cv.declare_id(PIDClimate),
            cv.Required(CONF_SENSOR): cv.use_id(sensor.Sensor),
            cv.Required(CONF_DEFAULT_TARGET_TEMPERATURE): cv.temperature,
            cv.Optional(CONF_COOL_OUTPUT): cv.use_id(output.FloatOutput),
            cv.Optional(CONF_HEAT_OUTPUT): cv.use_id(output.FloatOutput),
            cv.Optional(CONF_DEADBAND_PARAMETERS): cv.Schema(
                {
                    cv.Required(CONF_THRESHOLD_HIGH): cv.temperature,
                    cv.Required(CONF_THRESHOLD_LOW): cv.temperature,
                    cv.Optional(CONF_KP_MULTIPLIER, default=0.1): cv.float_,
                    cv.Optional(CONF_KI_MULTIPLIER, default=0.0): cv.float_,
                    cv.Optional(CONF_KD_MULTIPLIER, default=0.0): cv.float_,
                    cv.Optional(
                        CONF_DEADBAND_OUTPUT_AVERAGING_SAMPLES, default=1
                    ): cv.int_,
                }
            ),
            cv.Required(CONF_CONTROL_PARAMETERS): cv.Schema(
                {
                    cv.Required(CONF_KP): cv.float_,
                    cv.Optional(CONF_KI, default=0.0): cv.float_,
                    cv.Optional(CONF_KD, default=0.0): cv.float_,
                    cv.Optional(CONF_STARTING_INTEGRAL_TERM, default=0.0): cv.float_,
                    cv.Optional(CONF_MIN_INTEGRAL, default=-1): cv.float_,
                    cv.Optional(CONF_MAX_INTEGRAL, default=1): cv.float_,
                    cv.Optional(CONF_DERIVATIVE_AVERAGING_SAMPLES, default=1): cv.int_,
                    cv.Optional(CONF_OUTPUT_AVERAGING_SAMPLES, default=1): cv.int_,
                }
            ),
            cv.Optional(CONF_DEFAULT_PRESET): cv.templatable(cv.string),
            cv.Optional(CONF_PRESET): cv.ensure_list(PRESET_CONFIG_SCHEMA),
            cv.Optional(CONF_PRESET_CHANGE): automation.validate_automation(
                single=True
            )
        }
    ),
    cv.has_at_least_one_key(CONF_COOL_OUTPUT, CONF_HEAT_OUTPUT),
    validate_pid_climate,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await climate.register_climate(var, config)

    sens = await cg.get_variable(config[CONF_SENSOR])
    cg.add(var.set_sensor(sens))

    if CONF_COOL_OUTPUT in config:
        out = await cg.get_variable(config[CONF_COOL_OUTPUT])
        cg.add(var.set_cool_output(out))
    if CONF_HEAT_OUTPUT in config:
        out = await cg.get_variable(config[CONF_HEAT_OUTPUT])
        cg.add(var.set_heat_output(out))
    params = config[CONF_CONTROL_PARAMETERS]
    cg.add(var.set_kp(params[CONF_KP]))
    cg.add(var.set_ki(params[CONF_KI]))
    cg.add(var.set_kd(params[CONF_KD]))
    cg.add(var.set_starting_integral_term(params[CONF_STARTING_INTEGRAL_TERM]))
    cg.add(var.set_derivative_samples(params[CONF_DERIVATIVE_AVERAGING_SAMPLES]))

    cg.add(var.set_output_samples(params[CONF_OUTPUT_AVERAGING_SAMPLES]))

    if CONF_MIN_INTEGRAL in params:
        cg.add(var.set_min_integral(params[CONF_MIN_INTEGRAL]))
    if CONF_MAX_INTEGRAL in params:
        cg.add(var.set_max_integral(params[CONF_MAX_INTEGRAL]))

    if CONF_DEADBAND_PARAMETERS in config:
        params = config[CONF_DEADBAND_PARAMETERS]
        cg.add(var.set_threshold_low(params[CONF_THRESHOLD_LOW]))
        cg.add(var.set_threshold_high(params[CONF_THRESHOLD_HIGH]))
        cg.add(var.set_kp_multiplier(params[CONF_KP_MULTIPLIER]))
        cg.add(var.set_ki_multiplier(params[CONF_KI_MULTIPLIER]))
        cg.add(var.set_kd_multiplier(params[CONF_KD_MULTIPLIER]))
        cg.add(
            var.set_deadband_output_samples(
                params[CONF_DEADBAND_OUTPUT_AVERAGING_SAMPLES]
            )
        )

    cg.add(var.set_default_target_temperature(config[CONF_DEFAULT_TARGET_TEMPERATURE]))

    if CONF_PRESET in config:
        for preset_config in config[CONF_PRESET]:
            name = preset_config[CONF_NAME]
            standard_preset = None
            if name.upper() in climate.CLIMATE_PRESETS:
                standard_preset = climate.CLIMATE_PRESETS[name.upper()]
            preset_target_config = PIDClimateTargetTempConfig(
                preset_config[CONF_DEFAULT_TARGET_TEMPERATURE]
            )

            preset_target_variable = cg.new_variable(
                preset_config[CONF_ID], preset_target_config
            )

            if CONF_MODE in preset_config:
                cg.add(preset_target_variable.set_mode(preset_config[CONF_MODE]))

            if standard_preset is not None:
                cg.add(var.set_preset_config(standard_preset, preset_target_variable))
            else:
                cg.add(var.set_custom_preset_config(name, preset_target_variable))

    if CONF_DEFAULT_PRESET in config:
        default_preset_name = config[CONF_DEFAULT_PRESET]

        # if the name is a built in preset use the appropriate naming format
        if default_preset_name.upper() in climate.CLIMATE_PRESETS:
            climate_preset = climate.CLIMATE_PRESETS[default_preset_name.upper()]
            cg.add(var.set_default_preset(climate_preset))
        else:
            cg.add(var.set_default_preset(default_preset_name))

    if CONF_PRESET_CHANGE in config:
        await automation.build_automation(
            var.get_preset_change_trigger(), [], config[CONF_PRESET_CHANGE]
        )



@automation.register_action(
    "climate.pid.reset_integral_term",
    PIDResetIntegralTermAction,
    automation.maybe_simple_id(
        {
            cv.Required(CONF_ID): cv.use_id(PIDClimate),
        }
    ),
)
async def pid_reset_integral_term(config, action_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    return cg.new_Pvariable(action_id, template_arg, paren)


@automation.register_action(
    "climate.pid.autotune",
    PIDAutotuneAction,
    automation.maybe_simple_id(
        {
            cv.Required(CONF_ID): cv.use_id(PIDClimate),
            cv.Optional(CONF_NOISEBAND, default=0.25): cv.float_,
            cv.Optional(
                CONF_POSITIVE_OUTPUT, default=1.0
            ): cv.possibly_negative_percentage,
            cv.Optional(
                CONF_NEGATIVE_OUTPUT, default=-1.0
            ): cv.possibly_negative_percentage,
        }
    ),
)
async def esp8266_set_frequency_to_code(config, action_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    var = cg.new_Pvariable(action_id, template_arg, paren)
    cg.add(var.set_noiseband(config[CONF_NOISEBAND]))
    cg.add(var.set_positive_output(config[CONF_POSITIVE_OUTPUT]))
    cg.add(var.set_negative_output(config[CONF_NEGATIVE_OUTPUT]))
    return var


@automation.register_action(
    "climate.pid.set_control_parameters",
    PIDSetControlParametersAction,
    automation.maybe_simple_id(
        {
            cv.Required(CONF_ID): cv.use_id(PIDClimate),
            cv.Required(CONF_KP): cv.templatable(cv.float_),
            cv.Optional(CONF_KI, default=0.0): cv.templatable(cv.float_),
            cv.Optional(CONF_KD, default=0.0): cv.templatable(cv.float_),
        }
    ),
)
async def set_control_parameters(config, action_id, template_arg, args):
    paren = await cg.get_variable(config[CONF_ID])
    var = cg.new_Pvariable(action_id, template_arg, paren)

    kp_template_ = await cg.templatable(config[CONF_KP], args, float)
    cg.add(var.set_kp(kp_template_))

    ki_template_ = await cg.templatable(config[CONF_KI], args, float)
    cg.add(var.set_ki(ki_template_))

    kd_template_ = await cg.templatable(config[CONF_KD], args, float)
    cg.add(var.set_kd(kd_template_))

    return var
