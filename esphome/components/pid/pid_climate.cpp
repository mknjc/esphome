#include "pid_climate.h"
#include "esphome/core/log.h"
#include "esphome/components/climate/climate_mode.h"

namespace esphome {
namespace pid {

static const char *const TAG = "pid.climate";

void PIDClimatePreset::setup() {
  float value = 0.0f;
  if (this->restore_state_) {
    this->pref_ = global_preferences->make_preference<float>(this->get_preference_hash());
    if (!this->pref_.load(&value)) {
      value = default_target_temperature_;
    }
  } else {
    value = default_target_temperature_;
  }
  this->publish_state(value);
}

void PIDClimatePreset::control(float value) {
  this->publish_state(value);
  auto *parent = this->get_parent();
  if (parent != nullptr) {
    parent->preset_update_(this);
  }

  if (this->restore_state_)
    this->pref_.save(&value);
}

PIDClimate::PIDClimate() : preset_change_trigger_(new Trigger<>()) {}

void PIDClimate::setup() {
  this->sensor_->add_on_state_callback([this](float state) {
    // only publish if state/current temperature has changed in two digits of precision
    this->do_publish_ = roundf(state * 100) != roundf(this->current_temperature * 100);
    this->current_temperature = state;
    this->update_pid_();
  });
  this->current_temperature = this->sensor_->state;

  // register for humidity values and get initial state
  if (this->humidity_sensor_ != nullptr) {
    this->humidity_sensor_->add_on_state_callback([this](float state) {
      this->current_humidity = state;
      this->publish_state();
    });
    this->current_humidity = this->humidity_sensor_->state;
  }

  // restore set points
  auto restore = this->restore_state_();
  if (restore.has_value()) {
    restore->to_call(this).perform();
  } else {
    // restore from defaults, change_away handles those for us
    if (supports_heat_() && supports_cool_()) {
      this->mode = climate::CLIMATE_MODE_HEAT_COOL;
    } else if (supports_cool_()) {
      this->mode = climate::CLIMATE_MODE_COOL;
    } else if (supports_heat_()) {
      this->mode = climate::CLIMATE_MODE_HEAT;
    }
    this->target_temperature = this->default_target_temperature_;

    if (this->default_preset_ != climate::ClimatePreset::CLIMATE_PRESET_NONE) {
      this->change_preset_(this->default_preset_);
    } else if (this->default_custom_preset_ != nullptr) {
      this->change_custom_preset_(this->default_custom_preset_);
    }
  }
}
void PIDClimate::control(const climate::ClimateCall &call) {
  if (call.get_preset().has_value()) {
    this->change_preset_(*call.get_preset());
  }
  if (call.get_custom_preset() != nullptr) {
    this->change_custom_preset_(call.get_custom_preset());
  }

  if (call.get_mode().has_value())
    this->mode = *call.get_mode();
  if (call.get_target_temperature().has_value())
    this->target_temperature = *call.get_target_temperature();

  // If switching to off mode, set output immediately
  if (this->mode == climate::CLIMATE_MODE_OFF)
    this->write_output_(0.0f);

  this->publish_state();
}
climate::ClimateTraits PIDClimate::traits() {
  auto traits = climate::ClimateTraits();
  traits.add_feature_flags(climate::CLIMATE_SUPPORTS_CURRENT_TEMPERATURE | climate::CLIMATE_SUPPORTS_ACTION);

  if (this->humidity_sensor_ != nullptr)
    traits.add_feature_flags(climate::CLIMATE_SUPPORTS_CURRENT_HUMIDITY);

  traits.set_supported_modes({climate::CLIMATE_MODE_OFF});
  if (supports_cool_())
    traits.add_supported_mode(climate::CLIMATE_MODE_COOL);
  if (supports_heat_())
    traits.add_supported_mode(climate::CLIMATE_MODE_HEAT);
  if (supports_heat_() && supports_cool_())
    traits.add_supported_mode(climate::CLIMATE_MODE_HEAT_COOL);

  std::vector<const char *> custom_presets;
  for (auto &it : this->preset_config_) {
    if (it->is_custom_preset()) {
      custom_presets.push_back(it->get_custom_preset());
    } else {
      traits.add_supported_preset(it->get_preset());
    }
  }
  traits.set_supported_custom_presets(custom_presets);

  traits.add_feature_flags(climate::CLIMATE_SUPPORTS_ACTION);
  return traits;
}

void PIDClimate::dump_preset_config_(const char *preset_name, const PIDClimatePreset *config,
                                     bool is_default_preset) {
  ESP_LOGCONFIG(TAG, "      %s Is Default: %s", preset_name, YESNO(is_default_preset));
  ESP_LOGCONFIG(TAG, "      %s Target Temperature: %.1f°C", preset_name, config->state);

  if (config->climate_mode_.has_value()) {
    ESP_LOGCONFIG(TAG, "      %s Mode: %s", preset_name,
                  LOG_STR_ARG(climate::climate_mode_to_string(*config->climate_mode_)));
  }
}
void PIDClimate::dump_config() {
  LOG_CLIMATE("", "PID Climate", this);
  ESP_LOGCONFIG(TAG,
                "  Control Parameters:\n"
                "    kp: %.5f, ki: %.5f, kd: %.5f, output samples: %d",
                controller_.kp_, controller_.ki_, controller_.kd_, controller_.output_samples_);

  if (controller_.threshold_low_ == 0 && controller_.threshold_high_ == 0) {
    ESP_LOGCONFIG(TAG, "  Deadband disabled.");
  } else {
    ESP_LOGCONFIG(TAG,
                  "  Deadband Parameters:\n"
                  "    threshold: %0.5f to %0.5f, multipliers(kp: %.5f, ki: %.5f, kd: %.5f), "
                  "output samples: %d",
                  controller_.threshold_low_, controller_.threshold_high_, controller_.kp_multiplier_,
                  controller_.ki_multiplier_, controller_.kd_multiplier_, controller_.deadband_output_samples_);
  }

  ESP_LOGCONFIG(TAG, "  Supported PRESETS: ");
  for (auto &it : this->preset_config_) {
    if (it->is_custom_preset()) {
      continue;
    }

    const auto *preset_name = LOG_STR_ARG(climate::climate_preset_to_string(it->get_preset()));

    ESP_LOGCONFIG(TAG, "    Supports %s: %s", preset_name, YESNO(true));
    this->dump_preset_config_(preset_name, it, it->get_preset() == this->default_preset_);
  }

  ESP_LOGCONFIG(TAG, "  Supported CUSTOM PRESETS: ");
  for (auto &it : this->preset_config_) {
    if (!it->is_custom_preset()) {
      continue;
    }
    const char *preset_name = it->get_custom_preset();

    ESP_LOGCONFIG(TAG, "    Supports %s: %s", preset_name, YESNO(true));
    this->dump_preset_config_(preset_name, it, it->get_custom_preset() == this->default_custom_preset_);
  }

  if (this->autotuner_ != nullptr) {
    this->autotuner_->dump_config();
  }
}

void PIDClimate::change_preset_(climate::ClimatePreset preset) {
  auto config = std::find_if(
      this->preset_config_.begin(), this->preset_config_.end(),
      [preset](PIDClimatePreset* cfg) { return !cfg->is_custom_preset() && cfg->get_preset() == preset; });

  if (config != this->preset_config_.end()) {
    ESP_LOGI(TAG, "Preset %s requested", LOG_STR_ARG(climate::climate_preset_to_string(preset)));
    if (this->change_preset_internal_(*config) || (!this->preset.has_value()) ||
        this->preset.value() != preset) {
      // Fire any preset changed trigger if defined
      Trigger<> *trig = this->preset_change_trigger_;
      assert(trig != nullptr);
      trig->trigger();

      ESP_LOGI(TAG, "Preset %s applied", LOG_STR_ARG(climate::climate_preset_to_string(preset)));
    } else {
      ESP_LOGI(TAG, "No changes required to apply preset %s", LOG_STR_ARG(climate::climate_preset_to_string(preset)));
    }
    this->clear_custom_preset_();
    this->preset = preset;
  } else {
    ESP_LOGE(TAG, "Preset %s is not configured, ignoring.", LOG_STR_ARG(climate::climate_preset_to_string(preset)));
  }
}

void PIDClimate::change_custom_preset_(const char *custom_preset) {
  auto config = std::find_if(
      this->preset_config_.begin(), this->preset_config_.end(),
      [custom_preset](PIDClimatePreset* cfg) { return cfg->is_custom_preset() && strcmp(cfg->get_custom_preset(), custom_preset) == 0; });

  if (config != this->preset_config_.end()) {
    ESP_LOGI(TAG, "Custom preset %s requested", custom_preset);
    if (this->change_preset_internal_(*config) || (this->has_custom_preset()) ||
        this->get_custom_preset() != custom_preset) {
      // Fire any preset changed trigger if defined
      Trigger<> *trig = this->preset_change_trigger_;
      assert(trig != nullptr);
      trig->trigger();

      ESP_LOGI(TAG, "Custom preset %s applied", custom_preset);
    } else {
      ESP_LOGI(TAG, "No changes required to apply custom preset %s", custom_preset);
    }
    this->preset.reset();
    this->set_custom_preset_(custom_preset);
  } else {
    ESP_LOGE(TAG, "Custom Preset %s is not configured, ignoring.", custom_preset);
  }
}

bool PIDClimate::change_preset_internal_(const PIDClimatePreset *config) {
  bool something_changed = false;

  float new_target_temperature = config->state;

  if (this->target_temperature != new_target_temperature) {
    this->target_temperature = new_target_temperature;
    something_changed = true;
  }

  // Note: The mode can be defined in the preset but if the climate.control call also specifies them then
  // the climate.control call's values will override the preset's values for that call
  if (config->climate_mode_.has_value() && (this->mode != config->climate_mode_.value())) {
    ESP_LOGV(TAG, "Setting mode to %s", LOG_STR_ARG(climate::climate_mode_to_string(*config->climate_mode_)));
    this->mode = *config->climate_mode_;
    something_changed = true;
  }

  // If switching to off mode, set output immediately
  if (this->mode == climate::CLIMATE_MODE_OFF)
    this->write_output_(0.0f);

  this->publish_state();
  return something_changed;
}

void PIDClimate::write_output_(float value) {
  this->output_value_ = value;

  // first ensure outputs are off (both outputs not active at the same time)
  if (this->supports_cool_() && value >= 0)
    this->cool_output_->set_level(0.0f);
  if (this->supports_heat_() && value <= 0)
    this->heat_output_->set_level(0.0f);

  // value < 0 means cool, > 0 means heat
  if (this->supports_cool_() && value < 0)
    this->cool_output_->set_level(std::min(1.0f, -value));
  if (this->supports_heat_() && value > 0)
    this->heat_output_->set_level(std::min(1.0f, value));

  // Update action variable for user feedback what's happening
  climate::ClimateAction new_action;
  if (this->supports_cool_() && value < 0) {
    new_action = climate::CLIMATE_ACTION_COOLING;
  } else if (this->supports_heat_() && value > 0) {
    new_action = climate::CLIMATE_ACTION_HEATING;
  } else if (this->mode == climate::CLIMATE_MODE_OFF) {
    new_action = climate::CLIMATE_ACTION_OFF;
  } else {
    new_action = climate::CLIMATE_ACTION_IDLE;
  }

  if (new_action != this->action) {
    this->action = new_action;
    this->do_publish_ = true;
  }
  this->pid_computed_callback_.call();
}
void PIDClimate::update_pid_() {
  float value;
  if (std::isnan(this->current_temperature) || std::isnan(this->target_temperature)) {
    // if any control parameters are nan, turn off all outputs
    value = 0.0;
  } else {
    // Update PID controller irrespective of current mode, to not mess up D/I terms
    // In non-auto mode, we just discard the output value
    value = this->controller_.update(this->target_temperature, this->current_temperature);

    // Check autotuner
    if (this->autotuner_ != nullptr && !this->autotuner_->is_finished()) {
      auto res = this->autotuner_->update(this->target_temperature, this->current_temperature);
      if (res.result_params.has_value()) {
        this->controller_.kp_ = res.result_params->kp;
        this->controller_.ki_ = res.result_params->ki;
        this->controller_.kd_ = res.result_params->kd;
        // keep autotuner instance so that subsequent dump_configs will print the long result message.
      } else {
        value = res.output;
      }
    }
  }

  if (this->mode == climate::CLIMATE_MODE_OFF) {
    this->write_output_(0.0);
  } else {
    this->write_output_(value);
  }

  if (this->do_publish_)
    this->publish_state();
}
void PIDClimate::start_autotune(std::unique_ptr<PIDAutotuner> &&autotune) {
  this->autotuner_ = std::move(autotune);
  float min_value = this->supports_cool_() ? -1.0f : 0.0f;
  float max_value = this->supports_heat_() ? 1.0f : 0.0f;
  this->autotuner_->config(min_value, max_value);
  this->autotuner_->set_autotuner_id(this->get_name());

  ESP_LOGI(TAG,
           "%s: Autotune has started. This can take a long time depending on the "
           "responsiveness of your system. Your system "
           "output will be altered to deliberately oscillate above and below the setpoint multiple times. "
           "Until your sensor provides a reading, the autotuner may display \'nan\'",
           this->get_name().c_str());

  this->set_interval("autotune-progress", 10000, [this]() {
    if (this->autotuner_ != nullptr && !this->autotuner_->is_finished())
      this->autotuner_->dump_config();
  });

  if (mode != climate::CLIMATE_MODE_HEAT_COOL) {
    ESP_LOGW(TAG, "%s: !!! For PID autotuner you need to set AUTO (also called heat/cool) mode!",
             this->get_name().c_str());
  }
}

void PIDClimate::preset_update_(const PIDClimatePreset *config) {
  // A preset has changed its target temperature, re-apply current preset to update
  if (this->preset.has_value()) {
    this->change_preset_(*this->preset);
  } else if (this->has_custom_preset()) {
    this->change_custom_preset_(this->get_custom_preset());
  }
}

void PIDClimate::reset_integral_term() { this->controller_.reset_accumulated_integral(); }

}  // namespace pid
}  // namespace esphome
