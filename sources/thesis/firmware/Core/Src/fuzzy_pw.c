#include "fuzzy_pw.h"
#include "stim4_config.h"
#include <stdint.h>
#define NB 0
#define NS 1
#define ZE 2
#define PS 3
#define PB 4
static const float singleton[5] = {-4.0f,-2.0f,0.0f,2.0f,4.0f};
static const uint8_t rule_base[5][5] = {
 {0,0,0,1,2},{0,1,1,2,3},{1,2,2,2,3},{2,3,3,4,4},{3,4,4,4,4}
};
static float trimf(float x,float a,float b,float c){if(x<=a||x>=c)return 0.0f;if(x<b)return(x-a)/(b-a);if(x>b)return(c-x)/(c-b);return 1.0f;}
static float trapmf_L(float x,float b,float c){if(x<=b)return 1.0f;if(x>=c)return 0.0f;return(c-x)/(c-b);}
static float trapmf_R(float x,float a,float b){if(x>=b)return 1.0f;if(x<=a)return 0.0f;return(x-a)/(b-a);}
static void fuzz_error(float e,float mu[5]){mu[NB]=trapmf_L(e,-45,-30);mu[NS]=trimf(e,-40,-20,0);mu[ZE]=trimf(e,-10,0,10);mu[PS]=trimf(e,0,20,40);mu[PB]=trapmf_R(e,30,45);}
static void fuzz_derror(float de,float mu[5]){mu[NB]=trapmf_L(de,-4,-2);mu[NS]=trimf(de,-4,-2,0);mu[ZE]=trimf(de,-1,0,1);mu[PS]=trimf(de,0,2,4);mu[PB]=trapmf_R(de,2,4);}
float fuzzy_pw(float e,float de){float me[5],md[5],num=0,den=0;if(e<-45)e=-45;if(e>45)e=45;if(de<-4)de=-4;if(de>4)de=4;fuzz_error(e,me);fuzz_derror(de,md);for(int i=0;i<5;i++)for(int j=0;j<5;j++){float f=me[i]<md[j]?me[i]:md[j];if(f>0){num+=f*singleton[rule_base[i][j]];den+=f;}}return den<1e-6f?0.0f:num/den;}
static float s_initial=0,s_value=0,s_gain=PW_INCR_GAIN_DEFAULT,s_lo=0,s_hi=400,s_delta=0;
static float clamp(float v,float lo,float hi){return v<lo?lo:v>hi?hi:v;}
static float delta(float e,float de){float d=fuzzy_pw(e,de)*s_gain;if(!(d==d))d=0;if(d>PW_INCR_MAX_STEP_US)d=PW_INCR_MAX_STEP_US;if(d<-PW_INCR_MAX_STEP_US)d=-PW_INCR_MAX_STEP_US;s_delta=d;return d;}
void FuzzyPW_Init(float initial,float gain,float lo,float hi){s_lo=lo;s_hi=hi<lo?lo:hi;s_gain=gain<0?0:gain;s_initial=clamp(initial,s_lo,s_hi);s_value=s_initial;s_delta=0;}
void FuzzyPW_Reset(void){s_value=s_initial;s_delta=0;}
float FuzzyPW_Step(float e,float de){s_value=clamp(s_value+delta(e,de),s_lo,s_hi);return s_value;}
float FuzzyPW_Hold(float e,float de){(void)e;(void)de;s_delta=0.0f;return s_value;}
void FuzzyPW_Set(float us){s_value=clamp(us,s_lo,s_hi);}
float FuzzyPW_Get(void){return s_value;}
float FuzzyPW_GetDelta(void){return s_delta;}
void FuzzyPW_SetGain(float g){s_gain=g<0?0:g;}
void FuzzyPW_SetInitial(float us){s_initial=clamp(us,s_lo,s_hi);}
void FuzzyPW_SetLimits(float lo,float hi){s_lo=lo;s_hi=hi<lo?lo:hi;s_initial=clamp(s_initial,s_lo,s_hi);s_value=clamp(s_value,s_lo,s_hi);}
