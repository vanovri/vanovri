#ifndef FUZZY_CURRENT_H
#define FUZZY_CURRENT_H

/* Fuzzy Sugeno 5x5 — Arus Stimulasi (mA)
 * Input 1: Magnitude error sudut   0° hingga 180°
 * Input 2: Delta error sudut      -90° hingga +90°
 * Output : Arus target             0mA hingga 30mA */

float fuzzy_current(float error_magnitude, float delta_error_deg);
float auto_frequency(float error_magnitude);

#endif
