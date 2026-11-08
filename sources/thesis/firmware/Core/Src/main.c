/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    main.c
  * @brief   STIM4 — Integrated Firmware v3 (SYSTEM ORCHESTRATOR)
  *
  *  Peran main.c : orchestrator / system controller.
  *  main.c TIDAK mengimplementasikan ulang EMG, IMU, fuzzy, atau FSM terapi.
  *
  *  Timer : TIM2 = ADC TRGO 4 kHz (emg_app) | TIM3 = H-Bridge 1 MHz
  *  Pin   : PA0 = EMG ADC | PA4 = HB PHASE_A | PA5 = HB PHASE_B | PB8/PB9 = I2C1 | PC13 = EMERGENCY
  *  Mode  : MODE_MANUAL (parameter fixed operator) | MODE_AUTO (stim4_fsm + fuzzy)
  *  Loop  : non-blocking, tanpa HAL_Delay
  *
  *  Alur  : BOOT -> IMU+EMG ON -> STATUS -> CAL IMU -> CAL MVC 3s -> MODE ->
  *          PARAM -> FES SWITCH -> READY -> START -> THERAPY -> COMPLETE/EMERGENCY
  ******************************************************************************
  */
/* USER CODE END Header */

#include "main.h"

/* USER CODE BEGIN Includes */
#include "stim4_config.h"
#include "fuzzy_pw.h"
#include "mcp4725.h"
#include "hbridge.h"
#include "lsm6ds3.h"
#include "emg_app.h"
#include "stim4_fsm.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
/* USER CODE END Includes */

/* USER CODE BEGIN PTD */
typedef enum {
    STIM4_MODE_NONE   = 0U,
    STIM4_MODE_MANUAL = 1U,
    STIM4_MODE_AUTO   = 2U
} STIM4_Mode;

typedef enum {
    SYSTEM_INIT = 0U,
    SYSTEM_WAIT_READY,
    SYSTEM_CALIBRATION,
    SYSTEM_CONFIG,
    SYSTEM_READY_TO_START,
    SYSTEM_THERAPY,
    SYSTEM_COMPLETED,
    SYSTEM_EMERGENCY
} System_State;

typedef enum {
    CAL_IDLE = 0U,
    CAL_IMU_RUN,
    CAL_IMU_SETTLE,
    CAL_MVC_RUN,
    CAL_DONE,
    CAL_FAIL
} Cal_State;

typedef enum {
    MANUAL_PHASE_ACTIVE = 0U,
    MANUAL_PHASE_REST   = 1U
} Manual_Phase;
/* USER CODE END PTD */

/* USER CODE BEGIN PD */
/* ---------------- Kalibrasi ---------------- */
#define IMU_CAL_DURATION_MS         200U    /* 20 x TS_MS — sama seperti versi lama   */
#define IMU_CAL_SETTLE_MS           500U    /* settling complementary filter          */
#define MVC_CAL_DURATION_MS        3000U    /* SPEC 6 : 3 detik (dulu 5000)           */
#define MVC_MIN_VALID_MV              1.0f  /* dipertahankan dari versi lama          */

/* ---------------- Retry init sensor (pengganti Error_Handler) ---------------- */
#define SENSOR_RETRY_INTERVAL_MS    500U
#define SENSOR_READ_FAIL_LIMIT        5U

/* ---------------- Safety net PW (SPEC 12 : maksimum normal 400 us) -----------
 * Ini HANYA jaring pengaman di sisi orchestrator.
 * Cap fatigue 320 us tetap tanggung jawab stim4_fsm.
 */
#define STIM4_ENFORCE_PW_NORMAL_CAP  1
#define STIM4_PW_NORMAL_CAP_US     400.0f

/* ---------------- Emergency latch --------------------------------------------
 * 0 = latched sampai MCU reset (sesuai SPEC 20)
 * 1 = boleh direset lewat command GUI eksplisit (tetap bukan otomatis)
 */
#define STIM4_ALLOW_EMERGENCY_RESET   1

/* ---------------- TEMPORARY BENCH / DRY-RUN MODE -----------------------------
 * 1 = MCP4725 boleh absen untuk menguji GUI, FSM, controller, dan session flow.
 *     Seluruh keluaran fisik H-Bridge tetap dipaksa OFF, walaupun MCP terpasang.
 * 0 = mode normal/produksi. MCP4725 wajib terdeteksi dan safety tidak berubah.
 * JANGAN gunakan nilai 1 untuk terapi manusia.
 */
#ifndef MCP_BYPASS_TEST
#define MCP_BYPASS_TEST              1U
#endif

#if ((MCP_BYPASS_TEST != 0U) && (MCP_BYPASS_TEST != 1U))
#error "MCP_BYPASS_TEST must be 0U or 1U"
#endif

/* ---------------- Status tambahan dari stim4_fsm ------------------------------
 * 0 = FSM_Output belum punya field status tambahan.
 * Set 1 setelah menambahkan active_submode / fatigue_detected /
 * fatigue_rest_count / mav_ratio ke FSM_Output.
 */
#define STIM4_FSM_HAS_STATUS_API      0
/* ---------------- AUTO : fuzzy PW incremental (v4) ---------------- */

#define AUTO_CURRENT_EMG_MOD       0      /* 1 = arus dimodulasi level EMG (perilaku v2/v3)  */
#define PW_RESET_EACH_BURST       0      /* 1 = tiap burst ACTIVE mulai lagi dari initial   */
#define PW_BACKCALC_FROM_FSM      0      /* 1 = integrator disinkronkan ke out.pw_final_us */

/* ---------------- Kode diagnostik ---------------- */
#define CAL_FAULT_NONE               0U
#define CAL_FAULT_IMU_NOT_READY      1U
#define CAL_FAULT_EMG_NOT_READY      2U
#define CAL_FAULT_MVC_TOO_LOW        3U
#define CAL_FAULT_IMU_FIRST          4U
#define CAL_FAULT_BUSY               5U
#define CAL_FAULT_THERAPY_RUNNING    6U

#define START_OK                     0U
#define START_BLOCK_EMERGENCY        1U
#define START_BLOCK_NO_MODE          2U
#define START_BLOCK_NO_PARAMS        3U
#define START_BLOCK_FES_OFF          4U
#define START_BLOCK_NEED_CAL         5U
#define START_BLOCK_SENSOR           6U
#define START_BLOCK_BUSY             7U


#define EMERGENCY_SRC_NONE           0U
#define EMERGENCY_SRC_FSM            2U
#define EMERGENCY_SRC_GUI            3U

/* ---------------- UART GUI protocol ----------------------------------------- */
#define GUI_RX_LINE_MAX              256U
#define GUI_RX_QUEUE_LEN              10U
#define GUI_TX_BUFFER_MAX           2048U
#define GUI_TELEMETRY_PERIOD_MS      100U
#define GUI_HEARTBEAT_TIMEOUT_MS    1200U
/* USER CODE END PD */

/* USER CODE BEGIN PM */
/* USER CODE END PM */

ADC_HandleTypeDef  hadc1;
DMA_HandleTypeDef  hdma_adc1;
I2C_HandleTypeDef  hi2c1;
TIM_HandleTypeDef  htim2;
TIM_HandleTypeDef  htim3;
UART_HandleTypeDef huart1;

/* USER CODE BEGIN PV */
/* ============================================================
 * SENSOR & SUBSISTEM
 * ============================================================ */
LSM6DS3_Handle g_imu_a = { .i2c_addr = LSM6DS3_ADDR_A };
LSM6DS3_Handle g_imu_b = { .i2c_addr = LSM6DS3_ADDR_B };
FSM_Handle     g_fsm;

/* ============================================================
 * STATUS KOMPONEN (SPEC 4 & 23) — dibaca GUI / Live Expression
 * ============================================================ */
volatile uint8_t g_imu_a_ready       = 0U;
volatile uint8_t g_imu_b_ready       = 0U;
volatile uint8_t g_emg_ready         = 0U;
volatile uint8_t g_mcp_ready         = 0U;
volatile uint8_t g_fes_ready         = 0U;
volatile uint8_t g_system_ready      = 0U;

volatile uint8_t g_imu_calibrated    = 0U;
volatile uint8_t g_mvc_calibrated    = 0U;
volatile uint8_t g_params_configured = 0U;
volatile uint8_t g_therapy_running   = 0U;
volatile uint8_t g_therapy_completed = 0U;
volatile uint8_t g_emergency         = 0U;
volatile uint8_t g_emergency_source  = EMERGENCY_SRC_NONE;

volatile uint8_t g_system_state      = (uint8_t)SYSTEM_INIT;
volatile uint8_t g_cal_state         = (uint8_t)CAL_IDLE;
volatile uint8_t g_cal_fault         = CAL_FAULT_NONE;
volatile uint8_t g_start_block       = START_BLOCK_NO_MODE;
volatile uint8_t g_current_fsm_state = 0U;
volatile uint8_t g_active_mode       = 0U;  /* 0=n/a 1=ACTIVE_NORMAL 2=ACTIVE_FATIGUE */
volatile uint8_t g_manual_phase      = 0U;  /* 0=ACTIVE 1=REST */

/* ============================================================
 * COMMAND DARI GUI (SPEC 22)
 * Diisi dari parser UART GUI atau tetap dapat diubah lewat Live Expression.
 * ============================================================ */
volatile uint8_t g_cmd_calibrate_imu   = 0U;
volatile uint8_t g_cmd_calibrate_mvc   = 0U;
volatile uint8_t g_cmd_apply_params    = 0U;
volatile uint8_t g_cmd_fes_switch_on   = 1U;
volatile uint8_t g_cmd_start_therapy   = 0U;
volatile uint8_t g_cmd_stop_therapy    = 0U;
volatile uint8_t g_cmd_recalibrate_emg = 0U;
volatile uint8_t g_cmd_reset_emergency = 0U;

volatile uint8_t g_selected_mode       = (uint8_t)STIM4_MODE_NONE;

/* MANUAL boleh start tanpa kalibrasi (simulasi). AUTO tetap wajib kalibrasi. */
volatile uint8_t g_bypass_calibration  = 1U;

/* ============================================================
 * PARAMETER MODE MANUAL (SPEC 8)
 * Default = paling aman: PW & frekuensi minimum, arus 0 mA.
 * ============================================================ */
volatile float    g_manual_pw_us             = PW_MIN_US;
volatile float    g_manual_current_mA         = I_MIN_MA;
volatile float    g_manual_frequency_Hz       = FREQ_MIN_HZ;
volatile uint32_t g_manual_active_duration_ms = 10000U;
volatile uint32_t g_manual_rest_duration_ms   = 10000U;
volatile uint32_t g_manual_cycle_count        = 0U;

/* ============================================================
 * PARAMETER MODE AUTO (SPEC 22)
 * 35.0f = nilai target sudut yang dipakai firmware v2.
 * ============================================================ */
