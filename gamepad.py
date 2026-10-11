"""Gamepad input — one active controller, normalized to an Xbox-style layout.

Recognised controllers (Xbox, PlayStation, Switch Pro, most others) go through
SDL's GameController API, so A/B/X/Y, triggers and sticks land in the same place
on every pad. Unrecognised devices fall back to raw joystick indices (Xbox order).

Call update() once per frame after pygame.event.get(), and handle_event() for
JOYDEVICEADDED / JOYDEVICEREMOVED so hot-plugging works.
"""
import math
import pygame
from pygame._sdl2 import controller as sdl_controller

# Tuning (Microsoft's XInput guidance: left stick ~0.24, triggers ~0.12)
STICK_DEADZONE    = 0.20   # radial deadzone for the sticks
TRIGGER_THRESHOLD = 0.12   # fraction of trigger travel before it counts at all
RESPONSE_CURVE    = 1.6    # exponent for analog speed: <1 twitchy, 1 linear, >1 finer low end

# Button names (Xbox labels)
A, B, X, Y          = "a", "b", "x", "y"
LB, RB, L3, R3      = "lb", "rb", "l3", "r3"
START, BACK         = "start", "back"
DPAD_UP, DPAD_DOWN  = "dpad_up", "dpad_down"
DPAD_LEFT, DPAD_RIGHT = "dpad_left", "dpad_right"

_CTRL_BUTTONS = {
    A: pygame.CONTROLLER_BUTTON_A,               B: pygame.CONTROLLER_BUTTON_B,
    X: pygame.CONTROLLER_BUTTON_X,               Y: pygame.CONTROLLER_BUTTON_Y,
    LB: pygame.CONTROLLER_BUTTON_LEFTSHOULDER,   RB: pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
    L3: pygame.CONTROLLER_BUTTON_LEFTSTICK,      R3: pygame.CONTROLLER_BUTTON_RIGHTSTICK,
    START: pygame.CONTROLLER_BUTTON_START,       BACK: pygame.CONTROLLER_BUTTON_BACK,
    DPAD_UP: pygame.CONTROLLER_BUTTON_DPAD_UP,   DPAD_DOWN: pygame.CONTROLLER_BUTTON_DPAD_DOWN,
    DPAD_LEFT: pygame.CONTROLLER_BUTTON_DPAD_LEFT, DPAD_RIGHT: pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
}
# Raw joystick fallback — Xbox order as SDL reports it
_RAW_BUTTONS = {A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, BACK: 6, START: 7, L3: 8, R3: 9}
_RAW_AXES    = {"lx": 0, "ly": 1, "rx": 2, "ry": 3, "lt": 4, "rt": 5}


def apply_curve(value):
    """Shape a 0..1 analog value so small inputs are precise and full input is full speed."""
    return value ** RESPONSE_CURVE


def _radial_deadzone(x, y):
    """Return (x, y, magnitude) with a radial deadzone, magnitude rescaled to 0..1."""
    mag = math.hypot(x, y)
    if mag < STICK_DEADZONE:
        return 0.0, 0.0, 0.0
    scaled = min(1.0, (mag - STICK_DEADZONE) / (1.0 - STICK_DEADZONE))
    return x / mag * scaled, y / mag * scaled, scaled


def _axis_deadzone(v):
    """Single-axis deadzone, rescaled to -1..1."""
    if abs(v) < STICK_DEADZONE:
        return 0.0
    return math.copysign(min(1.0, (abs(v) - STICK_DEADZONE) / (1.0 - STICK_DEADZONE)), v)


def _trigger(value):
    """0..1 trigger travel → 0 below threshold, rescaled 0..1 above."""
    if value < TRIGGER_THRESHOLD:
        return 0.0
    return min(1.0, (value - TRIGGER_THRESHOLD) / (1.0 - TRIGGER_THRESHOLD))


