#include "stim4_fsm.h"
#include "hbridge.h"
#include "mcp4725.h"
#include <stddef.h>

static void output_flags_off(FSM_Output *out)
{
    out->pw_final_us = 0.0f;
    out->fes_active = 0U;
}

static void actuator_safe_off(FSM_Output *out)
{
    HBridge_Stop();
    (void)MCP4725_SetCurrent_mA(0.0f);
    output_flags_off(out);
}

static float clamp_pw(float value, ActiveMode mode)
{
    float hi = (mode == ACTIVE_MODE_FATIGUE)
             ? FSM_PW_MAX_FATIGUE_US : FSM_PW_MAX_NORMAL_US;
    if (value < FSM_PW_MIN_US) return FSM_PW_MIN_US;
    if (value > hi) return hi;
    return value;
}

static void enter_idle(FSM_Handle *fsm, FSM_Output *out)
{
    actuator_safe_off(out);
    fsm->state = FSM_IDLE;
    fsm->active_mode = ACTIVE_MODE_NORMAL;
    fsm->active_start_ms = 0U;
    fsm->intent_persist_count = 0U;
    fsm->rest_start_ms = 0U;
    FatigueDetector_Reset(&fsm->fd);
}

static void enter_active(FSM_Handle *fsm, float mav_mV)
{
    fsm->state = FSM_ACTIVE;
    fsm->active_mode = ACTIVE_MODE_NORMAL;
    fsm->active_start_ms = HAL_GetTick();
    /* Hanya diset di sini. NORMAL -> FATIGUE tidak menyentuh timer ini. */
    FatigueDetector_CaptureReference(&fsm->fd, mav_mV);
    fsm->session_active_count++;
}

static void enter_rest(FSM_Handle *fsm, FSM_Output *out, uint8_t fatigue)
{
    actuator_safe_off(out);
    fsm->state = fatigue ? FSM_FATIGUE_REST : FSM_REST;
    fsm->rest_start_ms = HAL_GetTick();
    FatigueDetector_Reset(&fsm->fd);
}

static void enter_therapy_stop(FSM_Handle *fsm, FSM_Output *out)
{
    actuator_safe_off(out);
    fsm->state = FSM_THERAPY_STOP;
    fsm->active_mode = ACTIVE_MODE_NORMAL;
}

static void enter_emergency(FSM_Handle *fsm, FSM_Output *out)
{
    actuator_safe_off(out);
    fsm->state = FSM_EMERGENCY;
    fsm->active_mode = ACTIVE_MODE_NORMAL;
}

void STIM4_FSM_Init(FSM_Handle *fsm)
{
    if (fsm == NULL) return;
    fsm->state = FSM_IDLE;
    fsm->active_mode = ACTIVE_MODE_NORMAL;
    fsm->active_start_ms = 0U;
    fsm->rest_start_ms = 0U;
    fsm->fatigue_rest_count = 0U;
    fsm->intent_persist_count = 0U;
    fsm->session_active_count = 0U;
    fsm->session_rest_count = 0U;
    FatigueDetector_Init(&fsm->fd);
}