volatile float g_auto_target_angle = 35.0f;
/* ---- Parameter awal mode AUTO (di-set SEBELUM start) ---- */
/* ---- Parameter awal mode AUTO (di-set SEBELUM start) ---- */
volatile float g_auto_init_pw_us     = PW_INIT_DEFAULT_US;    /* 250 us */
volatile float g_auto_init_current_mA = I_INIT_DEFAULT_MA;      /*  10 mA */
volatile float g_auto_init_freq_Hz    = FREQ_INIT_DEFAULT_HZ;   /*  35 Hz */

/* ---- Tuning fuzzy incremental (boleh diubah live) ---- */
volatile float g_pw_incr_gain  = PW_INCR_GAIN_DEFAULT;   /* K  [us/unit/tick] */
volatile float g_fuzzy_de_gain  = FUZZY_DE_GAIN_DEFAULT;   /* skala Δe -> ±4    */
volatile float g_de_lpf_alpha = DE_LPF_ALPHA_DEFAULT;   /* 0.01 .. 1.0 */
/* ---- Monitoring ---- */
volatile float g_pw_delta_us   = 0.0f;   /* Δ fuzzy per tick   */
volatile float g_pw_cmd_us     = 0.0f;   /* output integrator  */

/* ---- Internal ---- */
static   float s_de_filt        = 0.0f;   /* Δe ter-low-pass    */
/* ============================================================
 * SINYAL & KONTROL — monitoring GUI (SPEC 23)
 * ============================================================ */
volatile float g_joint_angle   = 0.0f;
volatile float g_imu_a_angle   = 0.0f;
volatile float g_imu_b_angle   = 0.0f;
volatile float g_zero_offset   = 0.0f;
volatile float g_target_angle  = 0.0f;
volatile float g_error         = 0.0f;
volatile float g_delta_error   = 0.0f;

volatile float g_mav           = 0.0f;
volatile float g_rms           = 0.0f;
volatile float g_mvc           = 0.0f;
volatile float g_mav_ratio     = 0.0f;   /* monitor; referensi resmi ada di FSM */
volatile float g_emg_level     = 0.0f;
volatile uint8_t g_emg_intent  = 0U;

volatile float g_pw_fuzzy     = 0.0f;
volatile float g_pw_final     = 0.0f;
volatile float g_current       = 0.0f;
volatile float g_frequency     = 0.0f;

volatile uint8_t g_fatigue_detected   = 0U;
volatile uint8_t g_fatigue_rest_count = 0U;

/* ============================================================
 * DIAGNOSTIK
 * ============================================================ */
volatile uint32_t g_dac_error_count      = 0U;
volatile uint32_t g_imu_a_fail_count     = 0U;
volatile uint32_t g_imu_b_fail_count     = 0U;
volatile uint32_t g_loop_max_interval_ms = 0U;  /* bukti loop non-blocking */
volatile uint32_t g_emg_start_status     = 0U;  /* 0 = HAL_OK */

/* ============================================================
 * STATE INTERNAL (bukan untuk GUI)
 * ============================================================ */
static System_State s_system            = SYSTEM_INIT;
static Cal_State    s_cal               = CAL_IDLE;
static Manual_Phase s_manual_phase      = MANUAL_PHASE_ACTIVE;

static float    s_prev_error            = 0.0f;
static float    s_mvc_peak              = 0.0f;
static float    s_mvc_mV                = 1.0f;
static float    s_mav_ref               = 0.0f;

static uint32_t s_cal_start_ms          = 0U;
static uint32_t s_manual_phase_start_ms = 0U;
static uint32_t s_ctrl_tick_ms          = 0U;
static uint32_t s_retry_tick_ms         = 0U;
static uint32_t s_loop_tick_ms          = 0U;

static uint8_t  s_hb_running            = 0U;
static float    s_last_pw_us            = -1.0f;
static float    s_last_freq_hz          = -1.0f;
static float    s_last_current_mA       = -1.0f;
static uint8_t  s_fes_was_active        = 0U;
static uint8_t  s_last_mode             = (uint8_t)STIM4_MODE_NONE;
static uint8_t  s_imu_a_fail            = 0U;
static uint8_t  s_imu_b_fail            = 0U;

/* UART GUI: RX interrupt per-byte -> ring queue baris; TX telemetry non-blocking. */
static uint8_t            s_gui_rx_byte = 0U;
static char               s_gui_rx_build[GUI_RX_LINE_MAX];
static volatile uint16_t  s_gui_rx_build_len = 0U;
static char               s_gui_rx_queue[GUI_RX_QUEUE_LEN][GUI_RX_LINE_MAX];
static volatile uint8_t   s_gui_rx_head = 0U;
static volatile uint8_t   s_gui_rx_tail = 0U;
static volatile uint32_t  g_gui_rx_drop_count = 0U;
static volatile uint8_t   s_gui_tx_busy = 0U;
static char               s_gui_tx_buffer[GUI_TX_BUFFER_MAX];
static uint32_t           s_gui_telemetry_tick_ms = 0U;
static uint32_t           s_gui_last_heartbeat_ms = 0U;
static uint8_t            s_gui_link_seen = 0U;
/* USER CODE END PV */

void        SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_ADC1_Init(void);
static void MX_I2C1_Init(void);
static void MX_TIM2_Init(void);
static void MX_TIM3_Init(void);
static void MX_USART1_UART_Init(void);

/* USER CODE BEGIN PFP */
static float   clampf(float v, float lo, float hi);
static uint8_t Mcp_StartGateOk(void);
static void    Output_SetCurrent(float mA);
static void    Output_Disable(void);
static void    Output_Enable(float pw_us, float freq_hz, float current_mA);
static void    Fsm_ForceEmergency(void);
static void    Emergency_Enter(uint8_t source);
static void    Sensors_Init(void);
static void    Sensors_ReadTask(void);
static void    Sensors_RetryTask(void);
static void    Cal_StartImu(void);
static void    Cal_StartMvc(void);
static void    Calibration_Task(void);
static void    Params_Apply(void);
static uint8_t Therapy_StartBlockReason(void);
static void    Therapy_Start(void);
static void    Therapy_Stop(uint8_t completed);
static void    Therapy_Manual(void);
static void    Therapy_Auto(void);
static void    Therapy_Task(void);
static void    Command_Task(void);
static void    Safety_Task(void);
static void    Status_UpdateReadiness(void);
static void    Status_Publish(void);
static void    GuiSerial_Start(void);
static void    GuiSerial_Task(void);
static void    GuiSerial_WatchdogTask(void);
static void    GuiSerial_PublishTelemetry(void);
static const char *GuiSerial_SystemStateName(void);
static const char *GuiSerial_EmgStatusName(void);

/* USER CODE END PFP */

/* USER CODE BEGIN 0 */

/* ============================================================
 * UTILITAS
 * ============================================================ */
static float clampf(float v, float lo, float hi)
{
    if (v < lo) { return lo; }
    if (v > hi) { return hi; }
    return v;
}

static uint8_t Mcp_StartGateOk(void)
{
#if MCP_BYPASS_TEST
    return 1U;
#else
    return g_mcp_ready;
#endif
}


/* ============================================================
 * OUTPUT LAYER — satu-satunya jalan ke H-Bridge dan DAC
 * ============================================================ */
static void Output_SetCurrent(float mA)
{
    mA = clampf(mA, I_MIN_MA, I_MAX_MA);

    if ((s_last_current_mA >= 0.0f) && (fabsf(mA - s_last_current_mA) < 0.01f)) {
        return;                       /* hindari spam I2C tiap iterasi loop */
    }
    if (MCP4725_SetCurrent_mA(mA) == HAL_OK) {
        s_last_current_mA = mA;
        g_current         = mA;
        g_mcp_ready       = 1U;
    } else {
        g_dac_error_count++;          /* cache tidak di-update -> retry siklus depan */
        g_mcp_ready = 0U;
    }
}

static void Output_Disable(void)
{
#if FUZZY_TEST_ONLY
    s_hb_running   = 0U;
    s_last_pw_us   = -1.0f;
    s_last_freq_hz = -1.0f;
    g_pw_final    = 0.0f;
    g_frequency    = 0.0f;
    g_current      = 0.0f;
#else
    HBridge_Stop();                    /* semua gate LOW + TIM3 stop */
    s_hb_running   = 0U;
    s_last_pw_us   = -1.0f;
    s_last_freq_hz = -1.0f;
#if MCP_BYPASS_TEST
    if (g_mcp_ready != 0U) {
        Output_SetCurrent(0.0f);
    } else {
        s_last_current_mA = -1.0f;
        g_current = 0.0f;
    }
#else
    Output_SetCurrent(0.0f);
#endif
    g_pw_final    = 0.0f;
    g_frequency    = 0.0f;
#endif
}

static void Output_Enable(float pw_us, float freq_hz, float current_mA)
{
    pw_us      = clampf(pw_us,      PW_MIN_US,   PW_MAX_US);
    freq_hz    = clampf(freq_hz,    FREQ_MIN_HZ, FREQ_MAX_HZ);
    current_mA = clampf(current_mA, I_MIN_MA,    I_MAX_MA);
#if MCP_BYPASS_TEST

    /* BENCH dry-run mode:
     * Physical output is strictly prevented when MCP is absent:
     * H-Bridge remains stopped and no DAC current is applied.
     * Logical controller parameters (pw_final, frequency) are tracked for FSM/telemetry/CSV. */
    (void)current_mA;
    HBridge_Stop();
    s_hb_running = 0U;
    g_current = 0.0f;
    g_pw_final = pw_us;
    g_frequency = freq_hz;

#elif FUZZY_TEST_ONLY

    /* TEST FUZZY:
     * Tidak mengaktifkan H-Bridge
     * Tidak mengirim current ke MCP4725
     */
    g_pw_final = pw_us;
    g_frequency = freq_hz;
    g_current   = current_mA;

#else

    if ((pw_us != s_last_pw_us) || (freq_hz != s_last_freq_hz)) {
        HBridge_SetParams(pw_us, freq_hz);
        s_last_pw_us   = pw_us;
        s_last_freq_hz = freq_hz;
    }

    if (s_hb_running == 0U) {
        HBridge_Start();
        s_hb_running = 1U;
    }

    Output_SetCurrent(current_mA);

    g_pw_final = pw_us;
    g_frequency = freq_hz;

#endif
}

/* ============================================================
 * EMERGENCY (SPEC 20, 21) — prioritas tertinggi, latched
 * ============================================================ */
static void Fsm_ForceEmergency(void)
{
    /* Emergency hanya dipaksa oleh fault safety-critical/GUI.
     * Fatigue count tidak pernah memanggil fungsi ini. */
    STIM4_FSM_ForceEmergency(&g_fsm);
}

