# Write your code here :-)
# Ctrl-I for Co-Pilot
import network
import urequests
import time
from machine import Pin, PWM, deepsleep
from bb_secret import Secrets

class BabyBuddyFeaturesEnum:
    TUMMY_START = 'TUMMY_START'
    TUMMY_END = 'TUMMY_END'
    SLEEP_START = 'SLEEP_START'
    SLEEP_END = 'SLEEP_END'
    DIAPER_SOLID = 'DIAPER_DRY'
    DIAPER_WET = 'DIAPER_WET'
    FEED_START = 'FEED_START'
    FEED_BOTTLE_MILK = 'FEED_BOTTLE_MILK'
    FEED_BOTTLE_FORMULA = 'FEED_BOTTLE_FORMULA'
    FEED_BREAST_LEFT = 'FEED_BREAST_LEFT'
    FEED_BREAST_RIGHT = 'FEED_BREAST_RIGHT'



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
        self.play_tone(1109, 1500)

    def chime_ok(self):
        # A, A
        self.play_tone(880, 250)
        time.sleep_ms(100)
        self.play_tone(880, 250)


class BabyBuddyApiClient:
    def __init__(self, pin_assignments, buzzer_pin_num):
        # === Button Setup ===
        self.buttons = {}
        self.button_last_press_time = {}
        for func, pin_num in pin_assignments.items():
            self.buttons[func] = Pin(pin_num, Pin.IN, Pin.PULL_UP)
            self.button_last_press_time[func] = 0
        self.buzzer = Buzzer(PWM(Pin(buzzer_pin_num)))
        self.debounce_ms = 300

    def run(self):
        self.connect_wifi()
        loop_start = time.ticks_ms()

        while True:
            # Go to sleep if nothing has happened in 30 seconds
            if time.ticks_ms() - loop_start > 30000:
                print("Going to sleep")
                time.sleep(1)
                deepsleep()

            # Look for button presses
            pressed = self.get_pressed_buttons()
            if len(pressed) == 0:
                time.sleep(0.05)
                continue

            # Small pause and get pressed buttons again in case multiple buttons pressed
            time.sleep(0.05)
            pressed = pressed.union(self.get_pressed_buttons())

            print(f"Pressed: '{pressed}'")
            self.buzzer.play_tone(1760, 250) # A6

            try:
                # -- Diapers
                if BabyBuddyFeaturesEnum.DIAPER_SOLID in pressed and BabyBuddyFeaturesEnum.DIAPER_WET in pressed:
                    self.log_diaper(wet=True, solid=True)
                elif BabyBuddyFeaturesEnum.DIAPER_WET in pressed:
                    self.log_diaper(wet=True, solid=False)
                elif BabyBuddyFeaturesEnum.DIAPER_SOLID in pressed:
                    self.log_diaper(wet=False, solid=True)
                # -- Feeding
                elif BabyBuddyFeaturesEnum.FEED_START in pressed:
                    self.start_timer("feeding")
                elif BabyBuddyFeaturesEnum.FEED_BREAST_LEFT in pressed and BabyBuddyFeaturesEnum.FEED_BREAST_RIGHT in pressed:
                    self.end_feeding("both breasts", "breast milk")
                elif BabyBuddyFeaturesEnum.FEED_BREAST_LEFT in pressed:
                    self.end_feeding("left breast", "breast milk")
                elif BabyBuddyFeaturesEnum.FEED_BREAST_RIGHT in pressed:
                    self.end_feeding("right breast", "breast milk")
                elif BabyBuddyFeaturesEnum.FEED_BOTTLE_MILK in pressed:
                    self.end_feeding("bottle", "breast milk")
                elif BabyBuddyFeaturesEnum.FEED_BOTTLE_FORMULA in pressed:
                    self.end_feeding("bottle", "formula")
                # -- Sleep
                elif BabyBuddyFeaturesEnum.SLEEP_START in pressed:
                    self.start_timer("sleep")
                elif BabyBuddyFeaturesEnum.SLEEP_END in pressed:
                    self.end_sleep()
                # -- Tummytime
                elif BabyBuddyFeaturesEnum.TUMMY_START in pressed:
                    self.start_timer("tummy_time")
                elif BabyBuddyFeaturesEnum.TUMMY_END in pressed:
                    self.end_tummy_time()
                else:
                    raise Exception(f"Unexpected buttons pressed: {pressed}")
            except Exception as ex:
                print(f"Error evaluating {pressed}:\n  {ex}")
                self.buzzer.chime_error()


            now = time.ticks_ms()
            for func in pressed:
                self.button_last_press_time[func] = now



    def get_pressed_buttons(self):
        now = time.ticks_ms()
        pressed = set()
        for func, pin in self.buttons.items():
                if not pin.value() and time.ticks_diff(now, self.button_last_press_time[func]) > self.debounce_ms:
                    pressed.add(func)
        return pressed
    def end_feeding(self, method, type):
        # method: 'left breast' | 'right breast' | 'both breasts' | 'bottle'
        # type: 'breast milk' | 'formula'

        timer = self.find_or_create_timer("feeding")

        # Log via a timer
        self.post("/feedings/", {
                "timer": timer['id'],
                'type': type,
                'method': method,
            })
        self.buzzer.chime_ok()

    def end_sleep(self):
        timer = self.find_or_create_timer("sleep")

        # Log via a timer
        self.post("/sleep/", {
                "timer": timer['id'],
            })
        self.buzzer.chime_ok()

    def end_tummy_time(self):
        timer = self.find_or_create_timer("tummy_time")

        # Log via a timer
        self.post("/tummy-times/", {
                "timer": timer['id'],
            })
        self.buzzer.chime_ok()


    def start_timer(self, timer_name, chime_ok=True) -> dict:
        data = {
            "child": Secrets.CHILD_ID,
            "name": timer_name,
        }
        result = self.post("/timers/", data)
        if result and "id" in result:
            print(f"'{timer_name}' timer started (ID {result['id']})")
            if chime_ok:
                self.buzzer.chime_ok()
            return result
        else:
            raise Exception("Timer not created successfully")

    def find_or_create_timer(self, timer_name):
        """Find a timer by name, or create a new one.
        Creates a new one because we don't have a real time clock so we don't know the time.
        """
        timers = self.get("/timers/")
        feeding_timer = [x for x in timers['results'] if x['name']==timer_name]
        if len(feeding_timer) == 0:
            # Forgot to start feeding, create a timer real quick so we can provide it as an input
            return self.start_timer("feeding", False)
        elif len(feeding_timer) == 1:
            return feeding_timer[0]
        else:
            raise Exception(f"Found {len(feeding_timer)} feeding timers")

    def log_diaper(self, wet: bool, solid: bool):
        data = {
            "child": Secrets.CHILD_ID,
            "wet": wet,
            "solid": solid
        }
        self.post("/changes/", data)
        self.buzzer.chime_ok()

    def connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print("Connecting to Wi-Fi...")
            wlan.connect(Secrets.SSID, Secrets.PASSWORD)
            while not wlan.isconnected():
                time.sleep(0.5)
        print("Connected:", wlan.ifconfig())
        time.sleep(0.1)
        self.buzzer.chime_welcome()

    def post(self, endpoint, data):
        try:
            url = Secrets.BABYBUDDY_URL + endpoint
            print(f"POST {url} → {data}")
            r = urequests.post(url, headers=Secrets.HEADERS, json=data)
            res = r.json()
            r.close()
            print(f"  → {res}")
            if r.status_code not in (200, 201):
                raise Exception(f"HTTP Error {r.status_code}")
            return res
        except Exception as e:
            print("HTTP Error:", e)
            self.buzzer.chime_error()
            raise e

    def get(self, endpoint):
        try:
            url = Secrets.BABYBUDDY_URL + endpoint
            print(f"GET {url}")
            r = urequests.get(url, headers=Secrets.HEADERS)
            res = r.json()
            r.close()
            print(f"  → {res}")
            return res
        except Exception as e:
            print("HTTP Error:", e)
            self.buzzer.chime_error()
            return None


pin_assignments = {
    BabyBuddyFeaturesEnum.FEED_START: 33,
    BabyBuddyFeaturesEnum.FEED_BREAST_LEFT: 23,
    BabyBuddyFeaturesEnum.FEED_BREAST_RIGHT: 32,
    BabyBuddyFeaturesEnum.FEED_BOTTLE_MILK: 22,
    BabyBuddyFeaturesEnum.FEED_BOTTLE_FORMULA: 25,
    BabyBuddyFeaturesEnum.DIAPER_SOLID: 19,
    BabyBuddyFeaturesEnum.DIAPER_WET: 26,
    BabyBuddyFeaturesEnum.SLEEP_START: 18,
    BabyBuddyFeaturesEnum.SLEEP_END: 27,
    BabyBuddyFeaturesEnum.TUMMY_START: 5,
    BabyBuddyFeaturesEnum.TUMMY_END: 14,
}
BabyBuddyApiClient(pin_assignments=pin_assignments, buzzer_pin_num=13).run()
