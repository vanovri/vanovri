#ifndef FUZZY_PW_H
#define FUZZY_PW_H
float fuzzy_pw(float error_deg, float delta_error_deg);
void FuzzyPW_Init(float initial_us, float gain_us_per_unit, float lo_us, float hi_us);
void FuzzyPW_Reset(void);
float FuzzyPW_Step(float error_deg, float delta_error_deg);
float FuzzyPW_Hold(float error_deg, float delta_error_deg);
void FuzzyPW_Set(float us);
float FuzzyPW_Get(void);
float FuzzyPW_GetDelta(void);
void FuzzyPW_SetGain(float gain_us_per_unit);
void FuzzyPW_SetLimits(float lo_us, float hi_us);
void FuzzyPW_SetInitial(float initial_us);
#endif
