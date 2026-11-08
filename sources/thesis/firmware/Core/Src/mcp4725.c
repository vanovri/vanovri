#include "mcp4725.h"

extern I2C_HandleTypeDef hi2c1;

HAL_StatusTypeDef MCP4725_SetVoltage(float voltage_v) {
    if (voltage_v < 0.0f)     voltage_v = 0.0f;
    if (voltage_v > DAC_VREF) voltage_v = DAC_VREF;
    uint16_t dac=(uint16_t)((voltage_v/DAC_VREF)*DAC_RES);
    uint8_t buf[2];
    buf[0]=(uint8_t)((dac>>8)&0x0F);
    buf[1]=(uint8_t)(dac&0xFF);
    return HAL_I2C_Master_Transmit(&hi2c1, MCP4725_ADDR, buf, 2, 10);
}

HAL_StatusTypeDef MCP4725_SetCurrent_mA(float current_mA) {
    if (current_mA < I_MIN_MA) current_mA = I_MIN_MA;
    if (current_mA > I_MAX_MA) current_mA = I_MAX_MA;
    float v=(current_mA/1000.0f)*RSENSE_OHM;
    return MCP4725_SetVoltage(v);
}