class Gamepad:
    def __init__(self):
        if not sdl_controller.get_init():
            sdl_controller.init()
        self._dev        = None    # Controller or Joystick
        self._is_ctrl    = False   # True when using the GameController mapping
        self._instance   = None    # joystick instance id, for removal matching
        self._held       = {}
        self._prev       = {}
        self._raw_trig_live = {"lt": False, "rt": False}
        self._clear_state()
        for i in range(pygame.joystick.get_count()):
            if self._connect(i):
                break

    # ── Connection ──────────────────────────────────────────────────────
    @property
    def connected(self):
        return self._dev is not None

    @property
    def name(self):
        return self._dev.name if self._is_ctrl else (self._dev.get_name() if self._dev else "")

    def _connect(self, device_index):
        try:
            if sdl_controller.is_controller(device_index):
                dev = sdl_controller.Controller(device_index)
                self._instance = dev.as_joystick().get_instance_id()
                self._is_ctrl  = True
            else:
                dev = pygame.joystick.Joystick(device_index)
                dev.init()
                self._instance = dev.get_instance_id()
                self._is_ctrl  = False
        except pygame.error:
            return False
        self._dev = dev
        self._raw_trig_live = {"lt": False, "rt": False}
        self._clear_state()
        return True

    def _disconnect(self):
        self._dev = None
        self._instance = None
        self._clear_state()

    def handle_event(self, event):
        if event.type == pygame.JOYDEVICEADDED and not self.connected:
            self._connect(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED and event.instance_id == self._instance:
            self._disconnect()
            for i in range(pygame.joystick.get_count()):   # fall back to another pad
                if self._connect(i):
                    break

    # ── Per-frame read ──────────────────────────────────────────────────
    def _clear_state(self):
        self._prev = {}
        self._held = {}
        self.lx = self.ly = self.l_mag = 0.0
        self.rx = self.ry = self.r_mag = 0.0
        self.lt = self.rt = 0.0
        self._raw_ly = self._raw_ry = 0.0

    def update(self):
        self._prev = self._held
        if not self._dev:
            self._held = {}
            return
        try:
            if self._is_ctrl:
                ax = lambda a: self._dev.get_axis(a) / 32767.0
                lx, ly = ax(pygame.CONTROLLER_AXIS_LEFTX),  ax(pygame.CONTROLLER_AXIS_LEFTY)
                rx, ry = ax(pygame.CONTROLLER_AXIS_RIGHTX), ax(pygame.CONTROLLER_AXIS_RIGHTY)
                lt = ax(pygame.CONTROLLER_AXIS_TRIGGERLEFT)
                rt = ax(pygame.CONTROLLER_AXIS_TRIGGERRIGHT)
                self._held = {n: bool(self._dev.get_button(b)) for n, b in _CTRL_BUTTONS.items()}
            else:
                d = self._dev
                n_axes = d.get_numaxes()
                ax = lambda k: d.get_axis(_RAW_AXES[k]) if _RAW_AXES[k] < n_axes else 0.0
                lx, ly, rx, ry = ax("lx"), ax("ly"), ax("rx"), ax("ry")
                lt, rt = self._raw_trigger(ax("lt"), "lt"), self._raw_trigger(ax("rt"), "rt")
                n_btn = d.get_numbuttons()
                self._held = {n: (b < n_btn and d.get_button(b) == 1) for n, b in _RAW_BUTTONS.items()}
                hx, hy = d.get_hat(0) if d.get_numhats() > 0 else (0, 0)
                self._held.update({DPAD_UP: hy == 1, DPAD_DOWN: hy == -1,
                                   DPAD_LEFT: hx == -1, DPAD_RIGHT: hx == 1})
        except pygame.error:
            self._disconnect()   # unplugged mid-read
            return
        self._raw_ly, self._raw_ry = ly, ry
        self.lx, self.ly, self.l_mag = _radial_deadzone(lx, ly)
        self.rx, self.ry, self.r_mag = _radial_deadzone(rx, ry)
        self.lt, self.rt = _trigger(lt), _trigger(rt)

    def _raw_trigger(self, value, key):
        """Raw triggers rest at -1. Some drivers report 0 (half-pressed) until the
        trigger is first touched, so ignore it until we've seen it move off 0."""
        if not self._raw_trig_live[key]:
            if value == 0.0:
                return 0.0
            self._raw_trig_live[key] = True
        return (value + 1.0) / 2.0

    # ── Queries ─────────────────────────────────────────────────────────
    def held(self, button):
        return self._held.get(button, False)

    def pressed(self, button):
        """True only on the frame the button went down."""
        return self._held.get(button, False) and not self._prev.get(button, False)

    def any_pressed(self):
        """True on the frame any button went down."""
        return any(v and not self._prev.get(k, False) for k, v in self._held.items())

    def any_held(self):
        return any(self._held.values()) or self.lt > 0 or self.rt > 0

    def left_angle(self):
        """Ship-rotation angle the left stick points to, or None inside the deadzone."""
        if self.l_mag <= 0:
            return None
        return math.degrees(math.atan2(-self.lx, self.ly))

    def right_angle(self):
        """Ship-rotation angle the right stick points to, or None inside the deadzone."""
        if self.r_mag <= 0:
            return None
        return math.degrees(math.atan2(-self.rx, self.ry))

    def stick_up(self, side):
        """Vertical push of the 'left' or 'right' stick: +1 full up, -1 full down.
        Uses only the vertical axis so sideways wobble doesn't change speed."""
        return -_axis_deadzone(self._raw_ly if side == "left" else self._raw_ry)
