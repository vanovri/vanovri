#ifndef LSM6DS3_H
#define LSM6DS3_H

#include "main.h"
#include "stim4_config.h"

/* Register map */
#define LSM6DS3_REG_WHO_AM_I   0x0F
#define LSM6DS3_REG_CTRL1_XL   0x10
#define LSM6DS3_REG_CTRL2_G    0x11
#define LSM6DS3_REG_CTRL3_C    0x12
#define LSM6DS3_REG_OUTX_L_G   0x22
#define LSM6DS3_REG_OUTX_L_XL  0x28

/* Sensitivitas */
#define LSM6DS3_GYRO_SENS   0.00875f    /* dps/LSB — FS=±245dps */
#define LSM6DS3_ACCEL_SENS  0.000061f   /* g/LSB   — FS=±2g     */

typedef struct {
    uint16_t  i2c_addr;  /* LSM6DS3_ADDR_A atau LSM6DS3_ADDR_B */
    float     angle;     /* Sudut terfilter (°)                 */
    float     gyro_dps;  /* Kecepatan angular (dps)             */
    float     accel_g;   /* Magnitudo akselerasi (g)            */
    float     cf_state;  /* State internal complementary filter */
    uint8_t   ready;     /* 1 = init OK, 0 = error              */
} LSM6DS3_Handle;

HAL_StatusTypeDef LSM6DS3_Init(LSM6DS3_Handle *h);
HAL_StatusTypeDef LSM6DS3_Read(LSM6DS3_Handle *h);
void              LSM6DS3_ResetFilter(LSM6DS3_Handle *h);

#endif /* LSM6DS3_H */
