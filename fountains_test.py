from machine import Pin, PWM
import time

a_in_1 = Pin(10, Pin.OUT)
a_in_2 = Pin(11, Pin.OUT)
b_in_1 = Pin(12, Pin.OUT)
b_in_2 = Pin(13, Pin.OUT)

button = Pin(14, Pin.IN, Pin.PULL_DOWN)

FULL = 65535
HALF = 55000
OFF = 0

FREQ = 15_000
pwm_a = PWM(a_in_1, freq=FREQ, duty_u16=0)
pwm_b = PWM(b_in_1, freq=FREQ, duty_u16=0)

dance = (
    (OFF, HALF),
    (FULL, OFF),
    (HALF, FULL),
    (FULL, HALF),
    (OFF, FULL),
    (HALF, OFF),
    
    (FULL, FULL),
    (HALF, FULL),    
    (FULL, FULL),
    (FULL, HALF),
    (FULL, FULL),
    
    (HALF, FULL),
    (FULL, HALF),
    (HALF, FULL),
    (FULL, HALF),
    
    (FULL, FULL),
)

def do_the_dance():
    step = 0
    while True:
        if button.value():
            break
        pwm_a.duty_u16(dance[step][0])
        pwm_b.duty_u16(dance[step][1])
        time.sleep(1)
        step = (step + 1) % len(dance)
    pwm_a.duty_u16(0)
    pwm_b.duty_u16(0)