FSM_State STIM4_FSM_Update(FSM_Handle *fsm, const FSM_Input *in, FSM_Output *out)
{
    uint32_t elapsed;
    uint8_t intent;

    if ((fsm == NULL) || (in == NULL) || (out == NULL)) return FSM_EMERGENCY;

    out->pw_final_us = 0.0f;
    out->fes_active = 0U;
    out->intent_detected = 0U;
    out->fatigue_candidate = 0U;
    out->fatigue_confirmed = fsm->fd.detected;

    /* Fatigue tidak pernah masuk ke cabang ini. */
    if (in->safety_fault != 0U) {
        enter_emergency(fsm, out);
        return fsm->state;
    }

    if (fsm->state == FSM_EMERGENCY || fsm->state == FSM_THERAPY_STOP) {
        output_flags_off(out);
        return fsm->state; /* latched sampai RESET/CLEAR */
    }

    switch (fsm->state) {
    case FSM_IDLE:
        output_flags_off(out);
        intent = ((in->mvc_mV > 0.0f) &&
                  (in->mav_mV >= (FSM_INTENT_MVC_RATIO * in->mvc_mV))) ? 1U : 0U;
           if (in->feature_updated != 0U) {
               if ((intent != 0U) && (in->imu_ready != 0U)) {
                   if (fsm->intent_persist_count < FSM_INTENT_PERSIST_WINDOWS)
                       fsm->intent_persist_count++;
               } else {
                   fsm->intent_persist_count = 0U;
               }
           }
           out->intent_detected =
               (fsm->intent_persist_count >= FSM_INTENT_PERSIST_WINDOWS) ? 1U : 0U;
           if (out->intent_detected != 0U) {
               enter_active(fsm, in->mav_mV);
               fsm->intent_persist_count = 0U;
           }

           break;

    case FSM_ACTIVE:
        elapsed = HAL_GetTick() - fsm->active_start_ms;

        /* Update tepat satu kali per feature window EMG (100 ms pada emg_app). */
        if ((fsm->active_mode == ACTIVE_MODE_NORMAL) && (in->feature_updated != 0U)) {
            FatigueDetector_Update(&fsm->fd, in->mav_mV, in->error, in->delta_error);
            out->fatigue_candidate = ((!fsm->fd.detected) &&
                                      (fsm->fd.persist_count > 0U)) ? 1U : 0U;
            if (fsm->fd.detected != 0U) {
                fsm->active_mode = ACTIVE_MODE_FATIGUE;
                /* active_start_ms sengaja TIDAK direset. */
            }
        }
        out->fatigue_confirmed = fsm->fd.detected;

        if (elapsed >= FSM_ACTIVE_DURATION_MS) {
            enter_rest(fsm, out,
                       (fsm->active_mode == ACTIVE_MODE_FATIGUE) ? 1U : 0U);
        } else {
            out->fes_active = 1U;
            out->pw_final_us = clamp_pw(in->pw_command_us, fsm->active_mode);
        }
        break;

    case FSM_REST:
        output_flags_off(out);
        elapsed = HAL_GetTick() - fsm->rest_start_ms;
        if (elapsed >= FSM_REST_DURATION_MS) {
            fsm->session_rest_count++;
            enter_idle(fsm, out);
        }
        break;

    case FSM_FATIGUE_REST:
        output_flags_off(out);
        elapsed = HAL_GetTick() - fsm->rest_start_ms;
        if (elapsed >= FSM_FATIGUE_REST_DURATION_MS) {
            fsm->fatigue_rest_count++;
            if (fsm->fatigue_rest_count >= FSM_FATIGUE_REST_STOP_COUNT)
                enter_therapy_stop(fsm, out);
            else
                enter_idle(fsm, out);
        }
        break;

    default:
        enter_emergency(fsm, out); /* corruption/invalid state = critical */
        break;
    }
    return fsm->state;
}

void STIM4_FSM_ForceEmergency(FSM_Handle *fsm)
{
    FSM_Output out = {0};
    if (fsm != NULL) enter_emergency(fsm, &out);
}

void STIM4_FSM_ResetSession(FSM_Handle *fsm)
{
    FSM_Output out = {0};
    if (fsm == NULL) return;
    actuator_safe_off(&out);
    STIM4_FSM_Init(fsm);
}

FSM_State STIM4_FSM_GetState(const FSM_Handle *fsm)
{ return (fsm == NULL) ? FSM_EMERGENCY : fsm->state; }

ActiveMode STIM4_FSM_GetActiveMode(const FSM_Handle *fsm)
{ return (fsm == NULL) ? ACTIVE_MODE_NORMAL : fsm->active_mode; }

uint32_t STIM4_FSM_GetFatigueRestCount(const FSM_Handle *fsm)
{ return (fsm == NULL) ? 0U : fsm->fatigue_rest_count; }

uint32_t STIM4_FSM_GetStateDurationMs(const FSM_Handle *fsm)
{
    if (fsm == NULL) return 0U;
    if (fsm->state == FSM_ACTIVE) return FSM_ACTIVE_DURATION_MS;
    if (fsm->state == FSM_REST) return FSM_REST_DURATION_MS;
    if (fsm->state == FSM_FATIGUE_REST) return FSM_FATIGUE_REST_DURATION_MS;
    return 0U;
}

uint32_t STIM4_FSM_GetStateElapsedMs(const FSM_Handle *fsm)
{
    if (fsm == NULL) return 0U;
    if (fsm->state == FSM_ACTIVE) return HAL_GetTick() - fsm->active_start_ms;
    if (fsm->state == FSM_REST || fsm->state == FSM_FATIGUE_REST)
        return HAL_GetTick() - fsm->rest_start_ms;
    return 0U;
}

uint32_t STIM4_FSM_GetStateRemainingMs(const FSM_Handle *fsm)
{
    uint32_t total = STIM4_FSM_GetStateDurationMs(fsm);
    uint32_t used = STIM4_FSM_GetStateElapsedMs(fsm);
    return (used >= total) ? 0U : total - used;
}
