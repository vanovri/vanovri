#ifndef EMG_APP_H
#define EMG_APP_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

typedef enum {
    EMG_STATUS_BOOT              = 0,
    EMG_STATUS_SENSOR_SETTLING   = 1,
    EMG_STATUS_CALIBRATING       = 2,
    EMG_STATUS_READY             = 3,
    EMG_STATUS_CALIBRATION_FAULT = 4,
    EMG_STATUS_ADC_FAULT         = 5,
    EMG_STATUS_NUMERIC_FAULT     = 6
} EMG_Status;

enum {
    EMG_ERROR_NONE                = 0U,
    EMG_ERROR_ADC_DMA_START       = (1UL << 0),
    EMG_ERROR_TIMER_START         = (1UL << 1),
    EMG_ERROR_CALIBRATION_TIMEOUT = (1UL << 2),
    EMG_ERROR_ADC_RUNTIME         = (1UL << 3),
    EMG_ERROR_FILTER_NUMERIC      = (1UL << 4),
    EMG_ERROR_ACQUISITION_STALL   = (1UL << 5),
    EMG_ERROR_EXCESSIVE_CLIPPING  = (1UL << 6),
    EMG_ERROR_CALIBRATION_QUALITY = (1UL << 7)
};

extern volatile uint8_t  emg_status;
extern volatile uint32_t emg_error_flags;
extern volatile uint8_t  filter_ready;
extern volatile uint8_t  recalibration_request;

extern volatile uint16_t adc_raw;
extern volatile float    adc_voltage;
extern volatile float    adc_offset_counts;
extern volatile uint32_t settling_count;
extern volatile uint32_t calibration_count;
extern volatile uint32_t calibration_total_count;
extern volatile float    calibration_valid_percent;
extern volatile float    calibration_std_counts;

extern volatile uint32_t dma_half_count;
extern volatile uint32_t dma_full_count;
extern volatile uint32_t adc_error_count;
extern volatile uint32_t feature_update_count;
extern volatile float    clipping_percent_1s;
extern volatile uint32_t last_dma_callback_tick;

extern volatile float emg_raw_latest;
extern volatile float emg_bandpass_latest;
extern volatile float emg_filtered_latest;

extern volatile float raw_rms_100ms;
extern volatile float bandpass_rms_100ms;
extern volatile float filtered_rms_100ms;
extern volatile float raw_mav_100ms;
extern volatile float bandpass_mav_100ms;
extern volatile float filtered_mav_100ms;

extern volatile float filtered_rms_mV;
extern volatile float filtered_mav_mV;

HAL_StatusTypeDef EMG_AppStart(ADC_HandleTypeDef *hadc, TIM_HandleTypeDef *htim);
void EMG_AppProcess(void);
void EMG_RequestRecalibration(void);

#ifdef __cplusplus
}
#endif

#endif /* EMG_APP_H */
