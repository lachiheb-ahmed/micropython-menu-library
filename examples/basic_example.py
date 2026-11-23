"""Example wiring for an existing 20x4 LCD and matrix keypad driver.

Adapt only these two small adapter classes to your hardware drivers.
"""

import uasyncio
from menu import MenuSystem


class LCDAdapter:
    def __init__(self, lcd):
        self.lcd = lcd

    def write_line(self, row, text):
        # The supplied project LCD driver accepts one flat 80-character string.
        # MenuSystem calls write_line once per row, so keep a local frame buffer.
        if not hasattr(self, "lines"):
            self.lines = [" " * 20 for _ in range(4)]
        self.lines[row] = text[:20].ljust(20)
        self.lcd.writeLCD("".join(self.lines))

    def clear(self):
        self.lines = [" " * 20 for _ in range(4)]


class KeypadAdapter:
    def __init__(self, keypad):
        self.keypad = keypad

    def getkey(self):
        return self.keypad.getkeypad()


def save_brightness(value, old_value):
    print("Brightness changed:", old_value, "->", value)


def reset_device():
    print("Reset action selected")


async def main(lcd_driver, keypad_driver):
    display = LCDAdapter(lcd_driver)
    keypad = KeypadAdapter(keypad_driver)
    menu = MenuSystem(display, keypad, title="Device", rows=4, columns=20)

    settings = menu.add_submenu("Settings")
    settings.add_value("Brightness", 75, on_change=save_brightness)
    settings.add_toggle("Backlight", True)
    settings.add_choice("Mode", ["AUTO", "MANUAL", "OFF"], "AUTO")

    menu.add_action("Reset device", reset_device)
    await menu.run()


# Call main(lcd_driver, keypad_driver) from your application after creating
# your existing hardware drivers.
