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
from QSofaGLViewTools import QXboxController


class QSofaViewXBoxController(QObject):
    view_update_requested = Signal()

    def __init__(self,
                 dead_zone=0.3,
                 translate_rate_limit=1.5,  # mm/s
                 rotate_rate_limit=20,  # deg/s
                 update_rate=20  # Hz
                 ):
        super(QSofaViewXBoxController, self).__init__()

        self.viewer = None  # type: QSofaGLView
        self._viewer_set = False
        self._bumper_pressed = False
        self._dead_zone = dead_zone
        self.translate_rate_limit = translate_rate_limit
        self.rotate_rate_limit = rotate_rate_limit
        self.xbox_thread = QThread()
        self.controller = QXboxController()
        self.controller.moveToThread(self.xbox_thread)
        self.xbox_thread.started.connect(self.controller.start)
        self.xbox_thread.start()
        self.controller.axis_rjoy_action.connect(lambda x: self.update_viewer_cam(self.viewer, 'r_thumb', x))
        self.controller.axis_ljoy_action.connect(lambda x: self.update_viewer_cam(self.viewer, 'l_thumb', x))
        self.controller.button_lbump_action.connect(lambda x: setattr(self, '_bumper_pressed', x))
        self.controller.axis_rtrigger_action.connect(lambda x: self.update_viewer_cam(self.viewer, 'r_trigger', x))
        self.controller.axis_ltrigger_action.connect(lambda x: self.update_viewer_cam(self.viewer, 'l_trigger', x))
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

        self.controller.button_x_action.connect(lambda: print(self.viewer.camera.position.array(), self.viewer.camera.orientation.array()))

    def set_viewer(self, viewer):
        self.viewer = viewer
        self._viewer_set = True
        try:
            self._update_timer.disconnect()
        except TypeError:
            pass
        self._update_timer.timeout.connect(self.viewer.update)

    def start_auto_update(self, rate=0.05):
        if not self._viewer_set:
            print('Cannot start auto-update. No SofaGLViewer is set.')
            return
        self._update_timer.setInterval(rate)
        self._update_timer.start()

    def stop_auto_update(self):
        self._update_timer.stop()

    def update_viewer_cam(self, viewer, action, value):
        if not self._viewer_set:
            return
        if action == 'l_thumb':
            self.current_translational_speed = [self.scale_axis_value(-value['x']),
                                                  self.scale_axis_value(-value['y']),
                                                  self.current_translational_speed[2]]
        elif action == 'r_thumb':
            self.current_rotational_speed = [self.scale_axis_value(-value['y']), self.current_rotational_speed[1],
                                               self.scale_axis_value(value['x'])] if self._bumper_pressed else [
                self.scale_axis_value(-value['y']), self.scale_axis_value(value['x']),
                self.current_rotational_speed[2]]
        elif action == 'r_trigger':
            self.current_translational_speed = [self.current_translational_speed[0],
                                                  self.current_translational_speed[1],
                                                  value]
        elif action == 'l_trigger':
            self.current_translational_speed = [self.current_translational_speed[0],
                                                  self.current_translational_speed[1],
                                                  -value]
        self.view_update_requested.emit()

    def scale_axis_value(self, axis_input):
        scaled = axis_input * 2
        if abs(scaled) < self._dead_zone:
            return 0
        else:
            return np.sign(scaled) * (abs(scaled) - self._dead_zone) / (1 - self._dead_zone)

    def update_camera(self):
        now = time.time()
        time_since_last_update = self.time_at_last_update - now
        self.time_at_last_update = now

        # very inefficiently calculate the new angle for the camera
        current_rotational_speed = np.array(self.current_rotational_speed) * self.rotate_rate_limit
        additional_rotation = current_rotational_speed * time_since_last_update
        rotation = transform.Rotation.from_euler("XYZ", additional_rotation, degrees=True)
        self.viewer.camera.rotate(rotation.as_quat().tolist())
        current_orientation = transform.Rotation.from_quat(self.viewer.camera.orientation.array())

        # calculate the new position
        current_position = self.viewer.camera.position.array()
        current_translational_speed = np.array(self.current_translational_speed) * self.translate_rate_limit
        self.viewer.camera.position = self.viewer.camera.position.array()
        self.viewer.camera.position = list(
            current_position + current_orientation.apply(current_translational_speed * time_since_last_update))