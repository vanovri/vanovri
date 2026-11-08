#include "emg_app.h"

#include <math.h>
#include <stddef.h>

/*
 * Konfigurasi final subsistem EMG:
 * - STM32F411CEU6
 * - SEN0240 A -> PA0 / ADC1_IN0
 * - ADC dipicu TIM2 TRGO pada 4000 Hz
 * - DMA circular 128 sampel, diproses per 64 sampel
 * - HPF Butterworth orde 2, 20 Hz
 * - LPF Butterworth orde 2, 500 Hz
 * - Notch orde 2, 50 Hz, Q = 30
 * - RMS dan MAV non-overlap 400 sampel / 100 ms
 */

#define EMG_SAMPLE_RATE_HZ             4000U
#define ADC_DMA_BUFFER_SIZE             128U
#define ADC_HALF_BUFFER_SIZE             64U
#define SENSOR_SETTLING_SAMPLES         2000U
#define CALIBRATION_VALID_SAMPLES       8000U
#define CALIBRATION_TIMEOUT_SAMPLES    20000U
#define CALIBRATION_MIN_VALID_PERCENT    90.0f
#define CALIBRATION_MAX_STD_COUNTS      400.0f
#define FEATURE_WINDOW_SAMPLES           400U
#define CLIPPING_WINDOW_SAMPLES         4000U
#define ACQUISITION_STALL_TIMEOUT_MS      250U

#define ADC_REFERENCE_VOLTAGE          3.3f
#define ADC_MAX_COUNTS              4095.0f
#define ADC_TO_VOLT (ADC_REFERENCE_VOLTAGE / ADC_MAX_COUNTS)
/*
 * SEN0240 mempunyai rentang keluaran 0 sampai 3,0 V. Margin 50 mV dari
 * masing-masing ujung dipakai untuk mendeteksi saturasi sensor, bukan hanya
 * saturasi ADC 0 sampai 3,3 V.
 */
#define SENSOR_CLIP_LOW_COUNTS             62U
#define SENSOR_CLIP_HIGH_COUNTS          3661U
#define EXCESSIVE_CLIPPING_PERCENT        5.0f
#define FILTER_ABSOLUTE_LIMIT_VOLT       10.0f

typedef struct
{
    float b0;
    float b1;
    float b2;
    float a1;
    float a2;
    float state1;
    float state2;
} BiquadDF2T;

/*
 * Koefisien menggunakan bentuk denominator:
 * A(z) = 1 + a1*z^-1 + a2*z^-2
 *
 * Implementasi memakai Direct Form II Transposed:
 * y  = b0*x + state1
 * s1 = b1*x - a1*y + state2
 * s2 = b2*x - a2*y
 */
static BiquadDF2T highpass_filter =
{
     0.9780304792f,
    -1.9560609584f,
     0.9780304792f,
    -1.9555782403f,
     0.9565436765f,
     0.0f,
     0.0f
};

static BiquadDF2T lowpass_filter =
{
     0.0976310729f,
     0.1952621459f,
     0.0976310729f,
    -0.9428090416f,
     0.3333333333f,
     0.0f,
     0.0f
};

static BiquadDF2T notch_filter =
{
     0.9986927135f,
    -1.9912281544f,
     0.9986927135f,
    -1.9912281544f,
     0.9973854271f,
     0.0f,
     0.0f
};

static ADC_HandleTypeDef *emg_adc = NULL;
static TIM_HandleTypeDef *emg_timer = NULL;
static uint8_t acquisition_running = 0U;

static volatile uint16_t adc_dma_buffer[ADC_DMA_BUFFER_SIZE];

/* Buffer ini berguna saat debugging atau inspeksi satu blok. */
float emg_raw_buffer[ADC_DMA_BUFFER_SIZE];
float emg_bandpass_buffer[ADC_DMA_BUFFER_SIZE];
float emg_filtered_buffer[ADC_DMA_BUFFER_SIZE];

volatile uint8_t emg_status = EMG_STATUS_BOOT;
volatile uint32_t emg_error_flags = EMG_ERROR_NONE;
volatile uint8_t filter_ready = 0U;
volatile uint8_t recalibration_request = 0U;

