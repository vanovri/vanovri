#ifndef FUZZY_PWM_H
#define FUZZY_PWM_H

/*
 * Fuzzy Sugeno 5x5 — Incremental PWM
 *
 * Input 1 : Error sudut       -35° ... +35°
 * Input 2 : Delta error       -10° ... +10°
 * Output  : Delta PWM         -10 ... +10 µs
 *
 * Output fuzzy bukan PWM final.
 * Output digunakan untuk mengubah PWbase.
 */
float fuzzy_pwm(float error_deg, float delta_error_deg);
/* ============================================================
 * INCREMENTAL API  —  u[k] = u[k-1] + K * fuzzy_pwm(e, de)
 * ============================================================ */
void  FuzzyPWM_Init(float initial_us, float gain_us_per_unit,
                    float lo_us, float hi_us);
void  FuzzyPWM_Reset(void);                                   /* balik ke initial     */
float FuzzyPWM_Step(float error_deg, float delta_error_deg);  /* integrasi -> absolut */
float FuzzyPWM_Hold(float error_deg, float delta_error_deg);  /* monitor, tanpa integrasi */
void  FuzzyPWM_Set(float us);                                 /* sinkronisasi eksternal   */
float FuzzyPWM_Get(void);
float FuzzyPWM_GetDelta(void);                                /* delta terakhir [us/tick] */
void  FuzzyPWM_SetGain(float gain_us_per_unit);
void  FuzzyPWM_SetLimits(float lo_us, float hi_us);
void  FuzzyPWM_SetInitial(float initial_us);
#endif
