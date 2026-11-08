#include "fatigue_detector.h"
#include <math.h>
#include <stddef.h>
void FatigueDetector_Init(FatigueDetector *fd)
{
    if (fd == NULL) return;
    fd->threshold = FATIGUE_THRESHOLD;
    fd->persist_windows = FATIGUE_PERSIST_WINDOWS;
    FatigueDetector_Reset(fd);
}
void FatigueDetector_CaptureReference(FatigueDetector *fd, float mav_current)
{
    if (fd == NULL) return;
    fd->mav_reference = (mav_current > 1.0f) ? mav_current : 1.0f;
    fd->mav_ratio = 1.0f;
    fd->persist_count = 0U;
    fd->detected = 0U;
    fd->reference_set = 1U;
}
void FatigueDetector_Update(FatigueDetector *fd, float mav_current, float error, float delta_error)
{
    uint8_t condition;
    if (fd == NULL || fd->reference_set == 0U || fd->detected != 0U) return;
    fd->mav_ratio = mav_current / fd->mav_reference;
    condition = ((fd->mav_ratio < fd->threshold) &&
                 (fabsf(error) > FATIGUE_ERROR_MIN_DEG) &&
                 (fabsf(delta_error) < FATIGUE_DELTA_ERROR_MAX_DEG)) ? 1U : 0U;
    if (condition != 0U) {
        if (fd->persist_count < fd->persist_windows) fd->persist_count++;
        if (fd->persist_count >= fd->persist_windows) fd->detected = 1U;
    } else {
        fd->persist_count = 0U; /* wajib berturut-turut */
    }
}
void FatigueDetector_Reset(FatigueDetector *fd)
{
    if (fd == NULL) return;
    fd->mav_reference = 0.0f;
    fd->mav_ratio = 1.0f;
    fd->persist_count = 0U;
    fd->detected = 0U;
    fd->reference_set = 0U;
}