volatile uint16_t adc_raw = 0U;
volatile float adc_voltage = 0.0f;
volatile float adc_offset_counts = 0.0f;
volatile uint32_t settling_count = 0U;
volatile uint32_t calibration_count = 0U;
volatile uint32_t calibration_total_count = 0U;
volatile float calibration_valid_percent = 0.0f;
volatile float calibration_std_counts = 0.0f;

volatile uint32_t dma_half_count = 0U;
volatile uint32_t dma_full_count = 0U;
volatile uint32_t adc_error_count = 0U;
volatile uint32_t feature_update_count = 0U;
volatile float clipping_percent_1s = 0.0f;
volatile uint32_t last_dma_callback_tick = 0U;

volatile float emg_raw_latest = 0.0f;
volatile float emg_bandpass_latest = 0.0f;
volatile float emg_filtered_latest = 0.0f;

volatile float raw_rms_100ms = 0.0f;
volatile float bandpass_rms_100ms = 0.0f;
volatile float filtered_rms_100ms = 0.0f;
volatile float raw_mav_100ms = 0.0f;
volatile float bandpass_mav_100ms = 0.0f;
volatile float filtered_mav_100ms = 0.0f;
volatile float filtered_rms_mV = 0.0f;
volatile float filtered_mav_mV = 0.0f;

static float calibration_mean_counts = 0.0f;
static float calibration_m2_counts = 0.0f;

static float raw_square_sum = 0.0f;
static float bandpass_square_sum = 0.0f;
static float filtered_square_sum = 0.0f;
static float raw_absolute_sum = 0.0f;
static float bandpass_absolute_sum = 0.0f;
static float filtered_absolute_sum = 0.0f;
static uint32_t feature_sample_count = 0U;

static uint32_t clipping_sample_count = 0U;
static uint32_t clipping_processed_count = 0U;

static float Biquad_Process(BiquadDF2T *filter, float input)
{
    float output = (filter->b0 * input) + filter->state1;

    filter->state1 =
        (filter->b1 * input) - (filter->a1 * output) + filter->state2;
    filter->state2 =
        (filter->b2 * input) - (filter->a2 * output);

    return output;
}

static void Biquad_Reset(BiquadDF2T *filter)
{
    filter->state1 = 0.0f;
    filter->state2 = 0.0f;
}

static void Reset_Feature_State(void)
{
    raw_square_sum = 0.0f;
    bandpass_square_sum = 0.0f;
    filtered_square_sum = 0.0f;
    raw_absolute_sum = 0.0f;
    bandpass_absolute_sum = 0.0f;
    filtered_absolute_sum = 0.0f;
    feature_sample_count = 0U;

    raw_rms_100ms = 0.0f;
    bandpass_rms_100ms = 0.0f;
    filtered_rms_100ms = 0.0f;
    raw_mav_100ms = 0.0f;
    bandpass_mav_100ms = 0.0f;
    filtered_mav_100ms = 0.0f;
    filtered_rms_mV = 0.0f;
    filtered_mav_mV = 0.0f;
}

static void Clear_Live_Signal_Outputs(void)
{
    Reset_Feature_State();
    emg_raw_latest = 0.0f;
    emg_bandpass_latest = 0.0f;
    emg_filtered_latest = 0.0f;
}

static void Reset_Signal_State(void)
{
    Biquad_Reset(&highpass_filter);
    Biquad_Reset(&lowpass_filter);
    Biquad_Reset(&notch_filter);

    adc_raw = 0U;
    adc_voltage = 0.0f;
    adc_offset_counts = 0.0f;
    settling_count = 0U;
    calibration_mean_counts = 0.0f;
    calibration_m2_counts = 0.0f;
    calibration_count = 0U;
    calibration_total_count = 0U;
    calibration_valid_percent = 0.0f;
    calibration_std_counts = 0.0f;
    filter_ready = 0U;

    clipping_sample_count = 0U;
    clipping_processed_count = 0U;
    clipping_percent_1s = 0.0f;

    Clear_Live_Signal_Outputs();

    for (uint32_t i = 0U; i < ADC_DMA_BUFFER_SIZE; ++i)
    {
        emg_raw_buffer[i] = 0.0f;
        emg_bandpass_buffer[i] = 0.0f;
        emg_filtered_buffer[i] = 0.0f;
    }

    emg_status = EMG_STATUS_SENSOR_SETTLING;
}

