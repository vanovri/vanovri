#include "stm32f4xx.h"

#if !defined(HSE_VALUE)
  #define HSE_VALUE    ((uint32_t)25000000)
#endif

uint32_t SystemCoreClock = 84000000;

const uint8_t AHBPrescTable[16] = {0,0,0,0,0,0,0,0,1,2,3,4,6,7,8,9};
const uint8_t APBPrescTable[8]  = {0,0,0,0,1,2,3,4};

void SystemInit(void)
{
#if (__FPU_PRESENT==1) && (__FPU_USED==1)
    SCB->CPACR |= ((3UL<<10*2)|(3UL<<11*2));
#endif
    RCC->CR     |= (uint32_t)0x00000001;
    RCC->CFGR    = 0x00000000;
    RCC->CR     &= (uint32_t)0xFEF6FFFF;
    RCC->PLLCFGR = 0x24003010;
    RCC->CR     &= (uint32_t)0xFFFBFFFF;
    RCC->CIR     = 0x00000000;
    SCB->VTOR    = FLASH_BASE | 0x00000000;
}

void SystemCoreClockUpdate(void) { SystemCoreClock = 84000000; }
