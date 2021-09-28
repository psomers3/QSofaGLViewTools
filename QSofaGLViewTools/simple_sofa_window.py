from QSofaGLViewTools import QSofaGLView
from qtpy.QtWidgets import QApplication, QMainWindow
from qtpy.QtCore import Qt
import threading
import sys
import Sofa

QApplication.setAttribute(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


def create_simple_window(main_function, node, camera_kargs=None):
    """
    A function to create a super basic window for a SOFA sim. This is not the recommended way to use the viewer, but
    it is sufficient for quick prototyping of SOFA simulations.
    Parameters
    ----------
    main_function : callable
            A function that will be called in a second thread. This is meant to imitate your "main()" function. This
            function MUST take two inputs. The first input is the SOFA node (same as the input for this function) and
            the second is the created SofaGLView.
    node : Sofa.Core.Node
            The node to be used for generating the SOFA view. Usually just the root node for the scene.
    camera_kargs : dict
        A dictionary of Sofa.Components.BaseCamera construction parameters. This is forwarded to a call to
        QSofaGLView.create_view_and_camera().

    Returns
    -------
    None : Runs the SofaView and calls the main_function.
    """
    _app = QApplication(["SOFA simple window"])
    Sofa.Simulation.init(node)

    class MainWindow(QMainWindow):
        def __init__(self):
            super(MainWindow, self).__init__()
            if camera_kargs is None:
                self.viewer, self.camera, self.camera_dofs = QSofaGLView.create_view_and_camera(node, internal_refresh_freq=20)
            else:
                self.viewer, self.camera, self.camera_dofs = QSofaGLView.create_view_and_camera(node, camera_kwargs=camera_kargs, internal_refresh_freq=20)
            self.setCentralWidget(self.viewer)
            self.viewer.close = self.close

    _main_window = MainWindow()
    _main_window.show()
    _app_thread = threading.Thread(target=main_function, args=[node, _main_window.viewer], daemon=True)
    _app_thread.start()
    _app.exec_()