static void Enter_Numeric_Fault(void)
{
    emg_error_flags |= EMG_ERROR_FILTER_NUMERIC;
    emg_status = EMG_STATUS_NUMERIC_FAULT;
    filter_ready = 0U;

    Biquad_Reset(&highpass_filter);
    Biquad_Reset(&lowpass_filter);
    Biquad_Reset(&notch_filter);
    Clear_Live_Signal_Outputs();
}

static void Enter_ADC_Fault(uint32_t error_flag)
{
    emg_error_flags |= error_flag;
    emg_status = EMG_STATUS_ADC_FAULT;
    filter_ready = 0U;
    Clear_Live_Signal_Outputs();
}

static void Stop_Acquisition_Transport(void)
{
    if (emg_timer != NULL)
    {
        (void)HAL_TIM_Base_Stop(emg_timer);
    }

    if (emg_adc != NULL)
    {
        (void)HAL_ADC_Stop_DMA(emg_adc);
    }

    acquisition_running = 0U;
}

static HAL_StatusTypeDef Start_Acquisition_Transport(void)
{
    last_dma_callback_tick = HAL_GetTick();

    if (HAL_ADC_Start_DMA(emg_adc,
                          (uint32_t *)adc_dma_buffer,
                          ADC_DMA_BUFFER_SIZE) != HAL_OK)
    {
        Enter_ADC_Fault(EMG_ERROR_ADC_DMA_START);
        return HAL_ERROR;
    }

    /*
     * ADC+DMA dijalankan lebih dahulu. TIM2 baru dinyalakan setelah DMA siap,
     * sehingga trigger pertama tidak kehilangan tempat penyimpanan.
     */
    if (HAL_TIM_Base_Start(emg_timer) != HAL_OK)
    {
        (void)HAL_ADC_Stop_DMA(emg_adc);
        Enter_ADC_Fault(EMG_ERROR_TIMER_START);
        return HAL_ERROR;
    }

    acquisition_running = 1U;
    return HAL_OK;
}

static void Update_Features(float raw_value,
                            float bandpass_value,
                            float filtered_value)
{
    raw_square_sum += raw_value * raw_value;
    bandpass_square_sum += bandpass_value * bandpass_value;
    filtered_square_sum += filtered_value * filtered_value;

    raw_absolute_sum += fabsf(raw_value);
    bandpass_absolute_sum += fabsf(bandpass_value);
    filtered_absolute_sum += fabsf(filtered_value);

    feature_sample_count++;

    if (feature_sample_count >= FEATURE_WINDOW_SAMPLES)
    {
        const float divisor = (float)feature_sample_count;

        const float next_raw_rms = sqrtf(raw_square_sum / divisor);
        const float next_bandpass_rms =
            sqrtf(bandpass_square_sum / divisor);
        const float next_filtered_rms =
            sqrtf(filtered_square_sum / divisor);

        const float next_raw_mav = raw_absolute_sum / divisor;
        const float next_bandpass_mav =
            bandpass_absolute_sum / divisor;
        const float next_filtered_mav =
            filtered_absolute_sum / divisor;

        if ((!isfinite(next_raw_rms)) ||
            (!isfinite(next_bandpass_rms)) ||
            (!isfinite(next_filtered_rms)) ||
            (!isfinite(next_raw_mav)) ||
            (!isfinite(next_bandpass_mav)) ||
            (!isfinite(next_filtered_mav)))
        {
            Enter_Numeric_Fault();
            return;
        }

        raw_rms_100ms = next_raw_rms;
        bandpass_rms_100ms = next_bandpass_rms;
        filtered_rms_100ms = next_filtered_rms;
        raw_mav_100ms = next_raw_mav;
        bandpass_mav_100ms = next_bandpass_mav;
        filtered_mav_100ms = next_filtered_mav;

        filtered_rms_mV = next_filtered_rms * 1000.0f;
        filtered_mav_mV = next_filtered_mav * 1000.0f;

        raw_square_sum = 0.0f;
        bandpass_square_sum = 0.0f;
        filtered_square_sum = 0.0f;
        raw_absolute_sum = 0.0f;
        bandpass_absolute_sum = 0.0f;
        filtered_absolute_sum = 0.0f;
        feature_sample_count = 0U;
        feature_update_count++;
    }
}

