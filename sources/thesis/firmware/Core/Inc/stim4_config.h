#ifndef STIM4_CONFIG_H
#define STIM4_CONFIG_H

/* =============================================
 * STIM4 — Konfigurasi Global
 * STM32F411CEU6 (BlackPill)
 * TIM2 = ADC trigger EMG @ 4000 Hz (TRGO)
 * TIM3 = H-Bridge pulse timing @ 1 MHz
 * PA0  = ADC1_IN0 — SEN0240 EMG
 * PA4–PA7 = GPIO H-Bridge
 * ============================================= */

/* =============================================
 * GPIO H-Bridge — MODE 2 PIN
 * PA4 = PHASE_A, PA5 = PHASE_B
 *
 * Kontrak sinyal (WAJIB dipenuhi driver gate):
 *   A=1, B=0  -> arus arah A (positif)
 *   A=0, B=1  -> arus arah B (negatif)
 *   A=0, B=0  -> OFF / high-Z (dead-time & rest)
 *   A=1, B=1  -> TIDAK PERNAH dihasilkan firmware
 *
 * Driver harus punya interlock + dead-time internal
 * (IR2184 / L6387 / DRV8871 / IR2110 single-input shaping).
 * Pasang pull-down 10k eksternal di PA4 & PA5.
 * ============================================= */
#define HB_PHASE_A_PORT   GPIOA
#define HB_PHASE_A_PIN    GPIO_PIN_4
#define HB_PHASE_B_PORT   GPIOA
#define HB_PHASE_B_PIN    GPIO_PIN_5
#define RELAY_GPIO_Port   GPIOA
#define RELAY_Pin         GPIO_PIN_6

/*
 * Sebagian modul relay active-low.
 * 1 = relay aktif ketika GPIO HIGH
 * 0 = relay aktif ketika GPIO LOW
 */
#define RELAY_ACTIVE_HIGH     1U

/* MCP4725 DAC — A0=GND → 0x60 */
#define MCP4725_ADDR    (0x60 << 1)

/* GY-LSM6DS3 — Dual IMU, share I2C1 (PB8=SCL, PB9=SDA) */
#define LSM6DS3_ADDR_A  (0x6A << 1)   /* SDO=GND — proksimal */
#define LSM6DS3_ADDR_B  (0x6B << 1)   /* SDO=VCC — distal    */
#define LSM6DS3_ALPHA   0.98f         /* Complementary filter coeff */

/* EMG threshold dan target */
#define EMG_THRESHOLD_MV    30.0f
#define EMG_MAX_LEVEL_MV   500.0f
#define EMG_MAX_TARGET_DEG  90.0f

/* Range parameter stimulasi */
#define PW_INITIAL_US   250.0f
#define PW_MIN_US        50.0f
#define PW_MAX_US       500.0f
#define FREQ_MIN_HZ      10.0f
#define FREQ_MAX_HZ      80.0f
#define I_MIN_MA          0.0f
#define I_MAX_MA         30.0f
#define DEAD_TIME_US     200U

/* =============================================
 * FUZZY TEST MODE
 * 1 = fuzzy berjalan, H-Bridge dan DAC tidak digunakan
 * 0 = operasi normal
 * ============================================= */
#define FUZZY_TEST_ONLY    0U


/* Hardware CCS */
#define RSENSE_OHM     82.0f
#define DAC_VREF         3.3f
#define DAC_RES       4095.0f

/* Sampling period kontrol loop */
#define TS_MS           10U

/* =============================================
 * FUZZY PW INCREMENTAL (v4)
 * u[k] = u[k-1] + K * fuzzy_pw(e, de)
 *
 * fuzzy_pw() mengeluarkan DELTA ternormalisasi (-4 .. +4),
 * bukan PW absolut. Integrator ada di fuzzy_pw.c.
 * ============================================= */

/* ---- Nilai awal mode AUTO (di-set operator sebelum START) ---- */
#define PW_INIT_DEFAULT_US     PW_INITIAL_US   /* 250 us  */
#define I_INIT_DEFAULT_MA          10.0f        /* 0 .. I_MAX_MA (30 mA)   */
#define FREQ_INIT_DEFAULT_HZ       35.0f        /* 10 .. FREQ_MAX_HZ (80)  */

/* ---- Batas atas integrator ----
 * PW_MAX_US = 500 us, tetapi SPEC 12 membatasi operasi normal 400 us.
 * Nilai terkecil dari keduanya yang dipakai sebagai limit integrator.  */
#define PW_INCR_HI_US            400.0f
#define PW_INCR_LO_US            PW_MIN_US     /* 50 us */

/* ---- K : us yang ditambahkan per 1 unit output fuzzy per tick TS_MS ----
 * Laju ramp = K * 4 * (1000 / TS_MS) us/detik.
 * TS_MS = 10  ->  laju = 400 * K  us/detik.
 *
 *   K = 0.05  ->   20 us/s   (250 -> 400 us dalam 7.5 s)  sangat halus
 *   K = 0.10  ->   40 us/s   (250 -> 400 us dalam 3.8 s)  DEFAULT
 *   K = 0.25  ->  100 us/s   (250 -> 400 us dalam 1.5 s)  agresif
 *   K = 0.50  ->  200 us/s                                uji bangku saja
 */
#define PW_INCR_GAIN_DEFAULT      0.10f
#define PWM_INCR_GAIN_DEFAULT     PW_INCR_GAIN_DEFAULT

/* ---- Slew limit per tick — jaring pengaman kalau K salah set via GUI ---- */
#define PW_INCR_MAX_STEP_US       2.0f         /* maks 200 us/s pada TS=10 ms */
#define PWM_INCR_MAX_STEP_US      PW_INCR_MAX_STEP_US

/* ---- Skala Δe ke semesta fuzzy ±4 ----
 * TS_MS = 10 ms, gerak sendi FES ~30-60 deg/s -> Δe hanya 0.3-0.6 deg/tick,
 * sehingga tanpa penskalaan Δe selalu jatuh di ZE dan aksi derivatif mati.
 * Aturan tuning: gain ≈ 4 / max|g_delta_error| hasil rekaman.
 *   gain = 3.0  ->  1.33 deg/tick (133 deg/s) sudah menyentuh PB
 */
#define FUZZY_DE_GAIN_DEFAULT      3.0f

/* ---- Low-pass Δe (0 = mati, 0.2-0.4 disarankan) ----
 * Menekan derau complementary filter yang ikut terkuatkan FUZZY_DE_GAIN. */
/* ---- Low-pass Δe (nilai awal, bisa diubah runtime lewat g_de_lpf_alpha) ----
 * Menekan derau complementary filter yang ikut terkuatkan FUZZY_DE_GAIN.
 * alpha = 1.0  -> filter MATI (Δe diteruskan apa adanya)
 * alpha = 0.3  -> disarankan
 * alpha = 0.1  -> sangat halus, tapi menambah lag ~90 ms
 * JANGAN dipakai di dalam #if — ini konstanta float.                       */
#define DE_LPF_ALPHA_DEFAULT       0.3f

/* ---- Deadband update H-Bridge, hindari SetParams tiap tick ---- */
#define PW_UPDATE_DEADBAND_US     1.0f

/* ---- Dokumentasi / Live Expression saja ---- */
#define PW_RAMP_US_PER_S \
        (PW_INCR_GAIN_DEFAULT * 4.0f * (1000.0f / (float)TS_MS))

#endif /* STIM4_CONFIG_H */
