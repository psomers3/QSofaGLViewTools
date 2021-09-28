from qtpy.QtWidgets import *
from qtpy.QtCore import *
from qtpy.QtGui import *
import Sofa.SofaGL as SGL
import Sofa
from SofaRuntime import importPlugin
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from typing import List
from PIL import Image
import os
import cv2
import time
import re
import shutil


sim = Sofa.Simulation


def euler_to_quaternion(roll, pitch, yaw):
    qx = np.sin(roll / 2) * np.cos(pitch / 2) * np.cos(yaw / 2) - np.cos(roll / 2) * np.sin(pitch / 2) * np.sin(yaw / 2)
    qy = np.cos(roll / 2) * np.sin(pitch / 2) * np.cos(yaw / 2) + np.sin(roll / 2) * np.cos(pitch / 2) * np.sin(yaw / 2)
    qz = np.cos(roll / 2) * np.cos(pitch / 2) * np.sin(yaw / 2) - np.sin(roll / 2) * np.sin(pitch / 2) * np.cos(yaw / 2)
    qw = np.cos(roll / 2) * np.cos(pitch / 2) * np.cos(yaw / 2) + np.sin(roll / 2) * np.sin(pitch / 2) * np.sin(yaw / 2)

    return [qx, qy, qz, qw]


def quaternion_rotation_matrix(Q):
    """
    https://automaticaddison.com/how-to-convert-a-quaternion-to-a-rotation-matrix/
    Covert a quaternion into a full three-dimensional rotation matrix.
    Input
    :param Q: A 4 element array representing the quaternion (q0,q1,q2,q3)
    Output
    :return: A 3x3 element matrix representing the full 3D rotation matrix.
             This rotation matrix converts a point in the local reference
             frame to a point in the global reference frame.
    """
    # Extract the values from Q
    q0 = Q[0]
    q1 = Q[1]
    q2 = Q[2]
    q3 = Q[3]

    # First row of the rotation matrix
    r00 = 2 * (q0 * q0 + q1 * q1) - 1
    r01 = 2 * (q1 * q2 - q0 * q3)
    r02 = 2 * (q1 * q3 + q0 * q2)

    # Second row of the rotation matrix
    r10 = 2 * (q1 * q2 + q0 * q3)
    r11 = 2 * (q0 * q0 + q2 * q2) - 1
    r12 = 2 * (q2 * q3 - q0 * q1)

    # Third row of the rotation matrix
    r20 = 2 * (q1 * q3 - q0 * q2)
    r21 = 2 * (q2 * q3 + q0 * q1)
    r22 = 2 * (q0 * q0 + q3 * q3) - 1

    # 3x3 rotate matrix <-- These values are tweaked to match the results obtained from scipy.spatial.transform.Rotation
    rot_matrix = np.array([[r22, -r12, r02],
                           [r21, -r11, r01],
                           [-r20, r10, -r00]])
    return rot_matrix


