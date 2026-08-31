#pragma once

/* Plant state observed by the LTL monitor. */
extern int temperature;    /* degrees C, from the thermocouple ADC  */
extern int pressure;       /* bar, from the pressure transducer ADC */
extern int heater_on;      /* switch driving the heater             */
extern int valve_open;     /* DAC driving the pump/valve            */
extern int fresh_sample;   /* T/P have handed data to S             */
extern int displayed;      /* S has written the screen              */
