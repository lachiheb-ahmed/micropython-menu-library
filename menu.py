"""A small, display- and input-driver-independent menu system for MicroPython.

The application supplies two adapters:
  display.write_line(row, text)  (optional display.clear())
  keypad.getkey()                (returns a key string or None)

Default keys: UP='^', DOWN='v', ENTER='E', BACK='M'.
"""


class MenuItem:
    """One selectable entry in a Menu."""
    def __init__(self, label, kind, value=None, callback=None,
                 on_change=None, options=None, formatter=None):
        self.label = str(label)
        self.kind = kind
        self.value = value
        self.callback = callback
        self.on_change = on_change
        self.options = options
        self.formatter = formatter
        self.parent = None


class Menu:
    """A menu container. Usually created by MenuSystem.add_submenu()."""
    def __init__(self, title="Menu"):
        self.title = str(title)
        self.items = []
        self.parent_item = None

    def _append(self, item):
        item.parent = self
        self.items.append(item)
        return item

    def add_submenu(self, label, title=None):
        child = Menu(title if title is not None else label)
        item = self._append(MenuItem(label, "submenu", value=child))
        child.parent_item = item
        return child

    def add_action(self, label, callback):
        return self._append(MenuItem(label, "action", callback=callback))

    def add_value(self, label, value, on_change=None, formatter=None):
        """Add an editable integer/float/string value.

        UP/DOWN changes numeric values by one. ENTER starts editing; numeric
        input is accepted from digit keys, '.' and '-'. ENTER commits; BACK
        cancels. For non-numeric values, UP/DOWN cycles only when options are
        supplied (use add_choice for that case).
        """
        if not isinstance(value, (int, float, str)):
            raise TypeError("value must be int, float, or str")
        return self._append(MenuItem(label, "value", value=value,
                                     on_change=on_change,
                                     formatter=formatter))

    def add_toggle(self, label, value=False, on_change=None):
        return self._append(MenuItem(label, "toggle", value=bool(value),
                                     on_change=on_change))

    def add_choice(self, label, options, value=None, on_change=None):
        """Add a value selected by cycling through options with UP/DOWN."""
        if not options:
            raise ValueError("options must not be empty")
        values = list(options)
        if value is None:
            value = values[0]
        if value not in values:
            raise ValueError("initial value must be in options")
        return self._append(MenuItem(label, "choice", value=value,
                                     options=values, on_change=on_change))


