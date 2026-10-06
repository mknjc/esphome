from esphome import automation
import esphome.codegen as cg
from esphome.components import climate, number, output, sensor
import esphome.config_validation as cv
from esphome.const import (
    CONF_HUMIDITY_SENSOR,
    CONF_ID,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_TEMPERATURE,
    CONF_MODE,
    CONF_NAME,
    CONF_PRESET,
    CONF_RESTORE_STATE,
    CONF_SENSOR,
    CONF_VISUAL,
    UNIT_CELSIUS,
    DEVICE_CLASS_TEMPERATURE,
    ENTITY_CATEGORY_CONFIG,
)
from esphome.core import Lambda
from esphome.types import ConfigType

CONF_PRESET_CHANGE = "preset_change"
CONF_CLIMATE_MODE = "climate_mode"
CONF_DEFAULT_PRESET = "default_preset"

pid_ns = cg.esphome_ns.namespace("pid")
PIDClimate = pid_ns.class_("PIDClimate", climate.Climate, cg.Component)
PIDClimatePreset = pid_ns.class_("PIDClimatePreset", number.Number, cg.Component)
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


def _validate_thresholds(config: ConfigType) -> ConfigType:
    # Same rule as PIDClimate::set_deadband_thresholds; equal is allowed since 0/0 is the default.
    if config[CONF_THRESHOLD_LOW] > config[CONF_THRESHOLD_HIGH]:
        raise cv.Invalid(
            f"{CONF_THRESHOLD_LOW} must not be greater than {CONF_THRESHOLD_HIGH}"
        )
    return config


def _validate_threshold_action(config: ConfigType) -> ConfigType:
    threshold_low = config[CONF_THRESHOLD_LOW]
    threshold_high = config[CONF_THRESHOLD_HIGH]
    if isinstance(threshold_low, Lambda) or isinstance(threshold_high, Lambda):
        return config
    return _validate_thresholds(config)


AUTO_LOAD = ["climate", "sensor", "output", "number"]

