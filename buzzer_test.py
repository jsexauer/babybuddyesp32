from machine import Pin, PWM
import time




class Buzzer:
    def __init__(self, buzzer_pin):
        self.buzzer_pin = buzzer_pin

    def play_tone(self, frequency=1000, duration_ms=500):
        self.buzzer_pin.freq(frequency)     # Set frequency in Hz
        self.buzzer_pin.duty(512)           # 50% duty cycle (range is 0–1023)
        time.sleep_ms(duration_ms)
        self.buzzer_pin.duty(0)             # Turn off

    def chime_welcome(self):
        # G, G#, A#
        self.play_tone(1568)
        self.play_tone(1661)
        self.play_tone(1865)

    def chime_error(self):
        # D, Db
        self.play_tone(1174)
        self.play_tone(1109, 1000)

    def chime_ok(self):
        # A, A
        self.play_tone(880, 250)
        time.sleep_ms(100)
        self.play_tone(880, 250)


buzzer = Buzzer(PWM(Pin(23)))
buzzer.chime_welcome()
time.sleep_ms(2000)
buzzer.chime_error()
time.sleep_ms(2000)
buzzer.chime_ok()
print("done.")


