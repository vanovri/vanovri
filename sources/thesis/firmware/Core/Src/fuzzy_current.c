#include "fuzzy_current.h"
#include "stim4_config.h"

#define NB 0
#define NS 1
#define ZE 2
#define PS 3
#define PB 4

#define I_NB    0.0f
#define I_NS    7.5f
#define I_ZE   15.0f
#define I_PS   22.5f
#define I_PB   30.0f

static const float i_rule[5][5] = {
    { I_NB, I_NB, I_NS, I_NS, I_ZE },
    { I_NB, I_NS, I_NS, I_ZE, I_PS },
    { I_NS, I_NS, I_ZE, I_PS, I_PS },
    { I_NS, I_ZE, I_PS, I_PS, I_PB },
    { I_ZE, I_PS, I_PS, I_PB, I_PB },
};

/* FIX: Pisahkan setiap if ke baris sendiri agar tidak ada warning
 *      -Wmisleading-indentation dari GCC */
static float trimf(float x, float a, float b, float c) {
    if (x <= a || x >= c) return 0.0f;
    if (x < b)  return (x - a) / (b - a);
    if (x > b)  return (c - x) / (c - b);
    return 1.0f;
}

static float trapmf_L(float x, float b, float c) {
    if (x <= b) return 1.0f;
    if (x >= c) return 0.0f;
    return (c - x) / (c - b);
}

static float trapmf_R(float x, float a, float b) {
    if (x >= b) return 1.0f;
    if (x <= a) return 0.0f;
    return (x - a) / (b - a);
}

static void fuzz_emag(float em, float mu[5]) {
    mu[NB] = trapmf_L(em,   0.0f,  45.0f);
    mu[NS] = trimf   (em,   0.0f,  45.0f,  90.0f);
    mu[ZE] = trimf   (em,  45.0f,  90.0f, 135.0f);
    mu[PS] = trimf   (em,  90.0f, 135.0f, 180.0f);
    mu[PB] = trapmf_R(em, 135.0f, 180.0f);
}

static void fuzz_de(float de, float mu[5]) {
    mu[NB] = trapmf_L(de, -90.0f, -45.0f);
    mu[NS] = trimf   (de, -90.0f, -45.0f,  0.0f);
    mu[ZE] = trimf   (de, -45.0f,   0.0f, 45.0f);
    mu[PS] = trimf   (de,   0.0f,  45.0f, 90.0f);
    mu[PB] = trapmf_R(de,  45.0f,  90.0f);
}

float fuzzy_current(float error_magnitude, float delta_error_deg) {
    if (error_magnitude <   0.0f) error_magnitude =   0.0f;
    if (error_magnitude > 180.0f) error_magnitude = 180.0f;
    if (delta_error_deg < -90.0f) delta_error_deg = -90.0f;
    if (delta_error_deg >  90.0f) delta_error_deg =  90.0f;

    float mu_em[5], mu_de[5];
    fuzz_emag(error_magnitude, mu_em);
    fuzz_de  (delta_error_deg, mu_de);

    float num = 0.0f, den = 0.0f;
    for (int i = 0; i < 5; i++) {
        for (int j = 0; j < 5; j++) {
            float w = (mu_em[i] < mu_de[j]) ? mu_em[i] : mu_de[j];
            if (w > 0.0f) {
                num += w * i_rule[i][j];
                den += w;
            }
        }
    }
    return (den < 1e-6f) ? I_ZE : (num / den);
}

float auto_frequency(float error_magnitude) {
    if (error_magnitude <   0.0f) error_magnitude =   0.0f;
    if (error_magnitude > 180.0f) error_magnitude = 180.0f;
    return FREQ_MIN_HZ + (error_magnitude / 180.0f) * (FREQ_MAX_HZ - FREQ_MIN_HZ);
}
