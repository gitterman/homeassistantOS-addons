import pigpio
import time
import os
import shutil

# Set environment variables for pigpio
pigpio_host =     os.getenv('PIGPIO_ADDR', 'localhost')  # Ensure pigpiod is running on localhost
pigpio_port = int(os.getenv('PIGPIO_PORT', 8888))        # Default pigpio port


# Read configuration from environment variables or set defaults
GPIO_PIN        =   int( os.environ.get( 'GPIO_PIN',        18   ) )
PWM_FREQ        =   int( os.environ.get( 'PWM_FREQ',        50   ) )  # 50 Hz for mosfet
targetTEMP      = float( os.environ.get( 'targetTEMP',      55.0 ) )  # Target temperature in °C
minTEMP         = float( os.environ.get( 'minTEMP',         50.0 ) )  # Min temp for fan off
maxTEMP         = float( os.environ.get( 'maxTEMP',         75.0 ) )  # Max temp for 100% fan speed
minPWM          =   int( os.environ.get( 'minPWM',          30   ) )  # Min fan duty cycle in %
UPDATE_INTERVAL =   int( os.environ.get( 'UPDATE_INTERVAL', 10   ) )  # seconds
MAX_LOG_SIZE    = 5 * 1024 * 1024                                     # 5 MB
LOG_PATH        = "/data/fan_daemon.log"                              # Log file path

def rotate_log():
    """rotate the log file if it exceeds MAX_LOG_SIZE"""
    if os.path.exists( LOG_PATH ) and os.path.getsize( LOG_PATH ) > MAX_LOG_SIZE:
        try:
            if os.path.exists( LOG_PATH + ".1" ):
               os.remove(      LOG_PATH + ".1" )
            shutil.move( LOG_PATH, LOG_PATH + ".1" )
        except Exception as e:
            print( f"Log rotation failed: {e}" )

def log( message ):
    """append message to the log and rotate if needed"""
    rotate_log()
    timestamp = time.strftime( "%Y-%m-%d %H:%M:%S" )
    with open( LOG_PATH, "a" ) as f:
        f.write( f"[{timestamp}] {message}\n" )

def read_temp():
    try:
        with open( "/sys/class/thermal/thermal_zone0/temp" ) as f:
            return( int(f.read()) / 1000.0 )
    except Exception:
        return( 0 )

def temp_to_percent( temp ):
    """convert temperature to fan speed percentage with min/max temperature limits"""
    if temp < minTEMP:
        return(   0 ) # Fan off if temp is lower than minTEMP
    elif temp > maxTEMP:
        return( 100 ) # Fan at 100% if temp is higher than maxTEMP
    else:
        # Linearly map the temperature between minTEMP and maxTEMP to a percentage
        return minPWM + ( temp - minTEMP ) / ( maxTEMP - minTEMP ) * ( 100 - minPWM )

def set_fan_speed( pi, gpio_pin, percent ):
    """set the fan speed using hardware PWM"""
    percent = max( 0, min(percent, 100) )  # Ensure it's between 0 and 100
    duty    = int( percent / 100 * 1_000_000 )
    pi.hardware_PWM( gpio_pin, PWM_FREQ, duty )
    log( f"Set fan speed to {percent:.1f}% (duty={duty})" )

def main():
    #pi = pigpio.pi( pigpio_host, pigpio_port )
    pi = pigpio.pi( 'localhost', 8888 )
    if not pi.connected:
        raise SystemExit( "Cannot connect to pigpiod on localhost" )

    log( "Fan daemon started" )
    try:
        while True:
            temp    = read_temp()
            percent = temp_to_percent( temp )
            set_fan_speed( pi, GPIO_PIN, percent )
            log( f"Temperature: {temp:.1f}°C → Fan: {percent:.1f}%" )
            time.sleep( UPDATE_INTERVAL )
    except KeyboardInterrupt:
        pass
    finally:
        set_fan_speed( pi, GPIO_PIN, 0 )
        pi.stop()
        log( "Fan daemon stopped" )

if __name__ == "__main__":
    main()

