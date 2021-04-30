from qtpy.QtCore import Signal, QObject
import inputs
import importlib
import time


class QXboxController(QObject):
    button_a_action = Signal(bool)
    button_b_action = Signal(bool)
    button_x_action = Signal(bool)
    button_y_action = Signal(bool)
    button_rbump_action = Signal(bool)
    button_lbump_action = Signal(bool)
    button_rjoy_action = Signal(bool)
    button_ljoy_action = Signal(bool)
    button_select_action = Signal(bool)
    button_start_action = Signal(bool)
    button_dup_action = Signal(bool)
    button_dleft_action = Signal(bool)
    button_dright_action = Signal(bool)
    button_ddown_action = Signal(bool)
    axis_ljoy_action = Signal(object)  # will send a dict{'x': x_val, 'y': y_val}
    axis_rjoy_action = Signal(object)  # will send a dict{'x': x_val, 'y': y_val}
    axis_ltrigger_action = Signal(float)
    axis_rtrigger_action = Signal(float)

    def __init__(self):
        super(QXboxController, self).__init__()
        self._stop = False
        self.connected = False
        self.gamepad = None  # type: inputs.GamePad
        self._ljoyx = 0
        self._ljoyy = 0
        self._rjoyx = 0
        self._rjoyy = 0
        self._haty = 0
        self._hatx = 0

        self.signaldictionary = {'SOUTH': lambda x: self.button_a_action.emit(x),
                                 'EAST': lambda x: self.button_b_action.emit(x),
                                 'WEST': lambda x: self.button_x_action.emit(x),
                                 'NORTH': lambda x: self.button_y_action.emit(x),
                                 'TR': lambda x: self.button_rbump_action.emit(x),
                                 'TL': lambda x: self.button_lbump_action.emit(x),
                                 'THUMBR': lambda x: self.button_rjoy_action.emit(x),
                                 'THUMBL': lambda x: self.button_ljoy_action.emit(x),
                                 'SELECT': lambda x: self.button_select_action.emit(x),
                                 'START': lambda x: self.button_start_action.emit(x),
                                 'HAT0Y': lambda x: self._determine_d_button('y', x),
                                 'HAT0X': lambda x: self._determine_d_button('x', x),
                                 'RY': lambda x: [self.__setattr__('_rjoyy', x/32768),
                                                  self.axis_rjoy_action.emit({'x': self._rjoyx, 'y': self._rjoyy})],
                                 'RX': lambda x: [self.__setattr__('_rjoyx', x/32768),
                                                  self.axis_rjoy_action.emit({'x': self._rjoyx, 'y': self._rjoyy})],
                                 'Y': lambda x: [self.__setattr__('_ljoyy', x/32768),
                                                  self.axis_ljoy_action.emit({'x': self._ljoyx, 'y': self._ljoyy})],
                                 'X': lambda x: [self.__setattr__('_ljoyx', x/32768),
                                                  self.axis_ljoy_action.emit({'x': self._ljoyx, 'y': self._ljoyy})],
                                 'RZ': lambda x: self.axis_rtrigger_action.emit(x/255),
                                 'Z': lambda x: self.axis_ltrigger_action.emit(x/255)}
        self._keys = self.signaldictionary.keys()

    def _determine_d_button(self, axis, state):
        prev_val = self._haty if axis == 'y' else self._hatx
        if axis == 'y':
            self._haty = state
        else:
            self._hatx = state

        if state == 0:
            if prev_val == -1:
                if axis == 'y':
                    self.button_dup_action.emit(state)
                if axis == 'x':
                    self.button_dleft_action.emit(state)
            else:
                if axis == 'y':
                    self.button_ddown_action.emit(state)
                if axis == 'x':
                    self.button_dright_action.emit(state)
        else:
            if axis == 'y':
                if state == -1:
                    self.button_dup_action.emit(state)
                else:
                    self.button_ddown_action.emit(state)
            else:
                if state == -1:
                    self.button_dleft_action.emit(state)
                else:
                    self.button_dright_action.emit(state)

    def start(self):
        while not self.connected and not self._stop:
            try:
                self.gamepad = inputs.devices.gamepads[0]
            except IndexError as e:
                time.sleep(0.1)
                importlib.reload(inputs)  # in case controller wasn't plugged in, this refreshes the module
                continue
            self.connected = True
            while not self._stop:
                try:
                    events = self.gamepad.read()
                except inputs.UnpluggedError:
                    self.connected = False
                    break

                for event in events:
                    if event.ev_type != 'Sync':
                        for key in self._keys:
                            if key in event.code:
                                self.signaldictionary[key](event.state)
                                break

            self._stop = False

    def stop(self):
        self._stop = True