static void Emergency_Enter(uint8_t source)
{
	Output_Disable();
	FuzzyPW_Reset();                  /* <-- TAMBAHAN */
	g_therapy_running = 0U;

    if (g_emergency == 0U) {
        g_emergency        = 1U;
        g_emergency_source = source;
        Fsm_ForceEmergency();
        s_system           = SYSTEM_EMERGENCY;
    }
}


/* ============================================================
 * SENSOR — IMU + EMG ALWAYS ON (SPEC 2), tanpa Error_Handler (SPEC 4)
 * ============================================================ */
static void Sensors_Init(void)
{
    (void)LSM6DS3_Init(&g_imu_a);
    (void)LSM6DS3_Init(&g_imu_b);
    s_imu_a_fail = 0U;
    s_imu_b_fail = 0U;
}

static void Sensors_ReadTask(void)
{
    if (g_imu_a.ready != 0U) {
        if (LSM6DS3_Read(&g_imu_a) != HAL_OK) {
            g_imu_a_fail_count++;
            s_imu_a_fail++;
            if (s_imu_a_fail >= SENSOR_READ_FAIL_LIMIT) { g_imu_a.ready = 0U; }
        } else {
            s_imu_a_fail = 0U;
        }
    }

    if (g_imu_b.ready != 0U) {
        if (LSM6DS3_Read(&g_imu_b) != HAL_OK) {
            g_imu_b_fail_count++;
            s_imu_b_fail++;
            if (s_imu_b_fail >= SENSOR_READ_FAIL_LIMIT) { g_imu_b.ready = 0U; }
        } else {
            s_imu_b_fail = 0U;
        }
    }

    g_imu_a_angle = g_imu_a.angle;
    g_imu_b_angle = g_imu_b.angle;
    g_joint_angle = (g_imu_b.angle - g_imu_a.angle) - g_zero_offset;
}

static void Sensors_RetryTask(void)
{
    uint32_t now = HAL_GetTick();

    if ((now - s_retry_tick_ms) < SENSOR_RETRY_INTERVAL_MS) { return; }
    s_retry_tick_ms = now;

    if (g_imu_a.ready == 0U) { (void)LSM6DS3_Init(&g_imu_a); s_imu_a_fail = 0U; }
    if (g_imu_b.ready == 0U) { (void)LSM6DS3_Init(&g_imu_b); s_imu_b_fail = 0U; }
    if (g_mcp_ready == 0U) {
        if (HAL_I2C_IsDeviceReady(&hi2c1, MCP4725_ADDR, 3U, 10U) == HAL_OK) {
            g_mcp_ready = 1U;
        }
    }
    /* EMG fault -> coba start ulang akuisisi, hanya kalau terapi tidak jalan */
    if ((g_therapy_running == 0U) &&
        ((emg_status == (uint8_t)EMG_STATUS_ADC_FAULT) ||
         (emg_status == (uint8_t)EMG_STATUS_NUMERIC_FAULT) ||
         (emg_status == (uint8_t)EMG_STATUS_CALIBRATION_FAULT))) {
        g_emg_start_status = (uint32_t)EMG_AppStart(&hadc1, &htim2);
    }
}

/* ============================================================
 * KALIBRASI NON-BLOCKING (SPEC 5, 6)
 * Kalibrasi tidak boleh mengaktifkan FES.
 * ============================================================ */
static void Cal_StartImu(void)
{
    if (g_therapy_running != 0U) { g_cal_fault = CAL_FAULT_THERAPY_RUNNING; return; }
    if ((s_cal == CAL_IMU_RUN) || (s_cal == CAL_IMU_SETTLE) || (s_cal == CAL_MVC_RUN)) {
        g_cal_fault = CAL_FAULT_BUSY;
        return;
    }
    if ((g_imu_a.ready == 0U) || (g_imu_b.ready == 0U)) {
        g_cal_fault = CAL_FAULT_IMU_NOT_READY;
        s_cal       = CAL_FAIL;
        return;
    }

    Output_Disable();
    g_cal_fault      = CAL_FAULT_NONE;
    g_imu_calibrated = 0U;
    s_cal_start_ms   = HAL_GetTick();
    s_cal            = CAL_IMU_RUN;
}

static void Cal_StartMvc(void)
{
    if (g_therapy_running != 0U) { g_cal_fault = CAL_FAULT_THERAPY_RUNNING; return; }
    if ((s_cal == CAL_IMU_RUN) || (s_cal == CAL_IMU_SETTLE) || (s_cal == CAL_MVC_RUN)) {
        g_cal_fault = CAL_FAULT_BUSY;
        return;
    }
    if (g_imu_calibrated == 0U) {        /* SPEC 6 : MVC setelah kalibrasi IMU */
        g_cal_fault = CAL_FAULT_IMU_FIRST;
        s_cal       = CAL_FAIL;
        return;
    }
    if (g_emg_ready == 0U) {
        g_cal_fault = CAL_FAULT_EMG_NOT_READY;
        s_cal       = CAL_FAIL;
        return;
    }

    Output_Disable();
    g_cal_fault      = CAL_FAULT_NONE;
    g_mvc_calibrated = 0U;
    s_mvc_peak       = 0.0f;
    s_cal_start_ms   = HAL_GetTick();
    s_cal            = CAL_MVC_RUN;
}

static void Calibration_Task(void)
{
    uint32_t now = HAL_GetTick();
    float    mav;

    switch (s_cal)
    {
    case CAL_IMU_RUN:
        if ((now - s_cal_start_ms) >= IMU_CAL_DURATION_MS) {
            if ((g_imu_a.ready != 0U) && (g_imu_b.ready != 0U)) {
                /* zero_offset = IMU_B - IMU_A pada posisi referensi */
                g_zero_offset = g_imu_b.angle - g_imu_a.angle;
                LSM6DS3_ResetFilter(&g_imu_a);
                LSM6DS3_ResetFilter(&g_imu_b);
                s_prev_error   = 0.0f;
                s_cal_start_ms = now;
                s_cal          = CAL_IMU_SETTLE;
            } else {
                g_cal_fault = CAL_FAULT_IMU_NOT_READY;
                s_cal       = CAL_FAIL;
            }
        }
        break;

    case CAL_IMU_SETTLE:
        /* tunggu complementary filter konvergen lagi setelah reset */
        if ((now - s_cal_start_ms) >= IMU_CAL_SETTLE_MS) {
            g_imu_calibrated = 1U;
            s_cal            = CAL_DONE;
        }
        break;

    case CAL_MVC_RUN:
        mav = filtered_mav_mV;
        if (mav > s_mvc_peak) { s_mvc_peak = mav; }   /* MVC = MAV maksimum */
        if ((now - s_cal_start_ms) >= MVC_CAL_DURATION_MS) {
            if (s_mvc_peak >= MVC_MIN_VALID_MV) {
                s_mvc_mV         = s_mvc_peak;
                g_mvc_calibrated = 1U;
                s_cal            = CAL_DONE;
            } else {
                g_cal_fault      = CAL_FAULT_MVC_TOO_LOW;
                g_mvc_calibrated = 0U;
                s_cal            = CAL_FAIL;
            }
        }
        break;

    case CAL_IDLE:
    case CAL_DONE:
    case CAL_FAIL:
    default:
        break;
    }
}

/* ============================================================
 * KONFIGURASI PARAMETER (SPEC 8, 22)
 * ============================================================ */
static void Params_Apply(void)
{
    if (g_selected_mode == (uint8_t)STIM4_MODE_MANUAL) {
        g_manual_pw_us       = clampf(g_manual_pw_us,       PW_MIN_US,   PW_MAX_US);
        g_manual_current_mA   = clampf(g_manual_current_mA,   I_MIN_MA,    I_MAX_MA);
        g_manual_frequency_Hz = clampf(g_manual_frequency_Hz, FREQ_MIN_HZ, FREQ_MAX_HZ);
        if (g_manual_active_duration_ms < (uint32_t)TS_MS) {
            g_manual_active_duration_ms = (uint32_t)TS_MS;
        }
        if (g_manual_rest_duration_ms < (uint32_t)TS_MS) {
            g_manual_rest_duration_ms = (uint32_t)TS_MS;
        }
        g_params_configured = 1U;
    } else if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) {
    	float pw_hi = (PW_MAX_US < PW_INCR_HI_US) ? PW_MAX_US : PW_INCR_HI_US;  /* = 400 us */
    	    g_de_lpf_alpha = clampf(g_de_lpf_alpha, 0.01f, 1.0f);
            g_auto_target_angle    = clampf(g_auto_target_angle,    0.0f,        EMG_MAX_TARGET_DEG);
            g_auto_init_pw_us     = clampf(g_auto_init_pw_us,     PW_MIN_US,   pw_hi);
            g_auto_init_current_mA = clampf(g_auto_init_current_mA, I_MIN_MA,    I_MAX_MA);
            g_auto_init_freq_Hz    = clampf(g_auto_init_freq_Hz,    FREQ_MIN_HZ, FREQ_MAX_HZ);
            g_pw_incr_gain        = clampf(g_pw_incr_gain,        0.0f,        5.0f);
            g_fuzzy_de_gain        = clampf(g_fuzzy_de_gain,        0.1f,       10.0f);

            /* siapkan integrator dengan nilai awal operator */
            FuzzyPW_Init(g_auto_init_pw_us, g_pw_incr_gain, PW_MIN_US, pw_hi);
            g_pw_cmd_us   = g_auto_init_pw_us;
            g_pw_delta_us = 0.0f;

            g_params_configured = 1U;
        } else {
        g_params_configured = 0U;
    }
}

/* ============================================================
 * TERAPI — START / STOP
 * ============================================================ */
static uint8_t Therapy_StartBlockReason(void)
{
    if (g_emergency != 0U) { return START_BLOCK_EMERGENCY; }
    if ((s_cal == CAL_IMU_RUN) || (s_cal == CAL_IMU_SETTLE) || (s_cal == CAL_MVC_RUN)) {
        return START_BLOCK_BUSY;
    }
    if (g_selected_mode == (uint8_t)STIM4_MODE_NONE) { return START_BLOCK_NO_MODE; }
    if (g_params_configured == 0U)                   { return START_BLOCK_NO_PARAMS; }
    if ((g_cmd_fes_switch_on == 0U) || (Mcp_StartGateOk() == 0U)) {
        return START_BLOCK_FES_OFF;
    }

    if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) {
        /* AUTO wajib kalibrasi IMU + MVC dan sensor harus ready */
        if ((g_imu_calibrated == 0U) || (g_mvc_calibrated == 0U)) { return START_BLOCK_NEED_CAL; }
        if ((g_imu_a_ready == 0U) || (g_imu_b_ready == 0U) || (g_emg_ready == 0U)) {
            return START_BLOCK_SENSOR;
        }
    } else {
        /* MANUAL boleh bypass kalibrasi untuk simulasi */
        if ((g_bypass_calibration == 0U) &&
            ((g_imu_calibrated == 0U) || (g_mvc_calibrated == 0U))) {
            return START_BLOCK_NEED_CAL;
        }
    }
    return START_OK;
}

