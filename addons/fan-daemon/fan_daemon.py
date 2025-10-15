import pigpio
import time
import os
import json
import signal

# ---------- Load options from the options.json file Home Assistant injects into the container ----------
try:
    with open( "/data/options.json", "r" ) as f:
        options = json.load( f )
except Exception as e:
    print( f"Failed to load /data/options.json: {e}" )
    exit( 1 )

# ---------- Read configuration from add-on options or set defaults ----------
pigpio_host     =        options.get('pigpio_addr', 'localhost')       # Ensure pigpiod is running on localhost
pigpio_port     =   int( options.get('pigpio_port', 8888 ) )           # Default pigpio port

GPIO_PIN        =   int( options.get('gpio_pin',        18   ) )       # GPIO pin to control fan (PWM)
PWM_FREQ        =   int( options.get('pwm_freq',        50   ) )       # 50 Hz for MOSFET PWM
targetTEMP      = float( options.get('target_temp',     55.0 ) )       # Target temperature in °C
minTEMP         = float( options.get('min_temp',        50.0 ) )       # Min temp for fan off
maxTEMP         = float( options.get('max_temp',        75.0 ) )       # Max temp for 100% fan speed
minPWM          =   int( options.get('min_pwm',         30   ) )       # Min fan duty cycle in %
UPDATE_INTERVAL =   int( options.get('update_interval', 10   ) )       # Update interval in seconds
pTemp           = float( options.get('pTemp',           10.0 ) )       # Proportional gain 
iTemp           = float( options.get('iTemp',            0.4 ) )       # Integral gain

def log( message ):
    timestamp = time.strftime( "%Y-%m-%d %H:%M:%S" )
    print(f"[{timestamp}] {message}", flush=True)

def read_temp():
    try:
        with open( "/sys/class/thermal/thermal_zone0/temp" ) as f:
            return( int( f.read() ) / 1000.0 )
    except Exception as e:
        log( f"failed to read temperature: {e}" )
        return( 0 )

def set_fan_speed( pi, gpio_pin, percent ):
    """set the fan speed using hardware PWM"""
    percent = max( 0, min(percent, 100) )  # Ensure it's between 0 and 100
    duty    = int( percent / 100 * 1_000_000 )
    pi.hardware_PWM( gpio_pin, PWM_FREQ, duty )

def main():
    log( f"connecting to pigpiod at {pigpio_host}:{pigpio_port}" )
    pi = pigpio.pi( pigpio_host, pigpio_port )
    if not pi.connected:
        raise SystemExit( "could not connect to pigpiod" )

    log( "fan daemon started" )
    stop_requested = False
    integral_sum    = 0 

    def handle_sigterm( signum, frame ):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        while not stop_requested:
            temp          = read_temp()
            error         = temp - targetTEMP
            integral_sum += error * UPDATE_INTERVAL
            output        = pTemp * error + iTemp * integral_sum  # P-I controller output

            if( temp < minTEMP):                                  # clamp output
                percent      =   0                                # no need for fan
                integral_sum =   0                                # reset integral avoids windup
            elif( temp >= maxTEMP ):
                percent      = 100                                # no need for fan
            else:
                percent = max( minPWM, min( output, 100 ) )       # enforce minimum PWM to keep fan spinning

            set_fan_speed( pi, GPIO_PIN, percent )
            log( f"temperature: {temp:.1f}°C → fan: {percent:.1f}%" )
            time.sleep( UPDATE_INTERVAL )
    except KeyboardInterrupt:
        pass
    finally:
        set_fan_speed( pi, GPIO_PIN, 0 )
        pi.stop()
        log( "fan daemon stopped" )

if __name__ == "__main__":
    main()

