try:
    from qtpy.QtWidgets import *
    from qtpy.QtCore import *
    from qtpy.QtGui import *
except Exception as e:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    Signal = pyqtSignal

import numpy as np
import scipy.spatial.transform as transform
import time
from QSofaGLViewTools import QSofaGLView


class QSofaViewKeyboardController(QObject):
    view_update_requested = Signal()

    def __init__(self,
                 translate_rate_limit=1.5,  # mm/s
                 rotate_rate_limit=5,  # deg/s
                 update_rate=20  # Hz
                 ):
        super(QSofaViewKeyboardController, self).__init__()

        self.viewers = None  # type: list[QSofaGLView]
        self._viewer_set = False
        self.translate_rate_limit = translate_rate_limit
        self.rotate_rate_limit = rotate_rate_limit
        self._update_timer = QTimer()
        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self.update_camera)
        self.camera_timer.setInterval(1/update_rate)
        self.translate_rate_limit = translate_rate_limit
        self.rotate_rate_limit = rotate_rate_limit
        self.current_translational_speed = [0., 0., 0.]  # in percent of max speed
        self.current_rotational_speed = [0., 0., 0.]  # in percent of max speed
        self.camera_timer.start()
        self.time_at_last_update = time.time()

    def set_viewers(self, viewers):
        if hasattr(viewers, '__iter__'):
            self.viewers = viewers
        else:
            self.viewers = [viewers]
        self._viewer_set = True
        try:
            self._update_timer.disconnect()
        except TypeError:
            pass
        for viewer in self.viewers:
            viewer._keyboard_control = self
            self._update_timer.timeout.connect(viewer.update)
            viewer.key_pressed.connect(self.keyPressEvent)
            viewer.key_released.connect(self.keyReleaseEvent)

    def start_auto_update(self, rate=0.05):
        if not self._viewer_set:
            print('Cannot start auto-update. No SofaGLViewer is set.')
            return
        self._update_timer.setInterval(rate)
        self._update_timer.start()

    def stop_auto_update(self):
        self._update_timer.stop()

    def keyPressEvent(self, event):
        key = event.key()
        mod = event.modifiers()

        if key == Qt.Key.Key_Up:
            self.current_rotational_speed[0] = -self.rotate_rate_limit
        elif key == Qt.Key.Key_Down:
            self.current_rotational_speed[0] = self.rotate_rate_limit
        elif key == Qt.Key.Key_Left:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_rotational_speed[2] = -self.rotate_rate_limit
            else:
                self.current_rotational_speed[1] = -self.rotate_rate_limit
        elif key == Qt.Key.Key_Right:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_rotational_speed[2] = self.rotate_rate_limit
            else:
                self.current_rotational_speed[1] = self.rotate_rate_limit

        elif key == Qt.Key.Key_W:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_translational_speed[2] = self.translate_rate_limit
            else:
                self.current_translational_speed[1] = -self.translate_rate_limit
        elif key == Qt.Key.Key_S:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_translational_speed[2] = -self.translate_rate_limit
            else:
                self.current_translational_speed[1] = self.translate_rate_limit
        elif key == Qt.Key.Key_A:
            self.current_translational_speed[0] = self.translate_rate_limit
        elif key == Qt.Key.Key_D:
            self.current_translational_speed[0] = -self.translate_rate_limit

        elif key == Qt.Key.Key_Control:
            self.current_rotational_speed[1] = 0
            self.current_translational_speed[1] = 0

    def keyReleaseEvent(self, event: QKeyEvent):
        key = event.key()
        mod = event.modifiers()

        if key == Qt.Key.Key_Up:
            self.current_rotational_speed[0] = 0
        elif key == Qt.Key.Key_Down:
            self.current_rotational_speed[0] = 0
        elif key == Qt.Key.Key_Left:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_rotational_speed[2] = 0
            else:
                self.current_rotational_speed[1] = 0
        elif key == Qt.Key.Key_Right:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_rotational_speed[2] = 0
            else:
                self.current_rotational_speed[1] = 0

        elif key == Qt.Key.Key_W:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_translational_speed[2] = 0
            else:
                self.current_translational_speed[1] = 0
        elif key == Qt.Key.Key_S:
            if mod == Qt.KeyboardModifier.ControlModifier:
                self.current_translational_speed[2] = 0
            else:
                self.current_translational_speed[1] = 0
        elif key == Qt.Key.Key_A:
            self.current_translational_speed[0] = 0
        elif key == Qt.Key.Key_D:
            self.current_translational_speed[0] = 0

        elif key == Qt.Key.Key_Control:
            self.current_rotational_speed[2] = 0
            self.current_translational_speed[2] = 0

    def update_camera(self):
        now = time.time()
        time_since_last_update = self.time_at_last_update - now
        self.time_at_last_update = now

        # very inefficiently calculate the new angle for the camera
        current_rotational_speed = np.array(self.current_rotational_speed) * self.rotate_rate_limit
        additional_rotation = current_rotational_speed * time_since_last_update
        rotation = transform.Rotation.from_euler("XYZ", additional_rotation, degrees=True)
        self.viewers[0].camera.rotate(rotation.as_quat().tolist())
        current_orientation = transform.Rotation.from_quat(self.viewers[0].camera_orientation.array())
        # calculate the new position
        current_translational_speed = np.array(self.current_translational_speed) * self.translate_rate_limit
        current_pos = self.viewers[0].camera_position.array()
        current_pos = np.reshape(current_pos, (current_pos.shape[-1]))
        self.viewers[0].update_position(current_pos[:3] + current_orientation.apply(current_translational_speed * time_since_last_update))
        self.viewers[0].update_orientation(current_orientation.as_quat())