static void Therapy_Start(void)
{
    Output_Disable();

    g_therapy_completed  = 0U;
    s_prev_error         = 0.0f;
    s_de_filt = 0.0f;
    s_fes_was_active     = 0U;
    s_mav_ref            = 0.0f;
    g_mav_ratio          = 0.0f;
    g_pw_fuzzy          = 0.0f;
    g_manual_cycle_count = 0U;

    if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) {
    	float pw_hi = (PW_MAX_US < PW_INCR_HI_US) ? PW_MAX_US : PW_INCR_HI_US;  /* = 400 us */
            STIM4_FSM_Init(&g_fsm);
            g_target_angle = g_auto_target_angle;

            /* integrator selalu mulai dari PW initial tiap sesi terapi */
            FuzzyPW_Init(g_auto_init_pw_us, g_pw_incr_gain, PW_MIN_US, pw_hi);
            g_pw_cmd_us   = g_auto_init_pw_us;
            g_pw_delta_us = 0.0f;
        } else {
        s_manual_phase          = MANUAL_PHASE_ACTIVE;
        s_manual_phase_start_ms = HAL_GetTick();
        g_target_angle          = 0.0f;
    }

    g_therapy_running = 1U;
}

static void Therapy_Stop(uint8_t completed)
{
    g_therapy_running = 0U;
    Output_Disable();

    /* === reset seluruh state kontrol incremental === */
    FuzzyPW_Reset();
    s_de_filt        = 0.0f;      /* <-- DI SINI (state low-pass Δe) */
    s_prev_error     = 0.0f;
    s_fes_was_active = 0U;
    g_pw_cmd_us     = 0.0f;
    g_pw_delta_us   = 0.0f;
    g_pw_fuzzy      = 0.0f;
    /* =============================================== */

    if (g_emergency == 0U) {
        STIM4_FSM_Init(&g_fsm);              /* balik ke IDLE, tanpa output */
    }
    g_therapy_completed = completed;
    g_active_mode       = 0U;
}

/* ============================================================
 * MODE MANUAL (SPEC 8) — parameter fixed, tanpa fuzzy, tanpa FSM
 * ============================================================ */
static void Therapy_Manual(void)
{
    uint32_t now     = HAL_GetTick();
    uint32_t elapsed = now - s_manual_phase_start_ms;

    if (s_manual_phase == MANUAL_PHASE_ACTIVE) {
        if (elapsed >= g_manual_active_duration_ms) {
            s_manual_phase          = MANUAL_PHASE_REST;
            s_manual_phase_start_ms = now;
            g_manual_cycle_count++;
            Output_Disable();
        } else {
            Output_Enable(g_manual_pw_us, g_manual_frequency_Hz, g_manual_current_mA);
        }
    } else {
        if (elapsed >= g_manual_rest_duration_ms) {
            s_manual_phase          = MANUAL_PHASE_ACTIVE;
            s_manual_phase_start_ms = now;
        } else {
            Output_Disable();
        }
    }

    g_manual_phase = (uint8_t)s_manual_phase;
}

/* ============================================================
 * MODE AUTO (SPEC 9-16) — fuzzy + stim4_fsm
 * main.c hanya orchestrator: fuzzy tidak diubah, FSM yang memutuskan
 * fes_active, submode ACTIVE, fatigue, timer, dan pw_final_us.
 * ============================================================ */
static void Therapy_Auto(void)
{
    static uint32_t last_feature_count = 0U;
    FSM_Input in = {0};
    FSM_Output out = {0};
    FSM_State state;
    float mav, rms, error, delta_e, de_scaled;
    float pw_request, pw_command, current_mA, frequency_hz;
    uint8_t feature_updated;

    g_target_angle = g_auto_target_angle;
    error = g_target_angle - g_joint_angle;
    delta_e = error - s_prev_error;
    s_prev_error = error;
    g_error = error;
    g_delta_error = delta_e;

    s_de_filt += g_de_lpf_alpha * (delta_e - s_de_filt);
    de_scaled = s_de_filt * g_fuzzy_de_gain;

    mav = filtered_mav_mV;
    rms = filtered_rms_mV;
    g_emg_level = clampf(rms / EMG_MAX_LEVEL_MV, 0.0f, 1.0f);

    feature_updated = (feature_update_count != last_feature_count) ? 1U : 0U;
    if (feature_updated != 0U) last_feature_count = feature_update_count;

    /* Tahap 1: FSM menentukan state dan izin FES menggunakan nilai PW saat ini.
     * Tidak ada integrasi fuzzy sebelum izin ACTIVE diberikan. */
    pw_request = FuzzyPW_Get();
    in.mav_mV = mav;
    in.mvc_mV = (g_mvc_calibrated != 0U) ? s_mvc_mV : 0.0f;
    in.error = error;
    in.delta_error = delta_e;
    in.pw_command_us = pw_request;
    in.imu_ready = ((g_imu_a_ready != 0U) && (g_imu_b_ready != 0U)) ? 1U : 0U;
    in.feature_updated = feature_updated;
    in.safety_fault = 0U; /* fault safety ditangani Safety_Task/Emergency_Enter */

    state = STIM4_FSM_Update(&g_fsm, &in, &out);
    g_emg_intent = out.intent_detected;
    g_active_mode = (state == FSM_ACTIVE)
                  ? ((STIM4_FSM_GetActiveMode(&g_fsm) == ACTIVE_MODE_FATIGUE) ? 2U : 1U)
                  : 0U;
    g_fatigue_detected = out.fatigue_confirmed;
    g_fatigue_rest_count = (uint8_t)STIM4_FSM_GetFatigueRestCount(&g_fsm);
    g_mav_ratio = g_fsm.fd.reference_set ? g_fsm.fd.mav_ratio : 0.0f;

    if (state == FSM_EMERGENCY) {
        Emergency_Enter(EMERGENCY_SRC_FSM);
        return;
    }

    if (state == FSM_THERAPY_STOP) {
        /* Controlled stop: bukan emergency dan tidak boleh auto-restart. */
        Output_Disable();
        FuzzyPW_Hold(error, de_scaled);
        g_pw_delta_us = 0.0f;
        g_therapy_running = 0U;
        g_therapy_completed = 1U;
        s_fes_was_active = 0U;
        return;
    }

    current_mA = g_auto_init_current_mA; /* fuzzy tidak mengubah arus */
    frequency_hz = g_auto_init_freq_Hz;  /* fuzzy tidak mengubah frekuensi */

    if (out.fes_active != 0U) {
        /* Integrasi hanya saat FSM benar-benar mengizinkan FES ACTIVE. */
        pw_request = FuzzyPW_Step(error, de_scaled);
        pw_command = pw_request;
        if (STIM4_FSM_GetActiveMode(&g_fsm) == ACTIVE_MODE_FATIGUE) {
            if (pw_command > FSM_PW_MAX_FATIGUE_US) pw_command = FSM_PW_MAX_FATIGUE_US;
        } else if (pw_command > FSM_PW_MAX_NORMAL_US) {
            pw_command = FSM_PW_MAX_NORMAL_US;
        }
        if (pw_command < FSM_PW_MIN_US) pw_command = FSM_PW_MIN_US;

        g_pw_delta_us = FuzzyPW_GetDelta();
        g_pw_cmd_us = pw_request;
        g_pw_fuzzy = pw_request;
        Output_Enable(pw_command, frequency_hz, current_mA);
        s_fes_was_active = 1U;
    } else {
        /* IDLE/REST/FATIGUE_REST: H-Bridge OFF, DAC 0, integrator hold. */
        Output_Disable();
        (void)FuzzyPW_Hold(error, de_scaled);
        g_pw_delta_us = 0.0f;
        s_fes_was_active = 0U;
    }
}

static void Therapy_Task(void)
{
    if ((g_therapy_running == 0U) || (g_emergency != 0U)) { return; }

    if (g_selected_mode == (uint8_t)STIM4_MODE_MANUAL) {
        Therapy_Manual();
    } else if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) {
        Therapy_Auto();
    } else {
        Therapy_Stop(0U);
    }
}


/* ============================================================
 * UART GUI — direct serial protocol
 * RX : JSON newline dari GUI.py, plus alias STOP legacy.
 * TX : satu frame JSON telemetry tiap 100 ms, non-blocking (IT).
 * ============================================================ */
static void GuiSerial_Start(void)
{
    s_gui_rx_build_len       = 0U;
    s_gui_rx_head            = 0U;
    s_gui_rx_tail            = 0U;
    s_gui_tx_busy            = 0U;
    s_gui_link_seen          = 0U;
    s_gui_last_heartbeat_ms  = HAL_GetTick();
    s_gui_telemetry_tick_ms  = HAL_GetTick();
    (void)HAL_UART_Receive_IT(&huart1, &s_gui_rx_byte, 1U);
}

static uint8_t GuiSerial_PopLine(char *dst, uint16_t dst_size)
{
    uint8_t tail;

    if ((dst == NULL) || (dst_size < 2U)) { return 0U; }
    if (s_gui_rx_tail == s_gui_rx_head) { return 0U; }

    tail = s_gui_rx_tail;
    strncpy(dst, s_gui_rx_queue[tail], (size_t)dst_size - 1U);
    dst[dst_size - 1U] = '\0';
    s_gui_rx_tail = (uint8_t)((tail + 1U) % GUI_RX_QUEUE_LEN);
    return 1U;
}

static const char *GuiSerial_FindJsonValue(const char *line, const char *key)
{
    char needle[40];
    const char *p;

    if ((line == NULL) || (key == NULL)) { return NULL; }
    if (snprintf(needle, sizeof(needle), "\"%s\"", key) <= 0) { return NULL; }

    p = strstr(line, needle);
    if (p == NULL) { return NULL; }

    p = strchr(p + strlen(needle), ':');
    if (p == NULL) { return NULL; }

    p++;
    while ((*p == ' ') || (*p == '\t')) { p++; }
    return p;
}

static uint8_t GuiSerial_GetString(const char *line, const char *key, char *out, uint16_t out_size)
{
    const char *p = GuiSerial_FindJsonValue(line, key);
    uint16_t n = 0U;

    if ((p == NULL) || (out == NULL) || (out_size < 2U) || (*p != '"')) { return 0U; }

    p++;
    while ((*p != '\0') && (*p != '"') && (n < (uint16_t)(out_size - 1U))) {
        out[n++] = *p++;
    }

    if (*p != '"') { return 0U; }

    out[n] = '\0';
    return 1U;
}