class MenuSystem:
    """Driver-independent menu controller for small character displays."""
    def __init__(self, display, keypad, title="Main Menu", rows=4,
                 columns=20, keys=None, refresh_delay_ms=30):
        if rows < 2 or columns < 8:
            raise ValueError("rows must be >= 2 and columns must be >= 8")
        self.display = display
        self.keypad = keypad
        self.rows = rows
        self.columns = columns
        self.refresh_delay_ms = refresh_delay_ms
        self.keys = {"up": "^", "down": "v", "enter": "E", "back": "M"}
        if keys:
            self.keys.update(keys)
        self.root = Menu(title)
        self.current = self.root
        self.selected = 0
        self.first_visible = 0
        self._editing = None
        self._edit_buffer = ""
        self._edit_started = False
        self._running = False

    # Convenience methods allow building the root menu directly.
    def add_submenu(self, label, title=None):
        return self.root.add_submenu(label, title)

    def add_action(self, label, callback):
        return self.root.add_action(label, callback)

    def add_value(self, label, value, on_change=None, formatter=None):
        return self.root.add_value(label, value, on_change, formatter)

    def add_toggle(self, label, value=False, on_change=None):
        return self.root.add_toggle(label, value, on_change)

    def add_choice(self, label, options, value=None, on_change=None):
        return self.root.add_choice(label, options, value, on_change)

    def _visible_count(self):
        return self.rows - 1  # first row is the menu title

    def _clamp_view(self):
        count = len(self.current.items)
        if count == 0:
            self.selected = 0
            self.first_visible = 0
            return
        self.selected = max(0, min(self.selected, count - 1))
        visible = self._visible_count()
        if self.selected < self.first_visible:
            self.first_visible = self.selected
        elif self.selected >= self.first_visible + visible:
            self.first_visible = self.selected - visible + 1

    def _value_text(self, item):
        if self._editing is item:
            return self._edit_buffer
        if item.kind == "submenu":
            return ">"
        if item.kind == "toggle":
            return "ON" if item.value else "OFF"
        if item.kind == "action":
            return ""
        if item.formatter:
            return str(item.formatter(item.value))
        return str(item.value)

    def _write_line(self, row, text):
        text = str(text)[:self.columns].ljust(self.columns)
        self.display.write_line(row, text)

    def render(self):
        """Draw the current menu. Display adapter must implement write_line."""
        self._clamp_view()
        if hasattr(self.display, "clear"):
            self.display.clear()
        title = self.current.title
        if self._editing is not None:
            title = "Edit: " + self._editing.label
        self._write_line(0, title)
        start = self.first_visible
        end = min(len(self.current.items), start + self._visible_count())
        for row, index in enumerate(range(start, end), 1):
            item = self.current.items[index]
            marker = ">" if index == self.selected else " "
            value = self._value_text(item)
            available = self.columns - 2 - len(value)
            label = item.label[:max(0, available)]
            line = marker + label
            if value:
                line = line.ljust(self.columns - len(value)) + value
            self._write_line(row, line)
        for row in range(1 + max(0, end - start), self.rows):
            self._write_line(row, "")

    def _notify(self, item, old_value):
        if item.on_change:
            item.on_change(item.value, old_value)

    def _enter_item(self):
        if not self.current.items:
            return
        item = self.current.items[self.selected]
        if item.kind == "submenu":
            self.current = item.value
            self.selected = 0
            self.first_visible = 0
        elif item.kind == "action":
            if item.callback:
                item.callback()
        elif item.kind == "toggle":
            old = item.value
            item.value = not item.value
            self._notify(item, old)
        elif item.kind == "choice":
            self._cycle_choice(item, 1)
        elif item.kind == "value":
            self._editing = item
            self._edit_buffer = str(item.value)
            self._edit_started = False

    def _cycle_choice(self, item, direction):
        old = item.value
        index = item.options.index(old)
        item.value = item.options[(index + direction) % len(item.options)]
        self._notify(item, old)

    def _move(self, direction):
        if self._editing is not None:
            return
        if not self.current.items:
            return
        self.selected = (self.selected + direction) % len(self.current.items)
        self._clamp_view()

    def _back(self):
        if self._editing is not None:
            self._editing = None
            self._edit_buffer = ""
            return
        if self.current.parent_item is not None:
            parent_item = self.current.parent_item
            parent = parent_item.parent
            self.current = parent
            self.selected = parent.items.index(parent_item)
            self._clamp_view()

    def _edit_key(self, key):
        if key == self.keys["back"]:
            self._back()
        elif key == self.keys["enter"]:
            item = self._editing
            old = item.value
            try:
                if isinstance(old, int) and not isinstance(old, bool):
                    new_value = int(self._edit_buffer)
                elif isinstance(old, float):
                    new_value = float(self._edit_buffer)
                else:
                    new_value = self._edit_buffer
            except ValueError:
                return
            item.value = new_value
            self._editing = None
            self._edit_buffer = ""
            self._edit_started = False
            self._notify(item, old)
        elif key == "BACKSPACE":
            self._edit_buffer = self._edit_buffer[:-1]
        elif key == "-":
            if not self._edit_started:
                self._edit_buffer = ""
                self._edit_started = True
            if self._edit_buffer == "":
                self._edit_buffer = "-"
        elif key == ".":
            if not self._edit_started:
                self._edit_buffer = ""
                self._edit_started = True
            if "." not in self._edit_buffer:
                self._edit_buffer += "."
        elif len(key) == 1 and key.isdigit():
            if not self._edit_started:
                self._edit_buffer = ""
                self._edit_started = True
            self._edit_buffer += key

    def handle_key(self, key):
        """Process one key. Useful for event-driven applications and testing."""
        if not key:
            return
        if self._editing is not None:
            self._edit_key(key)
        elif key == self.keys["up"]:
            self._move(-1)
        elif key == self.keys["down"]:
            self._move(1)
        elif key == self.keys["enter"]:
            self._enter_item()
        elif key == self.keys["back"]:
            self._back()
        self.render()

    def run_once(self):
        """Read at most one key, handle it, and redraw. Returns the key."""
        key = self.keypad.getkey()
        if key:
            self.handle_key(key)
        return key

    async def run(self):
        """Run the menu loop. Requires MicroPython uasyncio."""
        import uasyncio
        self._running = True
        self.render()
        while self._running:
            self.run_once()
            await uasyncio.sleep_ms(self.refresh_delay_ms)

    def stop(self):
        self._running = False

    def get_value(self, item):
        """Return an item's current value; item is returned by add_*()."""
        return item.value

    def set_value(self, item, value, notify=False):
        """Update an item's value from application code."""
        old = item.value
        if item.kind == "toggle":
            value = bool(value)
        if item.kind == "choice" and value not in item.options:
            raise ValueError("value must be one of the item's options")
        item.value = value
        if notify:
            self._notify(item, old)
        self.render()
