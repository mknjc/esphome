#include "therm.h"

#include "esphome/core/application.h"

namespace esphome {
namespace therm {

static const char *const TAG = "therm";

static const uint8_t INA3221_REGISTER_CONFIG = 0x00;
static const uint8_t INA3221_REGISTER_CHANNEL1_SHUNT_VOLTAGE = 0x01;
static const uint8_t INA3221_REGISTER_CHANNEL1_BUS_VOLTAGE = 0x02;
static const uint8_t INA3221_REGISTER_CHANNEL2_SHUNT_VOLTAGE = 0x03;
static const uint8_t INA3221_REGISTER_CHANNEL2_BUS_VOLTAGE = 0x04;
static const uint8_t INA3221_REGISTER_CHANNEL3_SHUNT_VOLTAGE = 0x05;
static const uint8_t INA3221_REGISTER_CHANNEL3_BUS_VOLTAGE = 0x06;
static const uint8_t INA3221_REGISTER_CHANNEL1_CRITICAL_ALERT_LIMIT = 0x07;
static const uint8_t INA3221_REGISTER_CHANNEL1_WARNING_ALERT_LIMIT = 0x08;
static const uint8_t INA3221_REGISTER_CHANNEL2_CRITICAL_ALERT_LIMIT = 0x09;
static const uint8_t INA3221_REGISTER_CHANNEL2_WARNING_ALERT_LIMIT = 0x0A;
static const uint8_t INA3221_REGISTER_CHANNEL3_CRITICAL_ALERT_LIMIT = 0x0B;
static const uint8_t INA3221_REGISTER_CHANNEL3_WARNING_ALERT_LIMIT = 0x0C;
static const uint8_t INA3221_REGISTER_SHUNT_VOLTAGE_SUM = 0x0D;
static const uint8_t INA3221_REGISTER_SHUNT_VOLTAGE_SUM_LIMIT = 0x0E;
static const uint8_t INA3221_REGISTER_MASK_ENABLE = 0x0F;
static const uint8_t INA3221_REGISTER_POWER_VALID_UPPER_LIMIT = 0x10;
static const uint8_t INA3221_REGISTER_POWER_VALID_LOWER_LIMIT = 0x11;
static const uint8_t INA3221_REGISTER_MANUFACTURER_ID = 0xFE;
static const uint8_t INA3221_REGISTER_DIE_ID = 0xFF;

std::pair<uint16_t, uint16_t> static calculate_config(MeasurementParameter param, bool single_shot) {
  uint16_t config = 0;
  uint32_t duration = 0;
  switch (param.integration_time) {
    case IntegrationTime::US140:
      duration += 140;
      break;
    case IntegrationTime::US204:
      duration += 204;
      break;
    case IntegrationTime::US332:
      duration += 332;
      break;
    case IntegrationTime::US588:
      duration += 588;
      break;
    case IntegrationTime::US1100:
      duration += 1100;
      break;
    case IntegrationTime::US2116:
      duration += 2116;
      break;
    case IntegrationTime::US4156:
      duration += 4156;
      break;
    case IntegrationTime::US8244:
      duration += 8244;
      break;
  }
  switch (param.averaging) {
    case Averaging::SAMPLE_1:
      duration *= 1;
      break;
    case Averaging::SAMPLE_4:
      duration *= 4;
      break;
    case Averaging::SAMPLE_16:
      duration *= 16;
      break;
    case Averaging::SAMPLE_64:
      duration *= 64;
      break;
    case Averaging::SAMPLE_128:
      duration *= 128;
      break;
    case Averaging::SAMPLE_256:
      duration *= 256;
      break;
    case Averaging::SAMPLE_512:
      duration *= 512;
      break;
    case Averaging::SAMPLE_1024:
      duration *= 1024;
      break;
  }

  uint8_t channel_count = 0;
  // 0b0xxx000000000000 << 12 Channel Enables (1 -> ON)
  if (param.channels & Channel::CHANNEL1_BUS || param.channels & Channel::CHANNEL1_SHUNT) {
    config |= 0b0100000000000000;
    channel_count++;
  }
  if (param.channels & Channel::CHANNEL2_BUS || param.channels & Channel::CHANNEL2_SHUNT) {
    config |= 0b0010000000000000;
    channel_count++;
  }
  if (param.channels & Channel::CHANNEL3_BUS || param.channels & Channel::CHANNEL3_SHUNT) {
    config |= 0b0001000000000000;
    channel_count++;
  }
  bool bus = param.channels & Channel::CHANNEL1_BUS || param.channels & Channel::CHANNEL2_BUS ||
             param.channels & Channel::CHANNEL3_BUS;
  bool shunt = param.channels & Channel::CHANNEL1_SHUNT || param.channels & Channel::CHANNEL2_SHUNT ||
               param.channels & Channel::CHANNEL3_SHUNT;

  if (bus && shunt) {
    channel_count *= 2;
  }

  // 0b0000xxx000000000 << 9 Averaging Mode (0 -> 1 sample, 111 -> 1024 samples)
  config |= static_cast<uint16_t>(param.averaging) << 9;
  // 0b0000000xxx000000 << 6 Bus Voltage Conversion time (100 -> 1.1ms, 111 -> 8.244 ms)
  config |= static_cast<uint16_t>(param.integration_time) << 6;
  // 0b0000000000xxx000 << 3 Shunt Voltage Conversion time (same as above)
  config |= static_cast<uint16_t>(param.integration_time) << 3;
  // 0b000000000000x00 << 2 Operating mode (1 = continuous)
  config |= single_shot ? 0b0000000000000000 : 0b0000000000000100;
  // 0b0000000000000x0 << 1 Bus voltage measurement
  config |= bus ? 0b0000000000000010 : 0b0000000000000000;
  // 0b00000000000000x << 0 Shunt voltage measurement
  config |= shunt ? 0b0000000000000001 : 0b0000000000000000;

  return std::make_pair(config, (duration * channel_count) / 1000);
}

bool ThermComponent::measure(MeasurementParameter param) {
  auto [config, duration] = calculate_config(param, true);
  if (!this->write_byte_16(INA3221_REGISTER_CONFIG, config)) {
    ESP_LOGE(TAG, "Error setting config");
    return false;
  }
  ESP_LOGV(TAG, "Waiting for %d ms", duration);
  delay(duration);

  uint16_t mask_reg;

  for (int i = 0; i < 1000; i++) {
    if (!this->read_bytes_16(INA3221_REGISTER_MASK_ENABLE, &mask_reg, 1)) {
      ESP_LOGE(TAG, "Error reading mask register");
      return false;
    }
    if (mask_reg & 0x1) {
      break;
    }
    delay(1);
  }
  if (mask_reg & 0x1) {
    return true;
  } else {
    ESP_LOGE(TAG, "Conversion never finished");
    return false;
  }
}

void ThermComponent::setup() {
  uint16_t manufacturer_id;
  uint16_t die_id;
  auto ret = read_register(INA3221_REGISTER_MANUFACTURER_ID, reinterpret_cast<uint8_t *>(&manufacturer_id), 2);
  if (ret != i2c::ERROR_OK) {
    ESP_LOGE(TAG, "Error reading manufacturer id: %d", ret);
    mark_failed();
    return;
  }
  manufacturer_id = convert_big_endian(manufacturer_id);
  if (manufacturer_id != 0x5449) {
    ESP_LOGE(TAG, "Invalid manufacturer id: 0x%04X", manufacturer_id);
    mark_failed();
    return;
  }
  ret = read_register(INA3221_REGISTER_DIE_ID, reinterpret_cast<uint8_t *>(&die_id), 2);
  if (ret != i2c::ERROR_OK) {
    ESP_LOGE(TAG, "Error reading die id: %d", ret);
    mark_failed();
    return;
  }
  die_id = convert_big_endian(die_id);
  if (die_id != 0x3220) {
    ESP_LOGE(TAG, "Invalid die id: 0x%04X", die_id);
    mark_failed();
    return;
  }
  ESP_LOGD(TAG, "INA3221 Manufacturer id: 0x%04X, die id: 0x%04X", manufacturer_id, die_id);

  if (!this->write_byte_16(INA3221_REGISTER_CONFIG, 0x8000)) {
    ESP_LOGE(TAG, "Error resetting");
    this->mark_failed();
    return;
  }
  delay(10);

  // inital read voltages
  measure(MeasurementParameter{IntegrationTime::US8244, Averaging::SAMPLE_1,
                               Channel::CHANNEL1_BUS | Channel::CHANNEL2_BUS | Channel::CHANNEL3_BUS});
  uint16_t valve_voltage, fan_voltage, continuous_voltage;
  if (!this->read_bytes_16(INA3221_REGISTER_CHANNEL1_BUS_VOLTAGE, &valve_voltage, 1)) {
    ESP_LOGE(TAG, "Error reading valve voltage");
    this->mark_failed();
    return;
  }
  if (!this->read_bytes_16(INA3221_REGISTER_CHANNEL2_BUS_VOLTAGE, &fan_voltage, 1)) {
    ESP_LOGE(TAG, "Error reading fan voltage");
    this->mark_failed();
    return;
  }
  if (!this->read_bytes_16(INA3221_REGISTER_CHANNEL3_BUS_VOLTAGE, &continuous_voltage, 1)) {
    ESP_LOGE(TAG, "Error reading continuous voltage");
    this->mark_failed();
    return;
  }
  ESP_LOGD(TAG, "Continuous voltage: %f, Valve voltage: %f, Fan voltage: %f", valve_voltage / 1000.0,
           fan_voltage / 1000.0, continuous_voltage / 1000.0);
}

void ThermComponent::update_fan() {}

void ThermComponent::read_bus_voltage(uint8_t ch) {
  uint16_t bus_voltage;
  if (!this->read_bytes_16(INA3221_REGISTER_CHANNEL1_BUS_VOLTAGE + ch * 2, &bus_voltage, 1)) {
    ESP_LOGE(TAG, "Error reading bus voltage");
    this->mark_failed();
    return;
  }
  if (this->bus_voltage_sensor_[ch]) {
    this->bus_voltage_sensor_[ch]->publish_state(bus_voltage / 1000.0);
  }
}
void ThermComponent::read_shunt(uint8_t ch) {
  uint16_t shunt_voltage;
  if (!this->read_bytes_16(INA3221_REGISTER_CHANNEL1_SHUNT_VOLTAGE + ch * 2, &shunt_voltage, 1)) {
    ESP_LOGE(TAG, "Error reading shunt voltage");
    this->mark_failed();
    return;
  }
  ESP_LOGV(TAG, "Raw Shunt voltage for channel %d: %d", ch, shunt_voltage);
  if (ch == 1) {
    ESP_LOGD(TAG, "Raw Shunt voltage for channel %d: %d", ch, shunt_voltage);
  }

  const float shunt_voltage_v = int16_t(shunt_voltage) * 40.0f / 8.0f / 1000000.0f;
  if (this->shunt_voltage_sensor_[ch]) {
    this->shunt_voltage_sensor_[ch]->publish_state(shunt_voltage_v);
  }
  if (this->current_sensor_[ch] && this->shunt_resistance_[ch] > 0.0f) {
    this->current_sensor_[ch]->publish_state(shunt_voltage_v / this->shunt_resistance_[ch]);
  }
}

float ThermComponent::valve_open_time() const {
  switch (this->valve_force_)
  {
  case ValveForce::CLOSE:
    return 0.0;
  case ValveForce::OPEN:
    return this->period_;
  case ValveForce::NONE:
    break;
  }
  return (float(this->period_) * this->valve_value_);
}

void ThermComponent::loop() {
  auto now = millis();

  if (now - this->state_start_ >= this->state_duration_) {
    this->state_start_ += this->state_duration_;

    switch (this->state_) {
      case State::WAIT_FOR_PERIOD_START:
        this->period_start_ = this->state_start_;

        this->valve_measure_counter_++;
        if (this->valve_measure_counter_ >= this->measure_interval_) {
          if (this->valve_position_sensor != nullptr) {
            switch (this->valve_force_) {
              case ValveForce::CLOSE:
                this->valve_position_sensor->publish_state(0.0f);
                break;
              case ValveForce::OPEN:
                this->valve_position_sensor->publish_state(100.0f);
                break;
              case ValveForce::NONE:
                this->valve_position_sensor->publish_state(this->valve_value_ * 100.0f);
                break;
            }
          }
          read_bus_voltage(0);
          read_bus_voltage(1);
          read_bus_voltage(2);
          read_shunt(0);
          read_shunt(2);

          this->valve_measure_counter_ = 0;
          this->state_ = State::VALVE_CURRENT_MEASUREMENT_WAIT;
          this->valve_output_->digital_write(true);  // do it as fast as possible to help with measurement stabilisation
          ESP_LOGD(TAG, "Valve current measurement start %d", now);
          auto [config, duration] = calculate_config(
              MeasurementParameter{IntegrationTime::US8244, Averaging::SAMPLE_1, Channel::CHANNEL2_SHUNT}, true);

          if (!this->write_byte_16(INA3221_REGISTER_CONFIG, config)) {
            ESP_LOGE(TAG, "Error setting config");
            this->mark_failed();
            return;
          }
          this->state_duration_ = duration;
        } else {
          float valve_open_time_ = valve_open_time();
          if (valve_open_time_ > 0) {
            this->valve_output_->digital_write(true);
            this->state_ = State::VALVE_CLOSE_WAIT;
            this->state_duration_ = valve_open_time_;
          } else {
            this->state_ = State::WAIT_FOR_PERIOD_START;
            this->state_duration_ = this->period_;
          }
        }
        break;
      case State::VALVE_CURRENT_MEASUREMENT_WAIT: {
        uint16_t mask_reg;
        if (!this->read_bytes_16(INA3221_REGISTER_MASK_ENABLE, &mask_reg, 1)) {
          ESP_LOGE(TAG, "Error reading mask register");
          this->mark_failed();
          return;
        }
        if (!(mask_reg & 0x1)) {
          ESP_LOGW(TAG, "Valve current measurement did not finished finished");
          return;
        }

        ESP_LOGD(TAG, "Valve current measurement finished %d", now);
        this->read_shunt(1);
        auto [config, duration] = calculate_config(
            MeasurementParameter{IntegrationTime::US8244, Averaging::SAMPLE_16,
                                 Channel::CHANNEL1_BUS | Channel::CHANNEL2_BUS | Channel::CHANNEL3_BUS |
                                     Channel::CHANNEL1_SHUNT | Channel::CHANNEL3_SHUNT},
            true);

        if (!this->write_byte_16(INA3221_REGISTER_CONFIG, config)) {
          ESP_LOGE(TAG, "Error setting config");
          this->mark_failed();
          return;
        }

        float valve_open_time_ = (valve_open_time()) - this->state_duration_;
        if (valve_open_time_ > 0) {
          this->state_ = State::VALVE_CLOSE_WAIT;
          this->state_duration_ = valve_open_time_;
        } else {
          this->valve_output_->digital_write(false);
          this->state_ = State::WAIT_FOR_PERIOD_START;
          this->state_duration_ = (this->period_ + this->period_start_) - this->state_start_;
        }
      } break;
      case State::VALVE_CLOSE_WAIT:
        this->valve_output_->digital_write(false);
        this->state_ = State::WAIT_FOR_PERIOD_START;
        this->state_duration_ = (this->period_ + this->period_start_) - this->state_start_;
        break;
    }
  }
}

void ThermComponent::dump_config() {}

void ThermOutput::write_state(float state) {
  if (this->parent_ == nullptr) {
    ESP_LOGE(TAG, "Parent not set");
    return;
  }

  if (this->type_ == OutputType::VALVE) {
    this->parent_->set_valve_value(state);
  } else {
    this->parent_->set_fan_value(state);
  }
}

void ValveForceSelect::setup() {
  this->publish_state("none");
}

void ValveForceSelect::control(const std::string &value) {
  if (value == "none") {
    this->parent_->valve_force_ = ValveForce::NONE;
    this->publish_state(value);
    return;
  } else if (value == "open") {
    this->parent_->valve_force_ = ValveForce::OPEN;
    this->publish_state(value);
    return;
  } else if (value == "close") {
    this->parent_->valve_force_ = ValveForce::CLOSE;
    this->publish_state(value);
    return;
  } else {
    ESP_LOGE(TAG, "Invalid valve force value: %s", value.c_str());
    return;
  }
}


}  // namespace therm
}  // namespace esphome