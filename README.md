# MicroPython Menu

A lightweight, driver-independent menu engine for MicroPython character displays and button/keypad inputs.

It provides nested menus, actions, editable values, boolean toggles, choice fields, change callbacks, and a small API that can also be driven manually by an application's own event loop.

## Design

The menu engine does not import `machine`, `pyb`, `Pin`, `UART`, or a particular LCD/keypad driver. Hardware integration is handled by two tiny adapters:

- `display.write_line(row, text)` writes one fixed-width line. `display.clear()` is optional.
- `keypad.getkey()` returns one key string when pressed, otherwise `None`.

This keeps the library portable across boards and display/keypad combinations. The core uses only basic Python features; `uasyncio` is imported only when `run()` is called.

## Quick start

```python
from menu import MenuSystem

menu = MenuSystem(display, keypad, title="Main Menu", rows=4, columns=20)

settings = menu.add_submenu("Settings")
settings.add_value("Target", 25)
settings.add_toggle("Enabled", True)
settings.add_choice("Mode", ["AUTO", "MANUAL"], "AUTO")

menu.add_action("Reboot", reboot_device)

await menu.run()
```

`display` and `keypad` above are adapters implementing the two methods described in the Design section. See [`examples/basic_example.py`](examples/basic_example.py) for an adapter pattern, including how to connect a four-line LCD and a keypad driver.

## API

### Create menu entries

- `menu.add_submenu(label, title=None)` creates and returns a child `Menu`. Add entries to that returned object.
- `menu.add_action(label, callback)` calls `callback()` when selected.
- `menu.add_value(label, value, on_change=None, formatter=None)` adds an editable `int`, `float`, or `str` value.
- `menu.add_toggle(label, value=False, on_change=None)` adds an ON/OFF value.
- `menu.add_choice(label, options, value=None, on_change=None)` adds a value cycled through a list of options.

`on_change(new_value, old_value)` is called after a value is committed or changed. Callbacks execute in the menu loop; keep them short, or schedule longer work separately.

### Read and update values

Each `add_*` method returns its `MenuItem`:

```python
brightness = settings.add_value("Brightness", 50)
print(menu.get_value(brightness))
menu.set_value(brightness, 80)
```

`set_value(item, value, notify=False)` updates a value from application code. Set `notify=True` to invoke its change callback.

### Run modes

- `await menu.run()` runs the polling loop using `uasyncio`.
- `menu.render()` redraws the current screen.
- `menu.handle_key(key)` handles one key without polling hardware.
- `menu.run_once()` polls the keypad once.
- `menu.stop()` stops the asynchronous loop.

Manual mode is useful when the application already owns its main loop or input events.

## Default controls

| Action | Key |
|---|---|
| Previous item | `^` |
| Next item | `v` |
| Select / start editing / commit | `E` |
| Back / cancel editing | `M` |
| Delete last edit character | `BACKSPACE` |

Override controls at construction:

```python
menu = MenuSystem(display, keypad, keys={
    "up": "UP", "down": "DOWN", "enter": "OK", "back": "CANCEL"
})
```

Numeric editing accepts digit keys, `-`, and `.`. ENTER commits; BACK cancels. For `add_choice`, ENTER advances to the next option. UP/DOWN remain dedicated to menu navigation.

## Display requirements

The engine is designed for fixed-width character displays. `rows` includes the title row, so a 20x4 display uses `rows=4, columns=20` and shows up to three entries at once. The display adapter should accept exactly one row per `write_line` call; the engine pads and truncates text to the configured width.

## Limitations / extension points

- This is a menu/navigation component, not a complete GUI framework.
- Persistent storage, hardware communication, validation rules, and application state remain the responsibility of the application.
- Numeric editing currently commits values that Python can parse as the original numeric type; applications needing ranges or domain-specific validation should validate in `on_change` or wrap the value update in their own callback logic.
- The default keypad contract is polling-based. An application with interrupts or another event source can call `handle_key()` directly.

## Files

- `menu.py` — reusable menu engine.
- `examples/basic_example.py` — example adapters for an existing LCD and keypad driver.

## License

MIT. See `LICENSE`.
