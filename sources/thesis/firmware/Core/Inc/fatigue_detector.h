#ifndef FATIGUE_DETECTOR_H
#define FATIGUE_DETECTOR_H
#include <stdint.h>
/* Engineering parameters; wajib divalidasi, bukan standar fisiologis universal. */
#define FATIGUE_THRESHOLD                 0.70f
#define FATIGUE_PERSIST_WINDOWS           3U
#define FATIGUE_ERROR_MIN_DEG             5.0f
#define FATIGUE_DELTA_ERROR_MAX_DEG       0.5f
typedef struct {
    float mav_reference;
    float mav_ratio;
    uint32_t persist_count;
    uint8_t detected;
    uint8_t reference_set;
    float threshold;
    uint32_t persist_windows;
} FatigueDetector;
void FatigueDetector_Init(FatigueDetector *fd);
void FatigueDetector_CaptureReference(FatigueDetector *fd, float mav_current);
void FatigueDetector_Update(FatigueDetector *fd, float mav_current, float error, float delta_error);
void FatigueDetector_Reset(FatigueDetector *fd);
#endif