static uint8_t GuiSerial_GetFloat(const char *line, const char *key, float *out)
{
    const char *p = GuiSerial_FindJsonValue(line, key);
    char *endptr;
    float v;

    if ((p == NULL) || (out == NULL)) { return 0U; }

    v = strtof(p, &endptr);
    if (endptr == p) { return 0U; }

    *out = v;
    return 1U;
}

static uint8_t GuiSerial_GetBool(const char *line, const char *key, uint8_t *out)
{
    const char *p = GuiSerial_FindJsonValue(line, key);

    if ((p == NULL) || (out == NULL)) { return 0U; }
    if ((strncmp(p, "true", 4U) == 0) || (*p == '1')) {
        *out = 1U;
        return 1U;
    }
    if ((strncmp(p, "false", 5U) == 0) || (*p == '0')) {
        *out = 0U;
        return 1U;
    }
    return 0U;
}

static float GuiSerial_PwPctToUs(float pct)
{
    pct = clampf(pct, 0.0f, 100.0f);
    return PW_MIN_US + (pct * (PW_MAX_US - PW_MIN_US) / 100.0f);
}

static float GuiSerial_PwUsToPct(float us)
{
    if (us <= 0.0f) { return 0.0f; }
    if (PW_MAX_US <= PW_MIN_US) { return 0.0f; }

    us = clampf(us, PW_MIN_US, PW_MAX_US);
    return 100.0f * (us - PW_MIN_US) / (PW_MAX_US - PW_MIN_US);
}

static void GuiSerial_RequestStop(void)
{
    g_cmd_stop_therapy   = 1U;
    g_cmd_fes_switch_on  = 0U;
}

static void GuiSerial_HandleCommand(const char *line)
{
    char cmd[32];
    float v;
    uint8_t output_requested;

    if ((strcmp(line, "!STOP") == 0) ||
        (strcmp(line, "STOP") == 0) ||
        (strcmp(line, "STOP_THERAPY") == 0) ||
        (strcmp(line, "STIM_OFF") == 0) ||
        (strcmp(line, "OUTPUT_OFF") == 0)) {
        GuiSerial_RequestStop();
        s_gui_link_seen = 1U;
        s_gui_last_heartbeat_ms = HAL_GetTick();
        return;
    }

    if (strcmp(line, "EMERGENCY_STOP") == 0) {
        Emergency_Enter(EMERGENCY_SRC_GUI);
        s_gui_link_seen = 1U;
        s_gui_last_heartbeat_ms = HAL_GetTick();
        return;
    }

    if (strstr(line, "\"type\":\"HB\"") != NULL) {
        s_gui_link_seen = 1U;
        s_gui_last_heartbeat_ms = HAL_GetTick();
        return;
    }

    if (!GuiSerial_GetString(line, "cmd", cmd, sizeof(cmd))) { return; }

    s_gui_link_seen = 1U;
    s_gui_last_heartbeat_ms = HAL_GetTick();

    if (strcmp(cmd, "CALIBRATE_ANGLE") == 0) {
        g_cmd_calibrate_imu = 1U;
        return;
    }

    if (strcmp(cmd, "CAPTURE_MVC") == 0) {
        g_cmd_calibrate_mvc = 1U;
        return;
    }

    if (strcmp(cmd, "CALIBRATE_EMG") == 0) {
        g_cmd_recalibrate_emg = 1U;
        return;
    }

    if ((strcmp(cmd, "RESET_ESTOP") == 0) ||
        (strcmp(cmd, "RESET_CLEAR") == 0) ||
        (strcmp(cmd, "RESET_SESSION") == 0) ||
        (strcmp(cmd, "CLEAR") == 0)) {
        g_cmd_reset_emergency = 1U;
        return;
    }

    if ((strcmp(cmd, "STOP_THERAPY") == 0) ||
        (strcmp(cmd, "STOP") == 0) ||
        (strcmp(cmd, "STOP_AUTO") == 0) ||
        (strcmp(cmd, "OUTPUT_OFF") == 0)) {
        GuiSerial_RequestStop();
        return;
    }

    if (strcmp(cmd, "ESTOP") == 0) {
        Emergency_Enter(EMERGENCY_SRC_GUI);
        return;
    }

    if ((strcmp(cmd, "FES_ON") == 0) || (strcmp(cmd, "STIM_ON") == 0)) {
        g_cmd_fes_switch_on = 1U;
        return;
    }

    if ((strcmp(cmd, "FES_OFF") == 0) || (strcmp(cmd, "STIM_OFF") == 0)) {
        GuiSerial_RequestStop();
        return;
    }

    if (strcmp(cmd, "APPLY_PARAMS") == 0) {
        g_cmd_apply_params = 1U;
        return;
    }

    if (strcmp(cmd, "START_THERAPY") == 0) {
        g_cmd_start_therapy = 1U;
        return;
    }

    if ((strcmp(cmd, "START_AUTO") == 0) || (strcmp(cmd, "SET_AUTO") == 0)) {
        uint8_t start_requested = (strcmp(cmd, "START_AUTO") == 0) ? 1U : 0U;
        g_selected_mode = (uint8_t)STIM4_MODE_AUTO;

        if (GuiSerial_GetFloat(line, "angle_target_deg", &v)) { g_auto_target_angle = v; }
        if (GuiSerial_GetFloat(line, "current_cmd_ma", &v) ||
            GuiSerial_GetFloat(line, "current_ma", &v)) {
            g_auto_init_current_mA = v;
        }
        if (GuiSerial_GetFloat(line, "frequency_set_hz", &v) ||
            GuiSerial_GetFloat(line, "frequency_hz", &v)) {
            g_auto_init_freq_Hz = v;
        }

        if (GuiSerial_GetFloat(line, "pulse_width_us", &v)) {
            g_auto_init_pw_us = v;
        } else if (GuiSerial_GetFloat(line, "pw_pct", &v)) {
            g_auto_init_pw_us = GuiSerial_PwPctToUs(v);
        }

        g_cmd_apply_params  = 1U;
        if (start_requested != 0U) {
            g_cmd_fes_switch_on = 1U;
            g_cmd_start_therapy = 1U;
        }
        return;
    }

    if ((strcmp(cmd, "SET_MANUAL") == 0) || (strcmp(cmd, "OUTPUT_ON") == 0)) {
        output_requested = (strcmp(cmd, "OUTPUT_ON") == 0) ? 1U : 0U;
        (void)GuiSerial_GetBool(line, "output", &output_requested);
        g_selected_mode = (uint8_t)STIM4_MODE_MANUAL;

        if (GuiSerial_GetFloat(line, "current_cmd_ma", &v) ||
            GuiSerial_GetFloat(line, "current_ma", &v)) {
            g_manual_current_mA = v;
        }
        if (GuiSerial_GetFloat(line, "frequency_set_hz", &v) ||
            GuiSerial_GetFloat(line, "frequency_hz", &v)) {
            g_manual_frequency_Hz = v;
        }

        if (GuiSerial_GetFloat(line, "pulse_width_us", &v)) {
            g_manual_pw_us = v;
        } else if (GuiSerial_GetFloat(line, "pw_pct", &v)) {
            g_manual_pw_us = GuiSerial_PwPctToUs(v);
        }

        if (GuiSerial_GetFloat(line, "active_duration_s", &v)) {
            v = clampf(v, 0.01f, 3600.0f);
            g_manual_active_duration_ms = (uint32_t)(v * 1000.0f + 0.5f);
        }

        if (GuiSerial_GetFloat(line, "rest_duration_s", &v)) {
            v = clampf(v, 0.01f, 3600.0f);
            g_manual_rest_duration_ms = (uint32_t)(v * 1000.0f + 0.5f);
        }

        g_cmd_apply_params  = 1U;
        if (output_requested != 0U) {
            g_cmd_fes_switch_on = 1U;
            g_cmd_start_therapy = 1U;
        }
        return;
    }
}

static void GuiSerial_Task(void)
{
    char line[GUI_RX_LINE_MAX];
    uint8_t processed = 0U;

    while ((processed < 4U) && GuiSerial_PopLine(line, sizeof(line))) {
        GuiSerial_HandleCommand(line);
        processed++;
    }
}

static void GuiSerial_WatchdogTask(void)
{
    if ((g_therapy_running != 0U) && (s_gui_link_seen != 0U)) {
        if ((HAL_GetTick() - s_gui_last_heartbeat_ms) > GUI_HEARTBEAT_TIMEOUT_MS) {
            GuiSerial_RequestStop();
            s_gui_link_seen = 0U;
        }
    }
}

static void GuiSerial_FormatFixed(char *dst, uint16_t dst_size, float value, uint8_t decimals)
{
    uint32_t scale = 1U;
    uint8_t i;
    uint8_t negative = (value < 0.0f) ? 1U : 0U;
    float magnitude = negative ? -value : value;
    uint32_t scaled;
    uint32_t whole;
    uint32_t frac;

    if ((dst == NULL) || (dst_size == 0U)) { return; }
    if (decimals > 4U) { decimals = 4U; }

    for (i = 0U; i < decimals; i++) { scale *= 10U; }

    scaled = (uint32_t)(magnitude * (float)scale + 0.5f);
    whole  = scaled / scale;
    frac   = scaled % scale;

    if (decimals == 0U) {
        (void)snprintf(dst, dst_size, "%s%lu",
                       negative ? "-" : "",
                       (unsigned long)whole);
    } else {
        (void)snprintf(dst, dst_size, "%s%lu.%0*lu",
                       negative ? "-" : "",
                       (unsigned long)whole,
                       (int)decimals,
                       (unsigned long)frac);
    }
}

static const char *GuiSerial_FsmName(void)
{
    FSM_State state = STIM4_FSM_GetState(&g_fsm);
    if ((g_emergency != 0U) || (state == FSM_EMERGENCY)) return "EMERGENCY";
    if (g_selected_mode == (uint8_t)STIM4_MODE_MANUAL) {
        if (g_therapy_running == 0U) return "MANUAL_STOPPED";
        return (s_manual_phase == MANUAL_PHASE_ACTIVE) ? "MANUAL_ACTIVE" : "MANUAL_REST";
    }
    if (g_selected_mode != (uint8_t)STIM4_MODE_AUTO) return "IDLE";
    switch (state) {
    case FSM_IDLE: return (g_therapy_running != 0U) ? "WAITING_INTENT" : "IDLE";
    case FSM_ACTIVE: return (STIM4_FSM_GetActiveMode(&g_fsm) == ACTIVE_MODE_FATIGUE)
                          ? "ACTIVE_FATIGUE" : "ACTIVE_NORMAL";
    case FSM_REST: return "REST";
    case FSM_FATIGUE_REST: return "FATIGUE_REST";
    case FSM_THERAPY_STOP: return "THERAPY_STOP";
    case FSM_EMERGENCY: return "EMERGENCY";
    default: return "EMERGENCY";
    }
}

