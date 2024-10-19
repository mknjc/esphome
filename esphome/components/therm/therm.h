#pragma once

#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/core/automation.h"
#include "esphome/core/gpio.h"

#include "esphome/components/i2c/i2c.h"
#include "esphome/components/ledc/ledc_output.h"
#include "esphome/components/select/select.h"
#include "esphome/components/sensor/sensor.h"

namespace esphome {
namespace therm {

enum class IntegrationTime : std::uint8_t {
  US140 = 0b000,
  US204 = 0b001,
  US332 = 0b010,
  US588 = 0b011,
  US1100 = 0b100,
  US2116 = 0b101,
  US4156 = 0b110,
  US8244 = 0b111,
};
enum class Averaging : std::uint8_t {
  SAMPLE_1 = 0b000,
  SAMPLE_4 = 0b001,
  SAMPLE_16 = 0b010,
  SAMPLE_64 = 0b011,
  SAMPLE_128 = 0b100,
  SAMPLE_256 = 0b101,
  SAMPLE_512 = 0b110,
  SAMPLE_1024 = 0b111,
};

enum Channel : std::uint8_t {
  CHANNEL1_BUS = 0b000,
  CHANNEL2_BUS = 0b001,
  CHANNEL3_BUS = 0b010,
  CHANNEL1_SHUNT = 0b011,
  CHANNEL2_SHUNT = 0b100,
  CHANNEL3_SHUNT = 0b101,
};

struct MeasurementParameter {
  IntegrationTime integration_time;
  Averaging averaging;
  std::uint8_t channels;
};

enum class OutputType {
  VALVE,
  FAN,
};

class ThermComponent;

class ThermOutput : public output::FloatOutput, public Parented<ThermComponent> {
 public:
  void set_type(OutputType type) { this->type_ = type; }

 protected:
  void write_state(float state) override;

 private:
  OutputType type_;
};

enum class State {
  WAIT_FOR_PERIOD_START,
  VALVE_CURRENT_MEASUREMENT_WAIT,
  VALVE_CLOSE_WAIT,
};

enum class ValveForce {
  NONE,
  OPEN,
  CLOSE
};

class ValveForceSelect : public select::Select, public Parented<ThermComponent> {
  public:
    void setup();
  protected:
    void control(const std::string &option) override;
};

class ThermComponent : public i2c::I2CDevice, public Component {
  friend class ThermOutput;
  friend class ValveForceSelect;

 public:
  void setup() override;
  void dump_config() override;
  /// HARDWARE setup priority
  float get_setup_priority() const override { return setup_priority::PROCESSOR; }

  void set_valve_output(GPIOPin *valve_output) { this->valve_output_ = valve_output; }
  void set_fan_output(ledc::LEDCOutput *fan_output) { this->fan_output_ = fan_output; }
  void set_r_output(GPIOPin *r_output) { this->r_output_ = r_output; }
  void set_g_output(GPIOPin *g_output) { this->g_output_ = g_output; }
  void set_b_output(GPIOPin *b_output) { this->b_output_ = b_output; }

  void set_shunt_resistance(uint8_t ch, float shunt_resistance) { this->shunt_resistance_[ch] = shunt_resistance; }
  void set_bus_voltage_sensor(uint8_t ch, sensor::Sensor *bus_voltage_sensor) {
    this->bus_voltage_sensor_[ch] = bus_voltage_sensor;
  }
  void set_shunt_voltage_sensor(uint8_t ch, sensor::Sensor *shunt_voltage_sensor) {
    this->shunt_voltage_sensor_[ch] = shunt_voltage_sensor;
  }
  void set_current_sensor(uint8_t ch, sensor::Sensor *current_sensor) { this->current_sensor_[ch] = current_sensor; }
  void set_power_sensor(uint8_t ch, sensor::Sensor *power_sensor) { this->power_sensor_[ch] = power_sensor; }

  void set_valve_position_sensor(sensor::Sensor *valve_sensor) { this->valve_position_sensor = valve_sensor; }

  void set_period(uint32_t period) { this->period_ = period; }
  void set_measure_interval(uint32_t measure_interval) { this->measure_interval_ = measure_interval; }

  void loop() override;

 private:
  void set_valve_value(float value) { this->valve_value_ = value; }
  void set_fan_value(float value) {
    this->fan_value_ = value;

    if (this->fan_output_) {
      ESP_LOGD("therm", "Setting fan value: %f", value);
      this->fan_output_->write_state(value);
    }
  }

  bool measure(MeasurementParameter param);

  void update_fan();

  void read_bus_voltage(uint8_t ch);
  void read_shunt(uint8_t ch);

  float valve_open_time() const;

  GPIOPin *valve_output_;
  ledc::LEDCOutput *fan_output_;
  GPIOPin *r_output_;
  GPIOPin *g_output_;
  GPIOPin *b_output_;

  float shunt_resistance_[3] = {0.0, 0.0, 0.0};
  sensor::Sensor *bus_voltage_sensor_[3] = {nullptr, nullptr, nullptr};
  sensor::Sensor *shunt_voltage_sensor_[3] = {nullptr, nullptr, nullptr};
  sensor::Sensor *current_sensor_[3] = {nullptr, nullptr, nullptr};
  sensor::Sensor *power_sensor_[3] = {nullptr, nullptr, nullptr};

  sensor::Sensor *valve_position_sensor = nullptr;

  float valve_value_ = 0.0;
  float fan_value_ = 0.0;

  uint32_t period_;
  State state_ = State::WAIT_FOR_PERIOD_START;
  uint32_t state_start_ = 0;
  uint32_t state_duration_ = 0;
  uint32_t period_start_ = 0;

  uint32_t valve_measure_counter_ = 0;
  uint32_t measure_interval_;

  ValveForce valve_force_ = ValveForce::NONE;
};

}  // namespace therm
}  // namespace esphome