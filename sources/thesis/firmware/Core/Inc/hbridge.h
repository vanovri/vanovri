#ifndef HBRIDGE_H
#define HBRIDGE_H

#include "main.h"
#include "stim4_config.h"

void HBridge_Init(void);
void HBridge_Start(void);
void HBridge_Stop(void);
void HBridge_SetParams(float pw_us, float freq_hz);
void HBridge_TimerCallback(void);  /* Panggil dari HAL_TIM_PeriodElapsedCallback */

#endif