static const char *GuiSerial_PhaseName(void)
{
    if (g_emergency != 0U) { return "E_STOP"; }
    if (g_therapy_running == 0U) { return "IDLE"; }
    if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) { return "AUTO"; }
    if (g_selected_mode == (uint8_t)STIM4_MODE_MANUAL) { return "MANUAL"; }
    return "IDLE";
}

static const char *GuiSerial_FaultName(void)
{
    if (g_emergency != 0U) { return "EMERGENCY"; }

    switch (g_cal_fault) {
    case CAL_FAULT_NONE:             return "NONE";
    case CAL_FAULT_IMU_NOT_READY:    return "CAL_IMU_NOT_READY";
    case CAL_FAULT_EMG_NOT_READY:    return "CAL_EMG_NOT_READY";
    case CAL_FAULT_MVC_TOO_LOW:      return "CAL_MVC_TOO_LOW";
    case CAL_FAULT_IMU_FIRST:        return "CAL_IMU_FIRST";
    case CAL_FAULT_BUSY:             return "CAL_BUSY";
    case CAL_FAULT_THERAPY_RUNNING:  return "CAL_THERAPY_RUNNING";
    default:                         return "FAULT";
    }
}

static const char *GuiSerial_EmgStatusName(void)
{
    switch (emg_status) {
    case EMG_STATUS_BOOT:               return "BOOT";
    case EMG_STATUS_SENSOR_SETTLING:    return "SETTLING";
    case EMG_STATUS_CALIBRATING:        return "CALIBRATING";
    case EMG_STATUS_READY:              return "READY";
    case EMG_STATUS_ADC_FAULT:          return "ADC_FAULT";
    case EMG_STATUS_NUMERIC_FAULT:      return "NUMERIC_FAULT";
    case EMG_STATUS_CALIBRATION_FAULT:  return "CALIBRATION_FAULT";
    default:                            return "UNKNOWN";
    }
}

static const char *GuiSerial_SystemStateName(void)
{
    switch ((System_State)g_system_state) {
    case SYSTEM_INIT:           return "SYSTEM_INIT";
    case SYSTEM_WAIT_READY:     return "SYSTEM_WAIT_READY";
    case SYSTEM_CALIBRATION:    return "SYSTEM_CALIBRATION";
    case SYSTEM_CONFIG:         return "SYSTEM_CONFIG";
    case SYSTEM_READY_TO_START: return "SYSTEM_READY_TO_START";
    case SYSTEM_THERAPY:        return "SYSTEM_THERAPY";
    case SYSTEM_COMPLETED:      return "SYSTEM_COMPLETED";
    case SYSTEM_EMERGENCY:      return "SYSTEM_EMERGENCY";
    default:                    return "SYSTEM_INIT";
    }
}

static const char *GuiSerial_SignalQualityName(void)
{
    if ((emg_error_flags & EMG_ERROR_EXCESSIVE_CLIPPING) != 0U) return "CLIPPING";
    return (g_emg_ready != 0U) ? "GOOD" : "INVALID";
}

static const char *GuiSerial_StartBlockName(void)
{
    switch (g_start_block) {
    case START_OK:              return "OK";
    case START_BLOCK_EMERGENCY: return "EMERGENCY";
    case START_BLOCK_NO_MODE:   return "NO_MODE";
    case START_BLOCK_NO_PARAMS: return "NO_PARAMS";
    case START_BLOCK_FES_OFF:   return "FES_OFF";
    case START_BLOCK_NEED_CAL:  return "NEED_CALIBRATION";
    case START_BLOCK_SENSOR:    return "SENSOR_NOT_READY";
    case START_BLOCK_BUSY:      return "BUSY";
    default:                    return "UNKNOWN";
    }
}

static const char *GuiSerial_FesStatusName(uint8_t output_active)
{
    if (g_mcp_ready == 0U) return "FAULT";
    if (output_active != 0U) return "ACTIVE";
    if ((g_cmd_fes_switch_on == 0U) || (g_emergency != 0U)) return "OFF";
    return "READY";
}

static const char *GuiSerial_McpStatusName(void)
{
    if (g_mcp_ready != 0U) return "OK";
#if MCP_BYPASS_TEST
    return "BYPASS";
#else
    return "ERROR";
#endif
}

static uint8_t GuiSerial_OutputActive(void)
{
#if MCP_BYPASS_TEST
    /* Dry-run tidak boleh pernah diklaim sebagai keluaran fisik aktif. */
    return 0U;
#else
    if ((g_emergency != 0U) ||
        (g_therapy_running == 0U) ||
        (g_cmd_fes_switch_on == 0U) ||
        (g_mcp_ready == 0U)) {
        return 0U;
    }

    if (g_selected_mode == (uint8_t)STIM4_MODE_MANUAL) {
        return (s_manual_phase == MANUAL_PHASE_ACTIVE) ? 1U : 0U;
    }

    if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) {
        return s_fes_was_active;
    }

    return 0U;
#endif
}

