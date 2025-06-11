import network
import urequests
import time
from machine import Pin, PWM
from utime import localtime

# === Wi-Fi Credentials ===
SSID = "the_lan_before_time"
PASSWORD = "sphericalpolyhedraiceclimbers8"

# === BabyBuddy API Info ===
BABYBUDDY_URL = "https://genericlifeform.pythonanywhere.com/api"
API_TOKEN = "2eda25d011e5c68e2edacd4bf76fb26af93dc4ee"
CHILD_ID = 1  # Update if needed

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}


# === Button Pins ===
BUTTON_PINS = {
    "wet": 21,
    "solid": 22,
    "feeding": 19,
    "sleep": 18,
    "tummy": 17
}

# === Timer State ===
active_timers = {
    "feeding": None,
    "sleep": None,
    "tummy": None
}

# === Debounce ===
DEBOUNCE_MS = 300
last_press_time = {k: 0 for k in BUTTON_PINS}


# Setup buzzer on GPIO 21
buzzer = PWM(Pin(23))

# Function to play a tone
def beep(frequency=1000, duration_ms=500):
    buzzer.freq(frequency)     # Set frequency in Hz
    buzzer.duty(512)           # 50% duty cycle (range is 0–1023)
    time.sleep_ms(duration_ms)
    buzzer.duty(0)             # Turn off

# === Helper Functions ===

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Connected:", wlan.ifconfig())

def post(endpoint, data):
    try:
        url = BABYBUDDY_URL + endpoint
        print(f"POST {url} → {data}")
        r = urequests.post(url, headers=HEADERS, json=data)
        res = r.json()
        r.close()
        return res
    except Exception as e:
        print("HTTP Error:", e)
        return None

def log_diaper(wet, solid):
    data = {
        "child": CHILD_ID,
        "wet": wet,
        "solid": solid
    }
    post("/changes/", data)

def start_timer(name):
    data = {
        "child": CHILD_ID,
        "name": name,
    }
    result = post("/timers/", data)
    if result and "id" in result:
        active_timers[name] = result["id"]
        print(f"{name} timer started (ID {result['id']})")

def stop_timer(name, endpoint):
    timer_id = active_timers[name]
    if timer_id:
        result = post(endpoint, {"timer": timer_id})
        if result:
            print(result)
            print(f"{name} timer stopped and logged.")
        active_timers[name] = None

def toggle_timer(name, endpoint):
    beep()
    if active_timers[name] is None:
        start_timer(name)
    else:
        stop_timer(name, endpoint)


def end_feeding():
    method = "left brest" "right brest" "both brests" "bottle"
    type = "breast milk" "formula"
# === Button Setup ===
buttons = {}
for name, pin in BUTTON_PINS.items():
    buttons[name] = Pin(pin, Pin.IN, Pin.PULL_UP)

# === Main Logic ===
connect_wifi()
print("System ready.")

while True:
    now = time.ticks_ms()

    for name, pin in buttons.items():
        if not pin.value():
            if time.ticks_diff(now, last_press_time[name]) > DEBOUNCE_MS:
                print(f"Button '{name}' pressed")

                if name == "wet":
                    log_diaper(wet=True, solid=False)
                elif name == "solid":
                    log_diaper(wet=False, solid=True)
                elif name == "feeding":
                    toggle_timer("feeding", "/feedings/")
                elif name == "sleep":
                    toggle_timer("sleep", "/sleep/")
                elif name == "tummy":
                    toggle_timer("tummy", "/tummy-times/")

                last_press_time[name] = now

    time.sleep(0.05)
