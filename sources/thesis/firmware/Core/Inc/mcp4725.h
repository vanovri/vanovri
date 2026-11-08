#ifndef MCP4725_H
#define MCP4725_H

#include "main.h"
#include "stim4_config.h"

HAL_StatusTypeDef MCP4725_SetVoltage(float voltage_v);
HAL_StatusTypeDef MCP4725_SetCurrent_mA(float current_mA);

#endif