static void GuiSerial_PublishTelemetry(void)
{
    uint32_t now = HAL_GetTick();
    uint32_t timer_ms = 0U, remaining_ms = 0U, duration_ms = 0U;
    int len;
    uint8_t output_active;
    float set_current = 0.0f, set_freq = 0.0f, command_pw = 0.0f;
    float active_s = 0.0f, rest_s = 0.0f;
    const char *mode_name = "NONE";
    const char *active_mode_name = "NONE";
    const char *fatigue_state_name = "NORMAL";
    const char *hbridge_state_name;
    char current[20], current_set[20], angle[20], target[20], err[20], derr[20];
    char pw_pct[20], pw_cmd_pct[20], pulse_us[20], freq_set[20], freq_output[20];
    char mav[20], rms[20], mvc[20], mav_ratio[20], fuzzy_output[20], clipping[20];
    char imu_a[20], imu_b[20], active_time[20], rest_time[20];
    char dac_voltage[20], zero_offset[20];

    if ((now - s_gui_telemetry_tick_ms) < GUI_TELEMETRY_PERIOD_MS) return;
    s_gui_telemetry_tick_ms = now;
    if (s_gui_tx_busy != 0U) return;

    output_active = GuiSerial_OutputActive();
    hbridge_state_name = output_active ? "RUNNING" : "OFF";

    if (g_selected_mode == (uint8_t)STIM4_MODE_MANUAL) {
        mode_name = "MANUAL";
        active_mode_name = (s_manual_phase == MANUAL_PHASE_ACTIVE) ? "NORMAL" : "NONE";
        set_current = g_manual_current_mA;
        set_freq = g_manual_frequency_Hz;
        command_pw = g_manual_pw_us;
        active_s = (float)g_manual_active_duration_ms / 1000.0f;
        rest_s = (float)g_manual_rest_duration_ms / 1000.0f;
        timer_ms = now - s_manual_phase_start_ms;
        duration_ms = (s_manual_phase == MANUAL_PHASE_ACTIVE)
                    ? g_manual_active_duration_ms : g_manual_rest_duration_ms;
        remaining_ms = (timer_ms < duration_ms) ? (duration_ms - timer_ms) : 0U;
    } else if (g_selected_mode == (uint8_t)STIM4_MODE_AUTO) {
        FSM_State state = STIM4_FSM_GetState(&g_fsm);
        mode_name = "AUTO";
        set_current = g_auto_init_current_mA;
        set_freq = g_auto_init_freq_Hz;
        command_pw = (g_pw_cmd_us > 0.0f) ? g_pw_cmd_us : g_auto_init_pw_us;
        active_s = (float)FSM_ACTIVE_DURATION_MS / 1000.0f;
        rest_s = (state == FSM_FATIGUE_REST)
               ? (float)FSM_FATIGUE_REST_DURATION_MS / 1000.0f
               : (float)FSM_REST_DURATION_MS / 1000.0f;
        timer_ms = STIM4_FSM_GetStateElapsedMs(&g_fsm);
        remaining_ms = STIM4_FSM_GetStateRemainingMs(&g_fsm);
        if (state == FSM_ACTIVE) {
            active_mode_name = (STIM4_FSM_GetActiveMode(&g_fsm) == ACTIVE_MODE_FATIGUE)
                             ? "FATIGUE" : "NORMAL";
        }
        if (g_fatigue_detected != 0U) fatigue_state_name = "CONFIRMED";
        else if (g_fsm.fd.persist_count > 0U) fatigue_state_name = "CANDIDATE";
    }

#if MCP_BYPASS_TEST
    /* In dry-run bench bypass mode:
     * Display logical parameters when therapy is logically active, while physical output remains strictly OFF. */
    uint8_t logical_active = (g_therapy_running != 0U && (s_fes_was_active != 0U || s_manual_phase == MANUAL_PHASE_ACTIVE)) ? 1U : 0U;
    float disp_curr = logical_active ? set_current : 0.0f;
    float disp_freq = logical_active ? set_freq : 0.0f;
    float dac_cmd_v = logical_active ? clampf((set_current / 1000.0f) * RSENSE_OHM, 0.0f, DAC_VREF) : 0.0f;

    GuiSerial_FormatFixed(current, sizeof(current), disp_curr, 3U);
    GuiSerial_FormatFixed(freq_output, sizeof(freq_output), disp_freq, 2U);
    GuiSerial_FormatFixed(dac_voltage, sizeof(dac_voltage), dac_cmd_v, 3U);
#else
    float dac_cmd_v = (output_active != 0U && g_current > 0.0f) ? clampf((g_current / 1000.0f) * RSENSE_OHM, 0.0f, DAC_VREF) : 0.0f;
    GuiSerial_FormatFixed(current, sizeof(current), g_current, 3U);
    GuiSerial_FormatFixed(freq_output, sizeof(freq_output), output_active ? g_frequency : 0.0f, 2U);
    GuiSerial_FormatFixed(dac_voltage, sizeof(dac_voltage), dac_cmd_v, 3U);
#endif
    GuiSerial_FormatFixed(current_set, sizeof(current_set), set_current, 3U);
    GuiSerial_FormatFixed(angle, sizeof(angle), g_joint_angle, 2U);
    GuiSerial_FormatFixed(target, sizeof(target), g_target_angle, 2U);
    GuiSerial_FormatFixed(err, sizeof(err), g_error, 2U);
    GuiSerial_FormatFixed(derr, sizeof(derr), g_delta_error, 2U);
    GuiSerial_FormatFixed(pw_pct, sizeof(pw_pct), GuiSerial_PwUsToPct(g_pw_final), 2U);
    GuiSerial_FormatFixed(pw_cmd_pct, sizeof(pw_cmd_pct), GuiSerial_PwUsToPct(command_pw), 2U);
    GuiSerial_FormatFixed(pulse_us, sizeof(pulse_us), g_pw_final, 1U);
    GuiSerial_FormatFixed(freq_set, sizeof(freq_set), set_freq, 2U);
    GuiSerial_FormatFixed(zero_offset, sizeof(zero_offset), g_zero_offset, 2U);
    GuiSerial_FormatFixed(mav, sizeof(mav), g_mav, 4U);
    GuiSerial_FormatFixed(rms, sizeof(rms), g_rms, 4U);
    GuiSerial_FormatFixed(mvc, sizeof(mvc), g_mvc, 4U);
    GuiSerial_FormatFixed(mav_ratio, sizeof(mav_ratio), g_mav_ratio, 4U);
    GuiSerial_FormatFixed(fuzzy_output, sizeof(fuzzy_output), g_pw_fuzzy, 2U);
    GuiSerial_FormatFixed(clipping, sizeof(clipping), clipping_percent_1s, 2U);
    GuiSerial_FormatFixed(imu_a, sizeof(imu_a), g_imu_a_angle, 2U);
    GuiSerial_FormatFixed(imu_b, sizeof(imu_b), g_imu_b_angle, 2U);
    GuiSerial_FormatFixed(active_time, sizeof(active_time), active_s, 2U);
    GuiSerial_FormatFixed(rest_time, sizeof(rest_time), rest_s, 2U);

    len = snprintf(s_gui_tx_buffer, sizeof(s_gui_tx_buffer),
        "{\"type\":\"TEL\",\"mcu_status\":\"ONLINE\",\"mode\":\"%s\","
        "\"system_state\":\"%s\",\"therapy_running\":%s,"
        "\"fsm_state\":\"%s\",\"active_mode\":\"%s\","
        "\"current_cmd_ma\":%s,\"current_set_ma\":%s,"
        "\"angle_deg\":%s,\"angle_target_deg\":%s,\"angle_error_deg\":%s,\"delta_error_deg\":%s,"
        "\"pw_pct\":%s,\"pw_command_pct\":%s,\"pulse_width_us\":%s,"
        "\"frequency_set_hz\":%s,\"frequency_output_hz\":%s,"
        "\"emg_mav_mv\":%s,\"emg_rms_mv\":%s,\"mvc_value_mv\":%s,\"mav_ratio\":%s,"
        "\"clipping_percent_1s\":%s,\"emg_error_flags\":%lu,"
        "\"fuzzy_output_us\":%s,\"fatigue_state\":\"%s\",\"fatigue_flag\":%s,\"fatigue_count\":%u,"
        "\"phase\":\"%s\",\"hbridge_state\":\"%s\",\"output_active\":%s,"
        "\"therapy_timer_ms\":%lu,\"state_remaining_ms\":%lu,"
        "\"fault\":\"%s\",\"emergency\":%u,\"emergency_source\":%u,"
        "\"imu_a_status\":\"%s\",\"imu_b_status\":\"%s\",\"imu_a_angle_deg\":%s,\"imu_b_angle_deg\":%s,"
        "\"angle_calibrated\":%s,\"emg_calibrated\":%s,\"mvc_ready\":%s,"
        "\"emg_status\":\"%s\",\"signal_quality\":\"%s\","
        "\"mcp4725_status\":\"%s\",\"hbridge_status\":\"%s\",\"fes_status\":\"%s\","
        "\"start_block\":\"%s\","
        "\"dac_voltage_v\":%s,\"imu_zero_offset_deg\":%s,"
        "\"intent_state\":\"%s\",\"active_duration_s\":%s,\"rest_duration_s\":%s}\n",
        mode_name, GuiSerial_SystemStateName(),
        (g_therapy_running != 0U) ? "true" : "false",
        GuiSerial_FsmName(), active_mode_name,
        current, current_set, angle, target, err, derr,
        pw_pct, pw_cmd_pct, pulse_us, freq_set, freq_output,
        mav, rms, mvc, mav_ratio,
        clipping, (unsigned long)emg_error_flags, fuzzy_output,
        fatigue_state_name, (g_fatigue_detected != 0U) ? "true" : "false",
        (unsigned int)g_fatigue_rest_count,
        GuiSerial_PhaseName(), hbridge_state_name, output_active ? "true" : "false",
        (unsigned long)timer_ms, (unsigned long)remaining_ms,
        GuiSerial_FaultName(), (unsigned int)g_emergency, (unsigned int)g_emergency_source,
        (g_imu_a_ready != 0U) ? "OK" : "NOT_READY",
        (g_imu_b_ready != 0U) ? "OK" : "NOT_READY", imu_a, imu_b,
        (g_imu_calibrated != 0U) ? "true" : "false",
        (g_mvc_calibrated != 0U) ? "true" : "false",
        (g_mvc_calibrated != 0U) ? "true" : "false",
        GuiSerial_EmgStatusName(), GuiSerial_SignalQualityName(),
        GuiSerial_McpStatusName(),
        (g_mcp_ready != 0U) ? "READY" : "NOT_READY",
        GuiSerial_FesStatusName(output_active),
        GuiSerial_StartBlockName(),
        dac_voltage, zero_offset,
        (g_emg_intent != 0U) ? "DETECTED" : "WAITING", active_time, rest_time);

    if ((len <= 0) || (len >= (int)sizeof(s_gui_tx_buffer))) return;
    s_gui_tx_busy = 1U;
    if (HAL_UART_Transmit_IT(&huart1, (uint8_t *)s_gui_tx_buffer, (uint16_t)len) != HAL_OK)
        s_gui_tx_busy = 0U;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    uint8_t next_head;

    if ((huart == NULL) || (huart->Instance != USART1)) { return; }

    if ((s_gui_rx_byte == '\n') || (s_gui_rx_byte == '\r')) {
        if (s_gui_rx_build_len > 0U) {
            next_head = (uint8_t)((s_gui_rx_head + 1U) % GUI_RX_QUEUE_LEN);

            if (next_head != s_gui_rx_tail) {
                s_gui_rx_build[s_gui_rx_build_len] = '\0';
                memcpy(
                    s_gui_rx_queue[s_gui_rx_head],
                    s_gui_rx_build,
                    (size_t)s_gui_rx_build_len + 1U
                );
                s_gui_rx_head = next_head;
            } else {
                g_gui_rx_drop_count++;
            }

            s_gui_rx_build_len = 0U;
        }
    } else if (s_gui_rx_build_len < (GUI_RX_LINE_MAX - 1U)) {
        s_gui_rx_build[s_gui_rx_build_len++] = (char)s_gui_rx_byte;
    } else {
        s_gui_rx_build_len = 0U;
        g_gui_rx_drop_count++;
    }

    (void)HAL_UART_Receive_IT(&huart1, &s_gui_rx_byte, 1U);
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if ((huart != NULL) && (huart->Instance == USART1)) {
        s_gui_tx_busy = 0U;
    }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if ((huart != NULL) && (huart->Instance == USART1)) {
        s_gui_tx_busy = 0U;
        (void)HAL_UART_Receive_IT(&huart1, &s_gui_rx_byte, 1U);
    }
}


/* ============================================================
 * COMMAND GUI (SPEC 22)
 * ============================================================ */
static void Command_Task(void)
{
    /* ganti mode = stop terapi + wajib apply parameter ulang */
    if (g_selected_mode != s_last_mode) {
        if (g_therapy_running != 0U) { Therapy_Stop(0U); }
        g_params_configured = 0U;
        s_last_mode         = g_selected_mode;
    }

    /* saklar FES dimatikan saat terapi = stop */
    if ((g_therapy_running != 0U) && (g_cmd_fes_switch_on == 0U)) {
        Therapy_Stop(0U);
    }

    if (g_cmd_stop_therapy != 0U) {
        g_cmd_stop_therapy = 0U;
        if (g_therapy_running != 0U) { Therapy_Stop(1U); }
    }

    if (g_cmd_apply_params != 0U) {
        g_cmd_apply_params = 0U;
        Params_Apply();
    }

    if (g_cmd_calibrate_imu != 0U) {
        g_cmd_calibrate_imu = 0U;
        if (g_emergency == 0U) { Cal_StartImu(); }
    }

    if (g_cmd_calibrate_mvc != 0U) {
        g_cmd_calibrate_mvc = 0U;
        if (g_emergency == 0U) { Cal_StartMvc(); }
    }

    if (g_cmd_recalibrate_emg != 0U) {
        g_cmd_recalibrate_emg = 0U;
        if ((g_emergency == 0U) && (g_therapy_running == 0U)) {
            g_mvc_calibrated = 0U;             /* MVC lama tidak valid lagi */
            EMG_RequestRecalibration();
        }
    }

    if (g_cmd_start_therapy != 0U) {
        g_cmd_start_therapy = 0U;
        g_start_block = Therapy_StartBlockReason();
        if ((g_start_block == START_OK) && (g_therapy_running == 0U)) {
            Therapy_Start();
        }
    }

#if STIM4_ALLOW_EMERGENCY_RESET
    if (g_cmd_reset_emergency != 0U) {
        uint8_t critical_fault_active;
        g_cmd_reset_emergency = 0U;

        critical_fault_active = (Mcp_StartGateOk() == 0U) ? 1U : 0U;
        if ((g_selected_mode == (uint8_t)STIM4_MODE_AUTO) &&
            ((g_imu_a_ready == 0U) || (g_imu_b_ready == 0U))) {
            critical_fault_active = 1U;
        }

        /* STM32 authority: reset ditolak selama penyebab critical masih aktif. */
        if (critical_fault_active == 0U) {
            Output_Disable();
            g_therapy_running = 0U;
            g_therapy_completed = 0U;
            FuzzyPW_Reset();
            STIM4_FSM_ResetSession(&g_fsm);
            s_de_filt = 0.0f;
            s_prev_error = 0.0f;
            s_fes_was_active = 0U;
            s_mav_ref = 0.0f;
            g_mav_ratio = 0.0f;
            g_pw_cmd_us = 0.0f;
            g_pw_delta_us = 0.0f;
            g_pw_fuzzy = 0.0f;
            g_active_mode = 0U;
            g_fatigue_detected = 0U;
            g_fatigue_rest_count = 0U;
            g_cmd_start_therapy = 0U;
            g_cmd_stop_therapy = 0U;
            g_cmd_apply_params = 0U;
            g_cmd_fes_switch_on = 0U; /* RESET tidak menyalakan FES */
            g_params_configured = 0U;
            s_cal = CAL_IDLE;
            g_cal_fault = CAL_FAULT_NONE;
            g_emergency = 0U;
            g_emergency_source = EMERGENCY_SRC_NONE;
            s_system = SYSTEM_WAIT_READY;
        }
    }
#else
    g_cmd_reset_emergency = 0U;
#endif
}

/* ============================================================
 * SAFETY (SPEC 3, 20) — output OFF kecuali benar-benar boleh stimulasi
 * ============================================================ */
