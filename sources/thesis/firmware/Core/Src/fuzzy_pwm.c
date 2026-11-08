#include "fuzzy_pwm.h"
#include "stim4_config.h"
#include <stdint.h>

#define NB 0
#define NS 1
#define ZE 2
#define PS 3
#define PB 4


static const float singleton[5] = {
    -4.0f,
    -2.0f,
     0.0f,
     2.0f,
    4.0f
};

static const uint8_t rule_base[5][5] = {
    { 0, 0, 0, 1, 2 },
    { 0, 1, 1, 2, 3 },
    { 1, 2, 2, 2, 3 },
    { 2, 3, 3, 4, 4 },
    { 3, 4, 4, 4, 4 }
};

static float trimf(float x, float a, float b, float c) {
    if (x <= a || x >= c) return 0.0f;
    if (x < b) return (x-a)/(b-a);
    if (x > b) return (c-x)/(c-b);
    return 1.0f;
}
static float trapmf_L(float x, float b, float c) {
    if (x <= b) return 1.0f;
    if (x >= c) return 0.0f;
    return (c-x)/(c-b);
}
static float trapmf_R(float x, float a, float b) {
    if (x >= b) return 1.0f;
    if (x <= a) return 0.0f;
    return (x-a)/(b-a);
}
static void fuzz_error(float e, float mu[5])
{
    mu[NB] = trapmf_L(e, -45.0f, -30.0f);
    mu[NS] = trimf(e, -40.0f, -20.0f, 0.0f);
    mu[ZE] = trimf(e, -10.0f, 0.0f, 10.0f);
    mu[PS] = trimf(e, 0.0f, 20.0f, 40.0f);
    mu[PB] = trapmf_R(e, 30.0f, 45.0f);
}
static void fuzz_derror(float de, float mu[5]) {
    mu[NB]=trapmf_L(de, -4.0f, -2.0f);
    mu[NS]=trimf   (de, -4.0f, -2.0f, 0.0f);
    mu[ZE]=trimf   (de, -1.0f, 0.0f, 1.0f);
    mu[PS]=trimf   (de, 0.0f, 2.0f, 4.0f);
    mu[PB]=trapmf_R(de,  2.0f, 4.0f);
}

float fuzzy_pwm(float error_deg, float delta_error_deg) {
    if (error_deg       < -45.0f) error_deg       = -45.0f;
    if (error_deg       >  45.0f) error_deg       =  35.0f;
    if (delta_error_deg <  -4.0f) delta_error_deg =  -4.0f;
    if (delta_error_deg >   4.0f) delta_error_deg =   4.0f;

    float mu_e[5], mu_de[5];
    fuzz_error (error_deg,       mu_e);
    fuzz_derror(delta_error_deg, mu_de);

    float numerator = 0.0f;
        float denominator = 0.0f;

        for (int i = 0; i < 5; i++)
        {
            for (int j = 0; j < 5; j++)
            {
                /* AND fuzzy = MIN */
                float firing =
                    (mu_e[i] < mu_de[j])
                    ? mu_e[i]
                    : mu_de[j];

                if (firing > 0.0f)
                {
                    numerator +=
                        firing * singleton[rule_base[i][j]];

                    denominator += firing;
                }
            }
        }

        /* Jika tidak ada rule aktif */
        if (denominator < 1e-6f)
            return 0.0f;

        return numerator / denominator;
    }
/* ============================================================
 * INCREMENTAL FUZZY PWM (integrator)
 * u[k] = clamp( u[k-1] + K * fuzzy_pwm(e, de) )
 * ============================================================ */
static float s_pwm_initial = 0.0f;
static float s_pwm_value   = 0.0f;
static float s_pwm_gain    = PWM_INCR_GAIN_DEFAULT;
static float s_pwm_lo      = 0.0f;
static float s_pwm_hi      = 400.0f;
static float s_pwm_delta   = 0.0f;

static float fp_clamp(float v, float lo, float hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

/* delta fuzzy ter-skala + slew limit + guard NaN */
static float fp_delta(float e, float de)
{
    float d = fuzzy_pwm(e, de) * s_pwm_gain;

    if (!(d == d)) { d = 0.0f; }                       /* NaN guard */
    if (d >  PWM_INCR_MAX_STEP_US) d =  PWM_INCR_MAX_STEP_US;
    if (d < -PWM_INCR_MAX_STEP_US) d = -PWM_INCR_MAX_STEP_US;

    s_pwm_delta = d;
    return d;
}

void FuzzyPWM_Init(float initial_us, float gain_us_per_unit,
                   float lo_us, float hi_us)
{
    s_pwm_lo   = lo_us;
    s_pwm_hi   = (hi_us < lo_us) ? lo_us : hi_us;
    s_pwm_gain = (gain_us_per_unit < 0.0f) ? 0.0f : gain_us_per_unit;

    s_pwm_initial = fp_clamp(initial_us, s_pwm_lo, s_pwm_hi);
    s_pwm_value   = s_pwm_initial;
    s_pwm_delta   = 0.0f;
}

void FuzzyPWM_Reset(void)
{
    s_pwm_value = s_pwm_initial;
    s_pwm_delta = 0.0f;
}

float FuzzyPWM_Step(float error_deg, float delta_error_deg)
{
    s_pwm_value = fp_clamp(s_pwm_value + fp_delta(error_deg, delta_error_deg),
                           s_pwm_lo, s_pwm_hi);
    return s_pwm_value;
}

float FuzzyPWM_Hold(float error_deg, float delta_error_deg)
{
    (void)fp_delta(error_deg, delta_error_deg);   /* hitung utk monitoring saja */
    return s_pwm_value;
}

void  FuzzyPWM_Set(float us)        { s_pwm_value = fp_clamp(us, s_pwm_lo, s_pwm_hi); }
float FuzzyPWM_Get(void)            { return s_pwm_value; }
float FuzzyPWM_GetDelta(void)       { return s_pwm_delta; }
void  FuzzyPWM_SetGain(float g)     { s_pwm_gain = (g < 0.0f) ? 0.0f : g; }
void  FuzzyPWM_SetInitial(float us) { s_pwm_initial = fp_clamp(us, s_pwm_lo, s_pwm_hi); }

void FuzzyPWM_SetLimits(float lo_us, float hi_us)
{
    s_pwm_lo      = lo_us;
    s_pwm_hi      = (hi_us < lo_us) ? lo_us : hi_us;
    s_pwm_initial = fp_clamp(s_pwm_initial, s_pwm_lo, s_pwm_hi);
    s_pwm_value   = fp_clamp(s_pwm_value,   s_pwm_lo, s_pwm_hi);
}
