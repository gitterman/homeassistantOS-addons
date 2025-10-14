#!/usr/bin/env python3
import pigpio
import time
import os
import shutil

GPIO_PIN        = 18
PWM_FREQ        = 25000            # 25 kHz for smooth fan PWM
targetTEMP      = 55.0             # Target temperature in °C
minPWM          = 30               # Minimum fan duty cycle in %
UPDATE_INTERVAL = 10               # seconds
MAX_LOG_SIZE    = 5 * 1024 * 1024  # 5 MB
LOG_PATH        = "/config/fan_daemon.log"

# PI controller constants (tune these!)
pTemp = 10.0    # Proportional gain
iTemp = 0.5     # Integral gain

integral_sum = 0.0

def rotate_log():
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_LOG_SIZE:
        try:
            if os.path.exists(LOG_PATH + ".1"):
                os.remove(LOG_PATH + ".1")
            shutil.move(LOG_PATH, LOG_PATH + ".1")
        except Exception as e:
            print(f"Log rotation failed: {e}")

def log(message):
    rotate_log()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def read_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000.0
    except Exception:
        return 0

def set_fan_speed(pi, gpio_pin, percent):
    percent = max(0, min(percent, 100))
    duty = int(percent / 100 * 1_000_000)  # Scale to pigpio hardware_PWM duty cycle range
    pi.hardware_PWM(gpio_pin, PWM_FREQ, duty)
    log(f"Set fan speed to {percent:.1f}% (duty={duty}/1_000_000)")

def main():
    global integral_sum

    pi = pigpio.pi('localhost', 8888)
    if not pi.connected:
        raise SystemExit("Cannot connect to pigpiod")

    log("Fan daemon started")

    try:
        while True:
            temp = read_temp()
            error = temp - targetTEMP
            integral_sum += error * UPDATE_INTERVAL

            # PI controller output
            output = pTemp * error + iTemp * integral_sum

            # Clamp output to 0-100%
            if temp < 40:
                # No need for fan, reset integral sum to avoid windup
                percent = 0
                integral_sum = 0
            elif temp >= 70:
                percent = 100
            else:
                # Enforce minimum PWM to keep fan spinning
                percent = max(minPWM, min(output, 100))

            set_fan_speed(pi, GPIO_PIN, percent)
            log(f"Temperature: {temp:.1f}°C → Fan: {percent:.1f}%")

            time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        set_fan_speed(pi, GPIO_PIN, 0)
        pi.stop()
        log("Fan daemon stopped")

if __name__ == "__main__":
    main()

