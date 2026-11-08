#include "hbridge.h"

/* =============================================================================
 * H-BRIDGE 2-PIN  —  PA4 = PHASE_A, PA5 = PHASE_B
 *
 * Kontrak sinyal:
 *   A=1, B=0  -> fase A (arus positif)
 *   A=0, B=1  -> fase B (arus negatif)
 *   A=0, B=0  -> OFF / high-Z  (dead-time & rest)
 *   A=1, B=1  -> TIDAK PERNAH dihasilkan
 *
 * Satu periode stimulasi:
 *   PHASE_A (pw) -> DEAD (50us) -> PHASE_B (pw) -> DEAD (50us) -> REST -> ulang
 *   period_us = 1e6 / freq_hz
 *   rest      = period_us - (2*pw + 2*dead)
 *
 * TIM3 = 1 MHz, ARR 16-bit -> maksimum 65535 us sekali arming.
 * Pada 10 Hz rest bisa 99400 us, jadi rest dipecah menjadi beberapa chunk.
 * ========================================================================== */

#define HB_MAX_CHUNK_US   60000U   /* < 65535, aman untuk ARR 16-bit */

typedef enum {
    ST_IDLE = 0, ST_PHASE_A, ST_DEAD_A, ST_PHASE_B, ST_DEAD_B, ST_REST
} HB_State;

static volatile HB_State g_state   = ST_IDLE;
static volatile uint8_t  g_running = 0U;

/* parameter yang di-set operator (di-latch tiap awal periode) */
static volatile uint32_t g_pw_set_us   = 200U;
static volatile uint32_t g_rest_set_us = 0U;

/* parameter yang sedang dipakai periode berjalan */
static volatile uint32_t g_pw_us        = 200U;
static volatile uint32_t g_rest_us      = 0U;
static volatile uint32_t g_rest_left_us = 0U;

extern TIM_HandleTypeDef htim3;

/* ---------------------------------------------------------------- GPIO ---- */
static inline void all_off(void)
{
    HAL_GPIO_WritePin(HB_PHASE_A_PORT, HB_PHASE_A_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(HB_PHASE_B_PORT, HB_PHASE_B_PIN, GPIO_PIN_RESET);
}

static inline void phase_a_on(void)
{
    /* B dimatikan LEBIH DULU supaya A=1,B=1 tidak pernah terjadi */
    HAL_GPIO_WritePin(HB_PHASE_B_PORT, HB_PHASE_B_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(HB_PHASE_A_PORT, HB_PHASE_A_PIN, GPIO_PIN_SET);
}

static inline void phase_b_on(void)
{
    HAL_GPIO_WritePin(HB_PHASE_A_PORT, HB_PHASE_A_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(HB_PHASE_B_PORT, HB_PHASE_B_PIN, GPIO_PIN_SET);
}

/* --------------------------------------------------------------- TIMER ---- */
static void timer_start(uint32_t us)
{
    if (us < 2U)              { us = 2U; }          /* cegah underflow us-1 */
    if (us > HB_MAX_CHUNK_US) { us = HB_MAX_CHUNK_US; }

    HAL_TIM_Base_Stop_IT(&htim3);
    __HAL_TIM_SET_AUTORELOAD(&htim3, us - 1U);
    __HAL_TIM_SET_COUNTER(&htim3, 0);
    __HAL_TIM_CLEAR_FLAG(&htim3, TIM_FLAG_UPDATE);
    HAL_TIM_Base_Start_IT(&htim3);
}

/* rest panjang dipecah jadi potongan <= HB_MAX_CHUNK_US */
static void arm_rest_chunk(void)
{
    uint32_t chunk = (g_rest_left_us > HB_MAX_CHUNK_US) ? HB_MAX_CHUNK_US
                                                        : g_rest_left_us;
    g_rest_left_us -= chunk;
    timer_start(chunk);
}

static void latch_params(void)
{
    g_pw_us   = g_pw_set_us;
    g_rest_us = g_rest_set_us;
}

static void begin_new_period(void)
{
    latch_params();                 /* parameter baru berlaku mulai periode ini */
    g_state = ST_PHASE_A;
    phase_a_on();
    timer_start(g_pw_us);
}

/* ============================================================================
 * API
 * ========================================================================== */
void HBridge_Init(void)
{
    all_off();
    g_state   = ST_IDLE;
    g_running = 0U;
}

void HBridge_SetParams(float pw_us, float freq_hz)
{
    uint32_t pw;
    uint32_t dead = (uint32_t)DEAD_TIME_US;
    uint32_t period_us;
    uint32_t used;

    if (pw_us   < 1.0f) { pw_us   = 1.0f; }
    if (freq_hz < 0.1f) { freq_hz = 0.1f; }

    pw        = (uint32_t)pw_us;
    period_us = (uint32_t)(1000000.0f / freq_hz);
    used      = (2U * pw) + (2U * dead);

    g_pw_set_us   = pw;
    /* SATU rest per periode (bukan dibagi 2) supaya frekuensi keluaran benar */
    g_rest_set_us = (period_us > used) ? (period_us - used) : 0U;
}

void HBridge_Start(void)
{
    all_off();
    g_running = 1U;
    begin_new_period();
}

void HBridge_Stop(void)
{
    g_running = 0U;
    HAL_TIM_Base_Stop_IT(&htim3);
    all_off();
    g_state = ST_IDLE;
}

void HBridge_TimerCallback(void)
{
    if (g_running == 0U) { return; }

    HAL_TIM_Base_Stop_IT(&htim3);

    switch (g_state)
    {
    case ST_PHASE_A:
        all_off();
        g_state = ST_DEAD_A;
        timer_start((uint32_t)DEAD_TIME_US);
        break;

    case ST_DEAD_A:
        phase_b_on();
        g_state = ST_PHASE_B;
        timer_start(g_pw_us);
        break;

    case ST_PHASE_B:
        all_off();
        g_state = ST_DEAD_B;
        timer_start((uint32_t)DEAD_TIME_US);
        break;

    case ST_DEAD_B:
        all_off();                       /* pastikan OFF selama rest */
        if (g_rest_us > 0U) {
            g_rest_left_us = g_rest_us;
            g_state        = ST_REST;
            arm_rest_chunk();
        } else {
            begin_new_period();
        }
        break;

    case ST_REST:
        if (g_rest_left_us > 0U) {
            arm_rest_chunk();            /* masih ada sisa rest */
        } else {
            begin_new_period();
        }
        break;

    default:
        all_off();
        g_state = ST_IDLE;
        break;
    }
}