static void Safety_Task(void)
{
    FSM_State state = STIM4_FSM_GetState(&g_fsm);

    if ((g_emergency == 0U) && (state == FSM_EMERGENCY)) {
        Emergency_Enter(EMERGENCY_SRC_FSM);
        return;
    }

    /* Sensor safety-critical hilang selama terapi => EMERGENCY latched. */
    if ((g_emergency == 0U) && (g_therapy_running != 0U)) {
        if (Mcp_StartGateOk() == 0U) {
            Emergency_Enter(EMERGENCY_SRC_FSM);
            return;
        }
        if ((g_selected_mode == (uint8_t)STIM4_MODE_AUTO) &&
            ((g_imu_a_ready == 0U) || (g_imu_b_ready == 0U))) {
            Emergency_Enter(EMERGENCY_SRC_FSM);
            return;
        }
    }

    /* Output hanya boleh hidup pada manual ACTIVE atau FSM_ACTIVE AUTO. */
    if ((g_emergency != 0U) || (g_therapy_running == 0U) ||
        (g_cmd_fes_switch_on == 0U) || (Mcp_StartGateOk() == 0U) ||
        ((g_selected_mode == (uint8_t)STIM4_MODE_AUTO) &&
         (state != FSM_ACTIVE))) {
        Output_Disable();
    }
}

/* ============================================================
 * STATUS untuk GUI / Live Expression (SPEC 4, 23, 24)
 * ============================================================ */
static void Status_UpdateReadiness(void)
{
    g_imu_a_ready = g_imu_a.ready;
    g_imu_b_ready = g_imu_b.ready;
    g_emg_ready   = ((filter_ready != 0U) &&
                     (emg_status == (uint8_t)EMG_STATUS_READY)) ? 1U : 0U;
    g_fes_ready = ((g_cmd_fes_switch_on != 0U) &&
                   (g_mcp_ready != 0U)) ? 1U : 0U;

    g_start_block  = Therapy_StartBlockReason();
    g_system_ready = (g_start_block == START_OK) ? 1U : 0U;
}

static void Status_Publish(void)
{
    g_mav = filtered_mav_mV;
    g_rms = filtered_rms_mV;
    g_mvc = (g_mvc_calibrated != 0U) ? s_mvc_mV : 0.0f;

    g_cal_state         = (uint8_t)s_cal;
    g_current_fsm_state = (uint8_t)STIM4_FSM_GetState(&g_fsm);

    if (g_emergency != 0U) {
        s_system = SYSTEM_EMERGENCY;
    } else if (g_therapy_running != 0U) {
        s_system = SYSTEM_THERAPY;
    } else if ((s_cal == CAL_IMU_RUN) || (s_cal == CAL_IMU_SETTLE) || (s_cal == CAL_MVC_RUN)) {
        s_system = SYSTEM_CALIBRATION;
    } else if ((g_imu_a_ready == 0U) || (g_imu_b_ready == 0U) || (g_emg_ready == 0U)) {
        s_system = SYSTEM_WAIT_READY;
    } else if (g_therapy_completed != 0U) {
        s_system = SYSTEM_COMPLETED;
    } else if (g_system_ready != 0U) {
        s_system = SYSTEM_READY_TO_START;
    } else {
        s_system = SYSTEM_CONFIG;
    }

    g_system_state = (uint8_t)s_system;
}
/* USER CODE END 0 */

int main(void)
{
  /* USER CODE BEGIN 1 */
  uint32_t now;
  /* USER CODE END 1 */

  HAL_Init();

  /* USER CODE BEGIN Init */
  /* USER CODE END Init */

  SystemClock_Config();

  /* USER CODE BEGIN SysInit */
  /* USER CODE END SysInit */

  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_I2C1_Init();
  MX_TIM2_Init();
  MX_TIM3_Init();
  MX_USART1_UART_Init();

  /* USER CODE BEGIN 2 */

  /* 1. OUTPUT WAJIB OFF LEBIH DULU (SPEC 3)
   *    HBridge_Init hanya membuat semua gate LOW; TIM3 belum jalan,
   *    jadi tidak ada stimulasi sampai HBridge_Start dipanggil saat terapi. */
  HBridge_Init();
  s_hb_running = 0U;

  if (HAL_I2C_IsDeviceReady(&hi2c1, MCP4725_ADDR, 3U, 10U) == HAL_OK) {
      g_mcp_ready = 1U;
  } else {
      g_mcp_ready = 0U;
  }

  Output_SetCurrent(0.0f);

  /* 2. FSM terapi di IDLE */
  STIM4_FSM_Init(&g_fsm);

  /* 3. SENSOR ALWAYS ON (SPEC 2)
   *    Kegagalan sensor menjadi STATUS, bukan Error_Handler (SPEC 4). */
  Sensors_Init();
  g_emg_start_status = (uint32_t)EMG_AppStart(&hadc1, &htim2);

  /* 4. Belum kalibrasi, belum pilih mode, belum ada terapi (SPEC 5, 6) */
  s_system        = SYSTEM_WAIT_READY;
  s_ctrl_tick_ms  = HAL_GetTick();
  s_retry_tick_ms = s_ctrl_tick_ms;
  s_loop_tick_ms  = s_ctrl_tick_ms;

  /* 5. UART GUI selalu menerima command dan menerbitkan telemetry. */
  GuiSerial_Start();

  /* USER CODE END 2 */

  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */
    /* USER CODE BEGIN 3 */

    /* 2 — EMG background: watchdog DMA stall + handle recalibration */
    EMG_AppProcess();

    /* 3 — status komponen (IMU / EMG / FES / SYSTEM READY) */
    Status_UpdateReadiness();

    /* 4 — command UART dari GUI -> flag/parameter orchestrator */
    GuiSerial_Task();
    GuiSerial_WatchdogTask();
    Command_Task();

    /* 5 — sensor + kalibrasi + terapi @ TS_MS
     *     (dt complementary filter di lsm6ds3.c fixed = TS_MS) */
    now = HAL_GetTick();
    if ((now - s_ctrl_tick_ms) >= (uint32_t)TS_MS) {
        s_ctrl_tick_ms = now;
        Sensors_ReadTask();
        Calibration_Task();
        Therapy_Task();
    }

    /* 6 — retry init sensor yang belum ready */
    Sensors_RetryTask();

    /* 7 — safety: paksa output OFF kalau tidak boleh stimulasi */
    Safety_Task();

    /* 8 — publish status untuk GUI / Live Expression + UART telemetry */
    Status_Publish();
    GuiSerial_PublishTelemetry();

    /* diagnostik: interval loop maksimum (bukti non-blocking) */
    now = HAL_GetTick();
    if ((now - s_loop_tick_ms) > g_loop_max_interval_ms) {
        g_loop_max_interval_ms = now - s_loop_tick_ms;
    }
    s_loop_tick_ms = now;

    /* USER CODE END 3 */
  }
}

void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM      = 25;
  RCC_OscInitStruct.PLL.PLLN      = 336;
  RCC_OscInitStruct.PLL.PLLP      = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ      = 4;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) { Error_Handler(); }
  RCC_ClkInitStruct.ClockType      = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK) { Error_Handler(); }
}

static void MX_ADC1_Init(void)
{
  ADC_ChannelConfTypeDef sConfig = {0};
  hadc1.Instance                   = ADC1;
  hadc1.Init.ClockPrescaler        = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution            = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode          = DISABLE;
  hadc1.Init.ContinuousConvMode    = DISABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge  = ADC_EXTERNALTRIGCONVEDGE_RISING;
  hadc1.Init.ExternalTrigConv      = ADC_EXTERNALTRIGCONV_T2_TRGO;
  hadc1.Init.DataAlign             = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion       = 1;
  hadc1.Init.DMAContinuousRequests = ENABLE;
  hadc1.Init.EOCSelection          = ADC_EOC_SINGLE_CONV;
  if (HAL_ADC_Init(&hadc1) != HAL_OK) { Error_Handler(); }
  sConfig.Channel      = ADC_CHANNEL_0;
  sConfig.Rank         = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_84CYCLES;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK) { Error_Handler(); }
}

static void MX_I2C1_Init(void)
{
  hi2c1.Instance             = I2C1;
  hi2c1.Init.ClockSpeed      = 100000;
  hi2c1.Init.DutyCycle       = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1     = 0;
  hi2c1.Init.AddressingMode  = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2     = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode   = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK) { Error_Handler(); }
}

static void MX_TIM2_Init(void)
{
  TIM_ClockConfigTypeDef  sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig      = {0};
  htim2.Instance               = TIM2;
  htim2.Init.Prescaler         = 83;
  htim2.Init.CounterMode       = TIM_COUNTERMODE_UP;
  htim2.Init.Period            = 249;
  htim2.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim2) != HAL_OK) { Error_Handler(); }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim2, &sClockSourceConfig) != HAL_OK) { Error_Handler(); }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
  sMasterConfig.MasterSlaveMode     = TIM_MASTERSLAVEMODE_ENABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK) { Error_Handler(); }
}

static void MX_TIM3_Init(void)
{
  TIM_ClockConfigTypeDef  sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig      = {0};
  htim3.Instance               = TIM3;
  htim3.Init.Prescaler         = 83;
  htim3.Init.CounterMode       = TIM_COUNTERMODE_UP;
  htim3.Init.Period            = 199;
  htim3.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim3) != HAL_OK) { Error_Handler(); }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim3, &sClockSourceConfig) != HAL_OK) { Error_Handler(); }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK) { Error_Handler(); }
}

static void MX_USART1_UART_Init(void)
{
  huart1.Instance          = USART1;
  huart1.Init.BaudRate     = 115200;
  huart1.Init.WordLength   = UART_WORDLENGTH_8B;
  huart1.Init.StopBits     = UART_STOPBITS_1;
  huart1.Init.Parity       = UART_PARITY_NONE;
  huart1.Init.Mode         = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl    = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK) { Error_Handler(); }
}

static void MX_DMA_Init(void)
{
  __HAL_RCC_DMA2_CLK_ENABLE();
  HAL_NVIC_SetPriority(DMA2_Stream0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA2_Stream0_IRQn);
}

static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();


  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4|GPIO_PIN_5, GPIO_PIN_RESET);
  GPIO_InitStruct.Pin   = GPIO_PIN_4|GPIO_PIN_5;
  GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull  = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
}

/* USER CODE BEGIN 4 */

/* TIM3 = H-Bridge pulse timing (TIM2 dipakai emg_app sebagai ADC TRGO) */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM3) { HBridge_TimerCallback(); }
}

/* USER CODE END 4 */

void Error_Handler(void)
{
  __disable_irq();
  while (1) { }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
  (void)file; (void)line;
}
#endif
