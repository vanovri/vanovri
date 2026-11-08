#include "lsm6ds3.h"
#include <math.h>

extern I2C_HandleTypeDef hi2c1;

static HAL_StatusTypeDef wreg(uint16_t addr, uint8_t reg, uint8_t val) {
    uint8_t b[2]={reg,val};
    return HAL_I2C_Master_Transmit(&hi2c1, addr, b, 2, 10);
}
static HAL_StatusTypeDef rregs(uint16_t addr, uint8_t reg, uint8_t *buf, uint16_t n) {
    HAL_StatusTypeDef s;
    s=HAL_I2C_Master_Transmit(&hi2c1, addr, &reg, 1, 10);
    if (s!=HAL_OK) return s;
    return HAL_I2C_Master_Receive(&hi2c1, addr, buf, n, 10);
}

HAL_StatusTypeDef LSM6DS3_Init(LSM6DS3_Handle *h) {
    uint8_t id=0; HAL_StatusTypeDef s;
    h->ready=0; h->cf_state=0.0f; h->angle=0.0f;
    s=rregs(h->i2c_addr, LSM6DS3_REG_WHO_AM_I, &id, 1);
    if (s!=HAL_OK || id!=0x69) return HAL_ERROR;
    s=wreg(h->i2c_addr, LSM6DS3_REG_CTRL1_XL, 0x40); if (s!=HAL_OK) return s;
    s=wreg(h->i2c_addr, LSM6DS3_REG_CTRL2_G,  0x40); if (s!=HAL_OK) return s;
    s=wreg(h->i2c_addr, LSM6DS3_REG_CTRL3_C,  0x44); if (s!=HAL_OK) return s;
    h->ready=1;
    return HAL_OK;
}

HAL_StatusTypeDef LSM6DS3_Read(LSM6DS3_Handle *h) {
    uint8_t buf[12]; HAL_StatusTypeDef s;
    if (!h->ready) return HAL_ERROR;
    s=rregs(h->i2c_addr, LSM6DS3_REG_OUTX_L_G, buf, 12);
    if (s!=HAL_OK) return s;

    int16_t gx_raw=(int16_t)((buf[1] <<8)|buf[2]);
    int16_t ax_raw=(int16_t)((buf[7] <<8)|buf[6]);
    int16_t ay_raw=(int16_t)((buf[9] <<8)|buf[8]);
    int16_t az_raw=(int16_t)((buf[11]<<8)|buf[10]);

    float gx=(float)gx_raw*LSM6DS3_GYRO_SENS;
    float ax=(float)ax_raw*LSM6DS3_ACCEL_SENS;
    float ay=(float)ay_raw*LSM6DS3_ACCEL_SENS;
    float az=(float)az_raw*LSM6DS3_ACCEL_SENS;

    float angle_accel=atan2f(ay, sqrtf(ax*ax+az*az))*(180.0f/3.14159265f);
    float dt=(float)TS_MS/1000.0f;
    h->cf_state = LSM6DS3_ALPHA*(h->cf_state+gx*dt)+(1.0f-LSM6DS3_ALPHA)*angle_accel;
    h->angle    = h->cf_state;
    h->gyro_dps = gx;
    h->accel_g  = sqrtf(ax*ax+ay*ay+az*az);
    return HAL_OK;
}

void LSM6DS3_ResetFilter(LSM6DS3_Handle *h) { h->cf_state=0.0f; h->angle=0.0f; }
