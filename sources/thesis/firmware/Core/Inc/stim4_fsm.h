#ifndef STIM4_FSM_H
#define STIM4_FSM_H

#include "main.h"
#include "stim4_config.h"
#include "fatigue_detector.h"

/* Durasi non-blocking (HAL_GetTick). */
#define FSM_ACTIVE_DURATION_MS        10000U
#define FSM_REST_DURATION_MS          10000U
#define FSM_FATIGUE_REST_DURATION_MS  15000U

/* Engineering parameter intent, wajib divalidasi pada subjek/pengujian. */
#define FSM_INTENT_MVC_RATIO 			 0.20f
#define FSM_INTENT_PERSIST_WINDOWS 		 3U


/* Batas Pulse Width. */
#define FSM_PW_MIN_US                     50.0f
#define FSM_PW_MAX_NORMAL_US             400.0f
#define FSM_PW_MAX_FATIGUE_US            320.0f
#define FSM_FATIGUE_REST_STOP_COUNT       3U

typedef enum {
    FSM_IDLE         = 0,
    FSM_ACTIVE       = 1,
    FSM_REST         = 2,
    FSM_FATIGUE_REST = 3,
    FSM_THERAPY_STOP = 4,
    FSM_EMERGENCY    = 5
} FSM_State;

typedef enum {
    ACTIVE_MODE_NORMAL  = 0,
    ACTIVE_MODE_FATIGUE = 1
} ActiveMode;

typedef struct {
    float mav_mV;
    float mvc_mV;
    float error;
    float delta_error;
    float pw_command_us;
    uint8_t imu_ready;
    uint8_t feature_updated; /* 1 hanya saat feature_update_count EMG berubah */
    uint8_t safety_fault;    /* 1 hanya untuk fault safety-critical */
} FSM_Input;

typedef struct {
    float pw_final_us;
    uint8_t fes_active;
    uint8_t intent_detected;
    uint8_t fatigue_candidate;
    uint8_t fatigue_confirmed;
} FSM_Output;

typedef struct {
    FSM_State state;
    ActiveMode active_mode;
    uint32_t active_start_ms;
    uint32_t rest_start_ms;
    uint32_t fatigue_rest_count;
    FatigueDetector fd;
    uint32_t intent_persist_count;
    uint32_t session_active_count;
    uint32_t session_rest_count;
} FSM_Handle;

void STIM4_FSM_Init(FSM_Handle *fsm);
FSM_State STIM4_FSM_Update(FSM_Handle *fsm, const FSM_Input *in, FSM_Output *out);
void STIM4_FSM_ForceEmergency(FSM_Handle *fsm);
void STIM4_FSM_ResetSession(FSM_Handle *fsm);
FSM_State STIM4_FSM_GetState(const FSM_Handle *fsm);
ActiveMode STIM4_FSM_GetActiveMode(const FSM_Handle *fsm);
uint32_t STIM4_FSM_GetFatigueRestCount(const FSM_Handle *fsm);
uint32_t STIM4_FSM_GetStateElapsedMs(const FSM_Handle *fsm);
uint32_t STIM4_FSM_GetStateDurationMs(const FSM_Handle *fsm);
uint32_t STIM4_FSM_GetStateRemainingMs(const FSM_Handle *fsm);

#endif
