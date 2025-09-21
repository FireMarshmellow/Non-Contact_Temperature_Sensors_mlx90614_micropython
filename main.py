from machine import I2C, Pin
import time

MLX_ADDR     = 0x5A
REG_TA       = 0x06   # ambient
REG_TOBJ1    = 0x07   # object (most breakouts wire TOBJ1)

# SMBus CRC-8 (PEC) with polynomial 0x07
def crc8_pec(bytes_iter):
    crc = 0
    for b in bytes_iter:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=100_000)  # MLX90614 prefers 100 kHz
time.sleep_ms(300)  # small settle after power-up

def read_word_with_pec(reg):
    # Read 3 bytes: LSB, MSB, PEC
    data = i2c.readfrom_mem(MLX_ADDR, reg, 3)
    lsb, msb, pec = data[0], data[1], data[2]
    raw = (msb << 8) | lsb

    # Compute expected PEC over: [addr_write, command, addr_read, LSB, MSB]
    addr_w = (MLX_ADDR << 1) | 0
    addr_r = (MLX_ADDR << 1) | 1
    expected = crc8_pec([addr_w, reg, addr_r, lsb, msb])

    # Basic sanity checks
    if raw in (0x0000, 0xFFFF) or pec != expected:
        return None  # bad read

    return raw

def raw_to_c(raw):
    # per datasheet: Kelvin = raw * 0.02; then to °C
    return raw * 0.02 - 273.15

while True:
    ta_raw = read_word_with_pec(REG_TA)
    to_raw = read_word_with_pec(REG_TOBJ1)
    if ta_raw is None or to_raw is None:
        print("Bad read (retrying) …")
    else:
        print("Ambient:", round(raw_to_c(ta_raw), 2), "°C")
        print("Object :", round(raw_to_c(to_raw), 2), "°C")
    time.sleep(0.5)