# 🌀 Fan Daemon Add-on for Home Assistant

This Home Assistant add-on controls a fan connected to a Raspberry Pi using PWM via the `pigpio` daemon.  
It adjusts fan speed based on CPU temperature to provide quiet and efficient cooling.

---

## 🔧 Features

- Connects to a running `pigpiod` daemon (remote or local)
- Uses hardware PWM for smooth fan control
- Fully configurable via add-on settings
- Automatically adjusts fan speed based on system temperature
- Runs as a background service on Home Assistant OS

---

## 📦 Requirements

- A Raspberry Pi running Home Assistant OS
- A fan connected to a GPIO pin via transistor/MOSFET (not directly!)
- The `pigpiod` daemon running (e.g., via the `pigpiod` add-on)
- This add-on installed from GitHub

---

## ⚙️ Configuration

This add-on can be configured via the Home Assistant UI or by editing the add-on's options.

### Example configuration:

```yaml
pigpio_addr: "192.168.1.100"  # IP address of the host running pigpiod
