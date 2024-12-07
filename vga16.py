from array import array
from machine import Pin
import random
import rp2
from rp2 import DMA
import time
import uctypes

hsync_pin = Pin(16)
vsync_pin = Pin(17)

red_pin = Pin(18)
green_pin = Pin(19)
blue_pin = Pin(20)
hi_green_pin = Pin(21)

vga_pins = (hsync_pin, vsync_pin, red_pin, green_pin, blue_pin, hi_green_pin)

button = Pin(14)


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def hsync():
    # Cycles: 1 + 1 + 6 + 32 * (30 + 1) = 1000
    pull(block)
    wrap_target()
    
    mov(x, osr)
    label("activeporch")
    jmp(x_dec, "activeporch")
    
    label("pulse")
    set(pins, 0) [31]
    set(pins, 0) [31]
    set(pins, 0) [31]
    
    label("backporch")
    set(pins, 1) [31]
    set(pins, 1) [12]
    irq(0)       [1]
    wrap()

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, sideset_init=rp2.PIO.OUT_LOW)
def vsync():
    pull(block)
    wrap_target()
    
    mov(x, osr)
    label("active")
    wait(1, irq, 0)
    irq(1)
    jmp(x_dec, "active")
    
    set(y, 9)
    label("frontporch")
    wait(1, irq, 0)
    jmp(y_dec, "frontporch")
    
    # Sync Pulse
    set(pins, 0)
    wait(1, irq, 0)
    wait(1, irq, 0)

    set(y, 31)
    label("backporch")
    wait(1, irq, 0).side(1)
    jmp(y_dec, "backporch")
    wrap()

@rp2.asm_pio(
    out_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW),
    set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW),
)
def rgb():
    pull(block)
    mov(y, osr)
    wrap_target()
    
    set(pins, 0)
    mov(x, y)
    
    wait(1, irq, 1)[3]
    
    label("colorout")
    pull(block)
    out(pins, 4) [4]
    out(pins, 4) [2]
    jmp(x_dec, "colorout")
    
    wrap()


framebuf = bytearray(320 * 480)
framebuf_ptr = array("I", [uctypes.addressof(framebuf)])

# Start the StateMachines.

hsync_sm = vsync_sm = rgb_sm = None
rgb_tx = rgb_reset = None

def start_vga():
    global rgb_tx, rgb_reset, hsync_sm, vsync_sm, rgb_sm
    print("Starting VGA")
    # Create the StateMachine with the hsync program, outputting on the HSync Pin.
    hsync_sm = rp2.StateMachine(0, hsync, freq=25_000_000, set_base=hsync_pin)

    # Set the horizontal resolution (640) + front porch (16) = 656
    # Subtract one for the mov.
    hsync_sm.put(655)

    vsync_sm = rp2.StateMachine(1, vsync, freq=25_000_000,
                                set_base=vsync_pin,
                                sideset_base=vsync_pin)

    # Set the vertical resolution -1 for the mov
    vsync_sm.put(479)

    rgb_sm = rp2.StateMachine(2, rgb, freq=125_000_000,
                              out_base=red_pin,
                              set_base=red_pin)
    rgb_sm.put(319)
        
    rgb_tx = DMA()
    rgb_reset = DMA()

    rgb_tx_ctrl = rgb_tx.pack_ctrl(
        size=0,           # Byte
        inc_read=True,
        inc_write=False,
        treq_sel=2,       # DREQ_PIO0_TX2
        chain_to=rgb_reset.channel,
    )
    rgb_tx.config(
        read=framebuf,
        write=rgb_sm,
        count=len(framebuf),
        ctrl=rgb_tx_ctrl,
    )

    rgb_reset_ctrl = rgb_reset.pack_ctrl(
        size=2,  # Word
        inc_read=False,
        inc_write=False,
        chain_to=rgb_tx.channel,
    )
    rgb_reset.config(
        read=framebuf_ptr,
        write=rgb_tx.registers[15:16],
        count=len(framebuf_ptr),
        ctrl=rgb_reset_ctrl,
    )
    
    hsync_sm.active(1)
    vsync_sm.active(1)
    rgb_sm.active(1)
    rgb_reset.active(1)
   

def stop_vga():
    global rgb_tx, rgb_reset, hsync_sm, vsync_sm, rgb_sm
    print("Stopping VGA")
    rgb_reset.close()
    rgb_tx.close()
    rgb_sm.active(0)
    vsync_sm.active(0)
    hsync_sm.active(0)
    for pin in vga_pins:
        pin.init(Pin.OUT)
        pin.low()
    
                
for x in range(320):
    framebuf[x] = 255

for y in range(480):
    framebuf[y * 320] = 255

offset = 0
for y in range(16):
    for line in range(30):
        for x in range(16):
            color = (x + y) % 16
            value = (color + (color * 16))
            for pair in range(20):
                if y == line == 0 or x == pair == 0:
                    offset = offset + 1
                else:                    
                    framebuf[offset] = value
                    offset = offset + 1


start_vga()
running = True

while True:
    while not button.value():
        time.sleep(.1)
    if running:
        stop_vga()
        running = False
    else:
        start_vga()
        running = True
    time.sleep(.5)
    
    if button.value():
        break

stop_vga()