static void Process_ADC_Block(uint32_t start_index, uint32_t length)
{
    const uint32_t end_index = start_index + length;

    for (uint32_t i = start_index; i < end_index; ++i)
    {
        const uint16_t sample = adc_dma_buffer[i];

        adc_raw = sample;
        adc_voltage = (float)sample * ADC_TO_VOLT;

        if (emg_status == EMG_STATUS_SENSOR_SETTLING)
        {
            settling_count++;
            emg_raw_buffer[i] = 0.0f;
            emg_bandpass_buffer[i] = 0.0f;
            emg_filtered_buffer[i] = 0.0f;

            if (settling_count >= SENSOR_SETTLING_SAMPLES)
            {
                calibration_mean_counts = 0.0f;
                calibration_m2_counts = 0.0f;
                calibration_count = 0U;
                calibration_total_count = 0U;
                calibration_valid_percent = 0.0f;
                calibration_std_counts = 0.0f;
                emg_status = EMG_STATUS_CALIBRATING;
            }

            continue;
        }

        if (emg_status == EMG_STATUS_CALIBRATING)
        {
            calibration_total_count++;

            if ((sample > SENSOR_CLIP_LOW_COUNTS) &&
                (sample < SENSOR_CLIP_HIGH_COUNTS))
            {
                calibration_count++;

                const float sample_counts = (float)sample;
                const float delta =
                    sample_counts - calibration_mean_counts;
                calibration_mean_counts +=
                    delta / (float)calibration_count;
                const float delta_after_mean =
                    sample_counts - calibration_mean_counts;
                calibration_m2_counts +=
                    delta * delta_after_mean;
            }

            calibration_valid_percent =
                ((float)calibration_count /
                 (float)calibration_total_count) * 100.0f;

            if (calibration_count > 1U)
            {
                calibration_std_counts =
                    sqrtf(calibration_m2_counts /
                          (float)calibration_count);
            }

            emg_raw_buffer[i] = 0.0f;
            emg_bandpass_buffer[i] = 0.0f;
            emg_filtered_buffer[i] = 0.0f;

            if ((calibration_count >= CALIBRATION_VALID_SAMPLES) &&
                (calibration_valid_percent >=
                 CALIBRATION_MIN_VALID_PERCENT) &&
                (calibration_std_counts <=
                 CALIBRATION_MAX_STD_COUNTS))
            {
                adc_offset_counts = calibration_mean_counts;

                Biquad_Reset(&highpass_filter);
                Biquad_Reset(&lowpass_filter);
                Biquad_Reset(&notch_filter);
                Reset_Feature_State();

                filter_ready = 1U;
                emg_status = EMG_STATUS_READY;
            }
            else if (calibration_total_count >=
                     CALIBRATION_TIMEOUT_SAMPLES)
            {
                if (calibration_count < CALIBRATION_VALID_SAMPLES)
                {
                    emg_error_flags |=
                        EMG_ERROR_CALIBRATION_TIMEOUT;
                }
                else
                {
                    emg_error_flags |=
                        EMG_ERROR_CALIBRATION_QUALITY;
                }

                emg_status = EMG_STATUS_CALIBRATION_FAULT;
                filter_ready = 0U;
                Clear_Live_Signal_Outputs();
            }

            continue;
        }

        if (emg_status != EMG_STATUS_READY)
        {
            emg_raw_buffer[i] = 0.0f;
            emg_bandpass_buffer[i] = 0.0f;
            emg_filtered_buffer[i] = 0.0f;
            continue;
        }

        if ((sample <= SENSOR_CLIP_LOW_COUNTS) ||
            (sample >= SENSOR_CLIP_HIGH_COUNTS))
        {
            clipping_sample_count++;
        }

        clipping_processed_count++;

        if (clipping_processed_count >= CLIPPING_WINDOW_SAMPLES)
        {
            clipping_percent_1s =
                ((float)clipping_sample_count /
                 (float)clipping_processed_count) * 100.0f;

            if (clipping_percent_1s >=
                EXCESSIVE_CLIPPING_PERCENT)
            {
                emg_error_flags |=
                    EMG_ERROR_EXCESSIVE_CLIPPING;
            }
            else
            {
                emg_error_flags &=
                    ~EMG_ERROR_EXCESSIVE_CLIPPING;
            }

            clipping_sample_count = 0U;
            clipping_processed_count = 0U;
        }

        const float raw_centered =
            ((float)sample - adc_offset_counts) * ADC_TO_VOLT;

        const float highpass_output =
            Biquad_Process(&highpass_filter, raw_centered);
        const float bandpass_output =
            Biquad_Process(&lowpass_filter, highpass_output);
        const float filtered_output =
            Biquad_Process(&notch_filter, bandpass_output);

        if ((!isfinite(raw_centered)) ||
            (!isfinite(bandpass_output)) ||
            (!isfinite(filtered_output)) ||
            (fabsf(filtered_output) > FILTER_ABSOLUTE_LIMIT_VOLT))
        {
            Enter_Numeric_Fault();
            return;
        }

        emg_raw_buffer[i] = raw_centered;
        emg_bandpass_buffer[i] = bandpass_output;
        emg_filtered_buffer[i] = filtered_output;

        emg_raw_latest = raw_centered;
        emg_bandpass_latest = bandpass_output;
        emg_filtered_latest = filtered_output;

        Update_Features(raw_centered,
                        bandpass_output,
                        filtered_output);

        if (emg_status != EMG_STATUS_READY)
        {
            return;
        }
    }
}