PRESET_CONFIG_SCHEMA = (
    number.number_schema(
        PIDClimatePreset,
        unit_of_measurement=UNIT_CELSIUS,
        icon="mdi:thermometer",
        device_class=DEVICE_CLASS_TEMPERATURE,
        entity_category=ENTITY_CATEGORY_CONFIG
        )
    .extend(
        {
            cv.Required(CONF_PRESET): cv.string_strict,
            cv.Required(CONF_DEFAULT_TARGET_TEMPERATURE): cv.temperature,
            cv.Optional(CONF_CLIMATE_MODE): climate.validate_climate_mode,
            cv.Optional(CONF_RESTORE_STATE, default=True): cv.boolean,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
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
            preset_temp = preset_config[CONF_DEFAULT_TARGET_TEMPERATURE]
            if not (visual_min_temperature <= preset_temp <= visual_max_temperature):
                raise cv.Invalid(
                    f"{CONF_DEFAULT_TARGET_TEMPERATURE} for preset {preset_config[CONF_NAME]} is set to {preset_temp}, which is outside the visual temperature range of {visual_min_temperature} to {visual_max_temperature}"
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
    climate.climate_schema(PIDClimate).extend(
        {
            cv.Required(CONF_SENSOR): cv.use_id(sensor.Sensor),
            cv.Optional(CONF_HUMIDITY_SENSOR): cv.use_id(sensor.Sensor),
            cv.Required(CONF_DEFAULT_TARGET_TEMPERATURE): cv.temperature,
            cv.Optional(CONF_COOL_OUTPUT): cv.use_id(output.FloatOutput),
            cv.Optional(CONF_HEAT_OUTPUT): cv.use_id(output.FloatOutput),
            cv.Optional(CONF_DEADBAND_PARAMETERS): cv.All(
                {
                    cv.Required(CONF_THRESHOLD_HIGH): cv.temperature_delta,
                    cv.Required(CONF_THRESHOLD_LOW): cv.temperature_delta,
                    cv.Optional(CONF_KP_MULTIPLIER, default=0.1): cv.float_,
                    cv.Optional(CONF_KI_MULTIPLIER, default=0.0): cv.float_,
                    cv.Optional(CONF_KD_MULTIPLIER, default=0.0): cv.float_,
                    cv.Optional(
                        CONF_DEADBAND_OUTPUT_AVERAGING_SAMPLES, default=1
                    ): cv.positive_not_null_int,
                },
                _validate_thresholds,
            ),
            cv.Required(CONF_CONTROL_PARAMETERS): cv.Schema(
                {
                    cv.Required(CONF_KP): cv.float_,
                    cv.Optional(CONF_KI, default=0.0): cv.float_,
                    cv.Optional(CONF_KD, default=0.0): cv.float_,
                    cv.Optional(CONF_STARTING_INTEGRAL_TERM, default=0.0): cv.float_,
                    cv.Optional(CONF_MIN_INTEGRAL, default=-1): cv.float_,
                    cv.Optional(CONF_MAX_INTEGRAL, default=1): cv.float_,
                    cv.Optional(
                        CONF_DERIVATIVE_AVERAGING_SAMPLES, default=1
                    ): cv.positive_not_null_int,
                    cv.Optional(
                        CONF_OUTPUT_AVERAGING_SAMPLES, default=1
                    ): cv.positive_not_null_int,
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


async def to_code(config: ConfigType) -> None:
    var = await climate.new_climate(config)
    await cg.register_component(var, config)

    sens = await cg.get_variable(config[CONF_SENSOR])
    cg.add(var.set_sensor(sens))

    if CONF_HUMIDITY_SENSOR in config:
        sens = await cg.get_variable(config[CONF_HUMIDITY_SENSOR])
        cg.add(var.set_humidity_sensor(sens))

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

    output_samples = params[CONF_OUTPUT_AVERAGING_SAMPLES]
    cg.add(var.set_output_samples(output_samples))

    if CONF_MIN_INTEGRAL in params:
        cg.add(var.set_min_integral(params[CONF_MIN_INTEGRAL]))
    if CONF_MAX_INTEGRAL in params:
        cg.add(var.set_max_integral(params[CONF_MAX_INTEGRAL]))

    deadband_output_samples = 1
    if CONF_DEADBAND_PARAMETERS in config:
        params = config[CONF_DEADBAND_PARAMETERS]
        cg.add(var.set_threshold_low(params[CONF_THRESHOLD_LOW]))
        cg.add(var.set_threshold_high(params[CONF_THRESHOLD_HIGH]))
        cg.add(var.set_kp_multiplier(params[CONF_KP_MULTIPLIER]))
        cg.add(var.set_ki_multiplier(params[CONF_KI_MULTIPLIER]))
        cg.add(var.set_kd_multiplier(params[CONF_KD_MULTIPLIER]))
        deadband_output_samples = params[CONF_DEADBAND_OUTPUT_AVERAGING_SAMPLES]
        cg.add(var.set_deadband_output_samples(deadband_output_samples))

    # Single shared output buffer sized to max of both modes
    cg.add(var.init_output_buffer(max(output_samples, deadband_output_samples)))

    cg.add(var.set_default_target_temperature(config[CONF_DEFAULT_TARGET_TEMPERATURE]))

    if CONF_PRESET in config:
        visual = config[CONF_VISUAL]

        for preset_config in config[CONF_PRESET]:
            name = preset_config[CONF_PRESET]
            preset_target_config = None
            if name.upper() in climate.CLIMATE_PRESETS:
                standard_preset = climate.CLIMATE_PRESETS[name.upper()]
                default_target_temp = preset_config[CONF_DEFAULT_TARGET_TEMPERATURE]
            
                preset_target_config = await number.new_number(
                    preset_config,
                    standard_preset, default_target_temp,
                    min_value=visual.get(CONF_MIN_TEMPERATURE, 10.0),
                    max_value=visual.get(CONF_MAX_TEMPERATURE, 30.0),
                    step=0.1,
                )
            else:
                preset_target_config = await number.new_number(
                    preset_config,
                    name, default_target_temp,
                    min_value=visual.get(CONF_MIN_TEMPERATURE, 10.0),
                    max_value=visual.get(CONF_MAX_TEMPERATURE, 30.0),
                    step=0.1,
                )

            if CONF_CLIMATE_MODE in preset_config:
                cg.add(preset_target_config.set_climate_mode(preset_config[CONF_CLIMATE_MODE]))

            cg.add(preset_target_config.set_restore_state(preset_config[CONF_RESTORE_STATE]))

            await cg.register_parented(preset_target_config, var)
            await cg.register_component(preset_target_config, preset_config)
            cg.add(var.add_preset_config(preset_target_config))

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



automation.register_apply_action(
    "climate.pid.reset_integral_term",
    automation.maybe_simple_id(
        {
            cv.Required(CONF_ID): cv.use_id(PIDClimate),
        }
    ),
    automation.ApplyCall("reset_integral_term()"),
)


automation.register_apply_action(
    "climate.pid.autotune",
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
    automation.ApplyCall(
        "start_autotune({}, {}, {})",
        (
            (CONF_NOISEBAND, cg.float_),
            (CONF_POSITIVE_OUTPUT, cg.float_),
            (CONF_NEGATIVE_OUTPUT, cg.float_),
        ),
    ),
)


automation.register_apply_action(
    "climate.pid.set_control_parameters",
    automation.maybe_simple_id(
        {
            cv.Required(CONF_ID): cv.use_id(PIDClimate),
            cv.Required(CONF_KP): cv.templatable(cv.float_),
            cv.Optional(CONF_KI, default=0.0): cv.templatable(cv.float_),
            cv.Optional(CONF_KD, default=0.0): cv.templatable(cv.float_),
        }
    ),
    automation.ApplyField(CONF_KP, "set_kp", cg.float_),
    automation.ApplyField(CONF_KI, "set_ki", cg.float_),
    automation.ApplyField(CONF_KD, "set_kd", cg.float_),
)


automation.register_apply_action(
    "climate.pid.set_deadband_control_parameters_multipliers",
    automation.maybe_simple_id(
        {
            cv.Required(CONF_ID): cv.use_id(PIDClimate),
            # kp_multiplier is required for compatibility with the original action API;
            # ki_multiplier and kd_multiplier are optional overrides.
            cv.Required(CONF_KP_MULTIPLIER): cv.templatable(cv.float_),
            cv.Optional(CONF_KI_MULTIPLIER): cv.templatable(cv.float_),
            cv.Optional(CONF_KD_MULTIPLIER): cv.templatable(cv.float_),
        }
    ),
    automation.ApplyField(CONF_KP_MULTIPLIER, "set_kp_multiplier", cg.float_),
    automation.ApplyField(CONF_KI_MULTIPLIER, "set_ki_multiplier", cg.float_),
    automation.ApplyField(CONF_KD_MULTIPLIER, "set_kd_multiplier", cg.float_),
)


automation.register_apply_action(
    "climate.pid.set_deadband_threshold_parameters",
    automation.maybe_simple_id(
        cv.All(
            {
                cv.Required(CONF_ID): cv.use_id(PIDClimate),
                cv.Required(CONF_THRESHOLD_HIGH): cv.templatable(cv.temperature_delta),
                cv.Required(CONF_THRESHOLD_LOW): cv.templatable(cv.temperature_delta),
            },
            _validate_threshold_action,
        )
    ),
    automation.ApplyCall(
        "set_deadband_thresholds({}, {})",
        ((CONF_THRESHOLD_LOW, cg.float_), (CONF_THRESHOLD_HIGH, cg.float_)),
    ),
)