class QSofaGLView(QOpenGLWidget):
    key_pressed = Signal(QKeyEvent)
    key_released = Signal(QKeyEvent)
    scroll_event = Signal(QWheelEvent)
    resizedGL = Signal(float, float)  # width, height
    repainted = Signal()

    DTYPES = {np.uint8: GL_UNSIGNED_BYTE,
              np.float32: GL_FLOAT,
              np.uint16: GL_UNSIGNED_SHORT}

    def __init__(self,
                 sofa_visuals_node: Sofa.Core.Node,
                 camera: Sofa.Components.BaseCamera,
                 size: tuple = (800, 600),
                 auto_place_camera: bool = False,
                 internal_refresh_freq = 0):
        """

        Parameters
        ----------
        sofa_visuals_node : Sofa.Core.Node
                The SOFA Node that will be transversed for calculating the visuals.
        camera : Sofa.Components.BaseCamera
                The SOFA BaseCamera object that is used for calculating the view
        size : Tuple[int, int]
                Minimum view size of (width, height) in pixels. Default = (800, 600)
        auto_place_camera : bool
                Whether or not to override the camera position and try to auto-place it for viewing the simulation. This
                will occur everytime the GLView is initialized.
        internal_refresh_freq : float
                rate at which the window will automatically call it's own update function in Hz. recommended: 20 Hz if
                not using another method to update the view.
        """

        super(QSofaGLView, self).__init__()

        self.auto_place = auto_place_camera
        self.visuals_node = sofa_visuals_node
        self.camera = camera
        self.camera_position = camera.position
        self.camera_orientation = camera.orientation
        self.dofs = None
        self.setMinimumSize(*size)
        self.resize(*size)
        self.z_far = camera.zFar  # get these values using self.z***.value because they are sofa Data objects
        self.z_near = camera.zNear
        self.setFocusPolicy(Qt.StrongFocus)
        self.background_color = [1, 1, 1, 0]
        self.spheres = []
        self.setWindowFlag(Qt.NoDropShadowWindowHint)
        self._rotating = False
        self._panning = False
        self._rotate_point = None
        self._temp_cam = None
        self._rotate_screen_origin = None
        self._pan_screen_origin = None
        self._recording = False
        self._video_file = None  # type: str
        self._save_img = False
        self._images = []
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update, Qt.QueuedConnection)
        if internal_refresh_freq > 0:
            ms = (1000/internal_refresh_freq)
            self._update_timer.start(internal_refresh_freq)

    @staticmethod
    def create_view_and_camera(node: Sofa.Core.Node,
                               sofa_visuals_node: Sofa.Core.Node = None,
                               initial_position: list = None,
                               size: tuple = (800, 600),
                               camera_kwargs: dict = {'distance': 5000, "fieldOfView": 45, "computeZClip": False},
                               internal_refresh_freq = 0
                               ):
        """
        Function to create a QSofaGLViewer object and place a camera in it. This will also create a MechanicalObject to
        control the DOFs of the camera.

        Parameters
        ----------
        node : Sofa.Core.Node
                The Simulation Node to add the camera and MechanicalObject to.
        sofa_visuals_node : Sofa.Core.Node
                The SOFA Node that will be transversed for calculating the visuals. If left as None, it will use node.
        initial_position : list
                initial position of the camera [x, y, z, quaternion]. If None, will try it's best to place the camera.
        size : tuple[int, int]
                Minimum view size of (width, height) in pixels. Default = (800, 600)
        camera_kwargs : dict
                dictionary of keywords to pass to construction of the Sofa.Components.InteractiveCamera object. Do not
                pass "name", "position", or "orientation".
        internal_refresh_freq : float
                rate at which the window will automatically call it's own update function in Hz. recommended: 20 Hz if
                not using another method to update the view.

        Returns
        -------
            tuple
                A tuple containing (QSofaGLView, Sofa.Components.InteractiveCamera, Sofa.Components.MechanicalObject)
                The MechanicalObject will also be available within the QSofaGLView as a parameter "dofs"

        """
        if initial_position is None:
            auto_place = True
            initial_position = [0, 0, 0, 0, 0, 0, 1]
        else:
            auto_place = False
        importPlugin("SofaGeneralEngine")
        subnode = node.addChild("camera_4_QSofaGLView")
        dofs = subnode.addObject("MechanicalObject", name="camera_dofs", template="Rigid3d", position=initial_position)
        subnode.addObject("RigidToQuatEngine", name="camera_engine", rigids="@camera_dofs.position")
        camera = subnode.addObject("InteractiveCamera", name="camera", position="@camera_engine.positions",
                                   orientation="@camera_engine.orientations", **camera_kwargs)

        if sofa_visuals_node is None:
            sofa_visuals_node = node

        view = QSofaGLView(sofa_visuals_node=sofa_visuals_node,
                           camera=camera,
                           size=size,
                           auto_place_camera=auto_place,
                           internal_refresh_freq=internal_refresh_freq)
        view.dofs = dofs
        view.camera_position = dofs.position
        return view, camera, dofs

    def update_position(self, new_position):
        """

        Parameters
        ----------
        new_position : np.array
                a numpy array of [x,y,z]

        Returns
        -------
            nothing. updates the camera position
        """
        if self.dofs is not None:
            current_pos = self.dofs.position.array().copy()
            current_pos[0, 0:3] = new_position
            self.dofs.position = list(current_pos)
        else:
            self.camera.position = list(new_position)

    def update_orientation(self, new_orientation):
        """

        Parameters
        ----------
        new_orientation : np.array
                a numpy array of [x,y,z, w] quaternion

        Returns
        -------
            nothing. updates the camera orientation
        """
        if self.dofs is not None:
            current_pos = self.dofs.position.array().copy()
            current_pos[0, 3:] = new_orientation
            self.dofs.position = list(current_pos)
        else:
            self.camera.orientation = list(new_orientation)

    def auto_place_camera(self):
        """
        Place the camera automatically such that it is outside the bounding box of the visuals node and looking at the
        center.
        Returns
        -------
        None
        """
        if self.dofs is None:
            self.camera.setDefaultView()
        else:
            cam = self.visuals_node.addObject("InteractiveCamera", name="tempcam")
            self.visuals_node.removeObject(self.camera)
            Sofa.Simulation.init(self.visuals_node)
            cam.setDefaultView()
            self.update_position(cam.position.array())
            self.update_orientation(cam.orientation.array())
            self.visuals_node.removeObject(cam)
        self.update()

    def make_viewer_transparent(self, make_transparent=True):
        """ This will only make the background of the viewer transparent if the background_color alpha is set to 0"""
        self.setAttribute(Qt.WA_TranslucentBackground, make_transparent)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, make_transparent)
        self.update()

    def set_background_color(self, color):
        """
        :param color: [r, g, b, alpha] alpha determines opacity. Use 0 to save images with a transparent background
        """
        self.background_color = color
        self.update()

    def get_intrinsic_parameters(self):
        # https://github.com/opencv/opencv_contrib/blob/master/modules/viz/src/types.cpp
        pm = glGetFloatv(GL_PROJECTION_MATRIX)
        pm = np.transpose(pm)  # openGL is column-major
        near = self.z_near.value
        left = (near * (pm[0][2] - 1)) / pm[0][0]
        right = 2 * near / pm[0][0] + left
        bottom = near * (pm[1][2] - 1) / pm[1][1]
        top = 2.0 * near / pm[1][1] + bottom
        cx = (left * self.width()) / (left - right)
        cy = (top * self.height()) / (top - bottom)
        fx = -near * cx / left
        fy = near * cy / top
        return fx, fy, cx, cy

    def get_transform_to_global_coord(self):
        transformation = np.zeros((4, 4))
        transformation[:3, -1] = self.camera.position.array()
        transformation[-1, -1] = 1
        transformation[:3, :3] = quaternion_rotation_matrix(self.camera.orientation.array())
        return transformation

    def initializeGL(self):
        glViewport(0, 0, self.width(), self.height())
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        SGL.glewInit()
        Sofa.Simulation.initVisual(self.visuals_node)
        Sofa.Simulation.initTextures(self.visuals_node)
        if self.auto_place:
            self.visuals_node.init()
            self.auto_place_camera()

    def paintGL(self):
        self.makeCurrent()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glClearColor(*self.background_color)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.camera.findData('fieldOfView').value, (self.width() / self.height()), self.z_near.value,
                       self.z_far.value)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        camera_mvm = self.camera.getOpenGLModelViewMatrix()
        glMultMatrixd(camera_mvm)
        SGL.draw(self.visuals_node)
        self.repainted.emit()

    def resizeGL(self, w: int, h: int) -> None:
        self.camera.widthViewport = w
        self.camera.heightViewport = h
        glViewport(0, 0, w, h)
        self.resizedGL.emit(w, h)

    def get_depth_image(self, scaled_for_viewing=True, return_type=np.uint16):
        """
         Get the depth map as an array for displaying
        :param scaled_for_viewing:
        :param return_type: either np.uint8 or np.uint16
        :return:
        """
        depth_image = self.get_depth_map()
        depth_image = (depth_image - depth_image.min()) / (depth_image.max() - depth_image.min())
        if scaled_for_viewing:
            indices = depth_image.nonzero()
            actual_image_pixels = depth_image[indices[0][:], indices[1][:]]
            actual_image_pixels = (actual_image_pixels - actual_image_pixels.min()) / (
                        actual_image_pixels.max() - actual_image_pixels.min())
            depth_image[indices] = actual_image_pixels

        depth_image = depth_image * np.iinfo(return_type).max
        return depth_image.astype(return_type)

    def get_depth_map(self):
        """ Get the depth value for each pixel in image """
        self.makeCurrent()
        width, height = self.width(), self.height()
        buff = glReadPixels(0, 0, width, height, GL_DEPTH_COMPONENT, GL_FLOAT)
        image = np.frombuffer(buff, dtype=np.float32)
        image = image.reshape(height, width)
        image = np.flipud(image)  # <-- image is now a numpy array you can use
        far, near = self.z_far.value, self.z_near.value
        return -far * near / (far + image * (near - far))

    def get_screen_shot(self, return_with_alpha=False, dtype: np.dtype = np.uint8):
        """
         Returns the RGB image array for the current view
        :param return_with_alpha:
        :param return_type:
        :return: numpy array representing the screen view with provided dtype
        """

        self.makeCurrent()
        # _, _, width, height = glGetIntegerv(GL_VIEWPORT)
        width, height = self.width(), self.height()
        if return_with_alpha:
            buff = glReadPixels(0, 0, width, height, GL_RGBA, self.DTYPES[dtype])
            image = np.frombuffer(buff, dtype=dtype)
            return np.flipud(image.reshape(height, width, 4))
        else:
            buff = glReadPixels(0, 0, width, height, GL_RGB, self.DTYPES[dtype])
            image = np.frombuffer(buff, dtype=dtype)
            return np.flipud(image.reshape(height, width, 3))

    def save_image(self, filename, dtype: np.dtype = np.uint16):
        """
        Save image to file
        :param filename: name of file to save image to. extension determines file type (i.e. "pic.png")
        """
        image = self.get_screen_shot(return_with_alpha=True, dtype=dtype)
        Image.fromarray(image).save(filename)

    def save_depth_image(self, filename, scaled=True, dtype: np.dtype = np.uint16):
        """
        Save pixel depth values to file
        :param filename: name of file to save depth image to. Extension determines file type (i.e. "pic.jpg")
        :param scaled: whether or not the depths are scaled for better viewing.
        """
        image = self.get_depth_image(scaled_for_viewing=scaled, return_type=dtype)
        Image.fromarray(image).save(filename)

    def save_depths(self, filename, dtype: np.dtype = np.uint16):
        """
        Save pixel depth values to file
        :param filename: name of file to save depths to. extension determines file type (i.e. "pic.jpg")
        """
        depths = self.get_depth_map(dtype=dtype)
        Image.fromarray(depths).save(filename)

    def get_screen_locations(self, points: List[List[float]]):
        """
        :param points: list of 3D world coordinate points
        :return: (x, y, z) positions in the screen coordinates
        """
        points = np.asarray(points)
        screen_positions = np.zeros((len(points), 3))
        for i in range(len(points)):
            screen_positions[i] = gluProject(points[i][0], points[i][1], points[i][2])
        return screen_positions

    def start_recording(self, video_file: str = 'test_vid.avi', save_separate_images=False):
        """
        Start recording screenshots to create a video.
        # TODO: add ffmpeg option for lossless recordings.
        :param video_file: path to video file to save.
        :param save_separate_images: whether or not to save each screenshot as it records. Better if running out of
                                     RAM for long videos, but is slower.
        """
        if self._recording:
            return
        self._save_img = save_separate_images
        if self._save_img:
            os.mkdir('tmp_screenshots')
        self._video_file = video_file
        self._recording = True
        self.repainted.connect(self._rec_save_img)

    def stop_recording(self):
        """
        Stop recording for video and combine into final video.
        TODO: allow for adjusting of fps setting.
        """
        if not self._recording:
            return
        self._recording = False
        self.repainted.disconnect(self._rec_save_img)
        if self._save_img:
            images = [os.path.join("tmp_screenshots", x) for x in os.listdir('tmp_screenshots')]
            times = [float(re.findall('(\d+\.\d+).png', x)[0]) for x in images]
            frame = cv2.imread(images[0])
        else:
            images = [x[1] for x in self._images]
            times = [x[0] for x in self._images]
            frame = images[0]

        avg = np.array(times)
        fps = 1 / (np.average(np.diff(avg)))
        height, width, layers = frame.shape
        video = cv2.VideoWriter(self._video_file, 0, fps, (width, height))
        if self._save_img:
            [video.write(cv2.imread(image)) for image in images]
        else:
            [video.write(image) for image in images]

        cv2.destroyAllWindows()
        video.release()
        if self._save_img:
            shutil.rmtree('tmp_screenshots')

    def _rec_save_img(self):
        if self._save_img:
            self.save_image(f'tmp_screenshots/{time.time()}.png', dtype=np.uint16)
        else:
            self._images.append((time.time(), self.get_screen_shot(dtype=np.uint16)))

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        self.key_pressed.emit(a0)
        super(QSofaGLView, self).keyPressEvent(a0)

    def keyReleaseEvent(self, a0: QKeyEvent) -> None:
        self.key_released.emit(a0)
        super(QSofaGLView, self).keyReleaseEvent(a0)

    def wheelEvent(self, a0: QWheelEvent) -> None:
        x, y = a0.x(), a0.y()
        screen_pt = self.camera.screenToWorldPoint([x, y, 0])
        current_pos = self.camera_position.array()
        current_pos = np.reshape(current_pos, (current_pos.shape[-1]))
        delta = np.array([screen_pt[0], screen_pt[1], screen_pt[2]]) - current_pos[:3]
        center = self.visuals_node.bbox.array()
        rate = np.linalg.norm(current_pos[:3] - center)

        if a0.angleDelta().y() > 0:
            delta *= rate
        elif a0.angleDelta().y() <=0:
            delta *= -rate

        self.update_position(current_pos[:3] + delta)
        self.update()

        self.scroll_event.emit(a0)
        super(QSofaGLView, self).wheelEvent(a0)

    def mousePressEvent(self, event: QMouseEvent, *args, **kwargs):
        if event.button() == Qt.MiddleButton:
            if self.dofs is not None:
                if self._temp_cam is None:
                    self._temp_cam = self.visuals_node.addObject("InteractiveCamera", name="tempcam", distance=10)
                current_pos = self.camera_position.array()
                current_pos = np.reshape(current_pos, (current_pos.shape[-1]))
                self._temp_cam.position = current_pos[:3]
                self._temp_cam.orientation = self.camera_orientation.array()
                self._temp_cam.init()

            self._rotating = True
            x, y = event.x(), event.y()
            self._rotate_screen_origin = [x, y]
            self.makeCurrent()
            width, height = self.width(), self.height()
            buff = glReadPixels(0, 0, width, height, GL_DEPTH_COMPONENT, GL_FLOAT)
            image = np.frombuffer(buff, dtype=np.float32)
            image = image.reshape(height, width)
            image = np.flipud(image)
            # get the fragment depth
            depth = image[y][x]
            # get projection matrix, view matrix and the viewport rectangle
            model_view = np.array(glGetDoublev(GL_MODELVIEW_MATRIX))
            proj = np.array(glGetDoublev(GL_PROJECTION_MATRIX))
            view = np.array(glGetIntegerv(GL_VIEWPORT))

            # unproject the point
            self._rotate_point = list(gluUnProject(y, x, depth, model_view, proj, view))

        elif event.button() == Qt.RightButton:
            self._panning = True
            x, y = event.x(), event.y()
            self._pan_screen_origin = [x, y]

    def mouseMoveEvent(self, event: QMouseEvent, *args, **kwargs):
        if self._rotating:
            x, y = event.x(), event.y()
            delta_x, delta_y = self._rotate_screen_origin[0] - x,  self._rotate_screen_origin[1] - y
            w, h = self.width(), self.height()
            x_percent, y_percent = 2*delta_x/w, 2*delta_y/h  # 2 is to make it go faster
            q = euler_to_quaternion(y_percent, x_percent, 0)
            self._rotate_screen_origin = [x, y]
            if self.dofs is not None:
                current_pos = self.camera_position.array()
                current_pos = np.reshape(current_pos, (current_pos.shape[-1]))
                self._temp_cam.position = current_pos[:3]
                self._temp_cam.orientation = self.camera_orientation.array()
                self._temp_cam.rotateWorldAroundPoint(q, self._rotate_point, list(self._temp_cam.orientation.toList()))
                self.update_position(self._temp_cam.position.array())
                self.update_orientation(self._temp_cam.orientation.array())
            else:
                self.camera.rotateWorldAroundPoint(q, self._rotate_point, self.camera_orientation.toList()[0])
            self.update()
        if self._panning:
            last = self.camera.screenToWorldPoint([self._pan_screen_origin[0], self._pan_screen_origin[1], 0])
            x, y = event.x(), event.y()
            new = self.camera.screenToWorldPoint([x, y, 0])
            dist = new - last
            dist *= -1000
            current_pos = self.camera_position.array()
            current_pos = np.reshape(current_pos, (current_pos.shape[-1]))
            self.update_position(current_pos[:3] + np.array([dist[0], dist[1], dist[2]]))
            self._pan_screen_origin = [x, y]
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent, *args, **kwargs):
        if event.button() == Qt.MiddleButton:
            self._rotating = False
            # self.visuals_node.removeObject(self._temp_cam)

        if event.button() == Qt.RightButton:
            self._panning = False

    def draw_spheres(self, positions, radii, colors, clear_existing=True):
        """
        :param clear_existing: whether or not to clear other spheres from the scene
        :param positions: list of x,y,z positions
        :param radii: list of radii for each sphere
        :param colors: list of colors [r, g, b] for each sphere
        """
        if clear_existing:
            self.clear_spheres()
        for i in range(len(positions)):
            new_node = self.visuals_node.addChild('sphere' + str(i))
            self.spheres.append(new_node)
            new_node.addObject("MeshObjLoader", name="loader" + str(i), filename="mesh/sphere.obj", scale=radii[i],
                               translation=positions[i])
            new_node.addObject("OglModel", name="i" + str(i), src="@loader" + str(i), color=colors[i])
        Sofa.Simulation.initVisual(self.visuals_node)
        Sofa.Simulation.initTextures(self.visuals_node)

    def clear_spheres(self):
        """
        clear all spheres from scene
        """
        [x.detachFromGraph() for x in self.spheres]