HAL_StatusTypeDef EMG_AppStart(ADC_HandleTypeDef *hadc,
                               TIM_HandleTypeDef *htim)
{
    if ((hadc == NULL) || (htim == NULL))
    {
        return HAL_ERROR;
    }

    emg_adc = hadc;
    emg_timer = htim;
    acquisition_running = 0U;
    emg_error_flags = EMG_ERROR_NONE;
    dma_half_count = 0U;
    dma_full_count = 0U;
    adc_error_count = 0U;
    feature_update_count = 0U;
    recalibration_request = 0U;

    Reset_Signal_State();

    return Start_Acquisition_Transport();
}

void EMG_AppProcess(void)
{
    if ((emg_status == EMG_STATUS_ADC_FAULT) &&
        (acquisition_running != 0U))
    {
        Stop_Acquisition_Transport();
    }

    if (acquisition_running != 0U)
    {
        const uint32_t now = HAL_GetTick();

        if ((now - last_dma_callback_tick) >
            ACQUISITION_STALL_TIMEOUT_MS)
        {
            Stop_Acquisition_Transport();
            Enter_ADC_Fault(EMG_ERROR_ACQUISITION_STALL);
        }
    }

    if (recalibration_request != 0U)
    {
        /*
         * Restart transport membuat kalibrasi ulang juga dapat memulihkan
         * ADC/DMA yang sebelumnya fault atau stall.
         */
        Stop_Acquisition_Transport();

        const uint32_t previous_primask = __get_PRIMASK();
        __disable_irq();
        recalibration_request = 0U;
        emg_error_flags = EMG_ERROR_NONE;
        Reset_Signal_State();

        if (previous_primask == 0U)
        {
            __enable_irq();
        }

        (void)Start_Acquisition_Transport();
    }
}

void EMG_RequestRecalibration(void)
{
    recalibration_request = 1U;
}

void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc)
{
    if ((emg_adc != NULL) && (hadc == emg_adc))
    {
        last_dma_callback_tick = HAL_GetTick();
        Process_ADC_Block(0U, ADC_HALF_BUFFER_SIZE);
        dma_half_count++;
    }
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if ((emg_adc != NULL) && (hadc == emg_adc))
    {
        last_dma_callback_tick = HAL_GetTick();
        Process_ADC_Block(ADC_HALF_BUFFER_SIZE,
                          ADC_HALF_BUFFER_SIZE);
        dma_full_count++;
    }
}

void HAL_ADC_ErrorCallback(ADC_HandleTypeDef *hadc)
{
    if ((emg_adc != NULL) && (hadc == emg_adc))
    {
        adc_error_count++;
        Enter_ADC_Fault(EMG_ERROR_ADC_RUNTIME);
    }
}
