try:
    from qtpy.QtWidgets import *
    from qtpy.QtCore import *
    from qtpy.QtGui import *
except Exception as e:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget
    Signal = pyqtSignal
from QSofaGLViewTools import QSofaGLView, QSofaViewKeyboardController
import sys
import Sofa.Core as SCore
import Sofa.Simulation as SSim
from SofaRuntime import PluginRepository, importPlugin


class SofaSim(QObject):
    animation_end = Signal()
    animation_start = Signal()

    def __init__(self):
        super(SofaSim, self).__init__()
        # Register all the common component in the factory.
        importPlugin('SofaOpenglVisual')
        importPlugin("SofaGeneralLoader")
        importPlugin("SofaImplicitOdeSolver")
        importPlugin("SofaLoader")
        importPlugin("SofaSimpleFem")
        importPlugin("SofaBoundaryCondition")
        importPlugin("SofaMiscForceField")
        importPlugin("SofaBaseLinearSolver")
        importPlugin("SofaBaseMechanics")
        self.root = SCore.Node("Root")
        root = self.root
        root.gravity = [0, -1., 0]
        root.addObject("VisualStyle", displayFlags="showBehaviorModels showAll")
        root.addObject("MeshGmshLoader", name="meshLoaderCoarse",
                       filename="../test/liver.msh")
        root.addObject("MeshObjLoader", name="meshLoaderFine",
                       filename="mesh/liver-smooth.obj")

        root.addObject("EulerImplicitSolver")
        root.addObject("CGLinearSolver", iterations="200",
                       tolerance="1e-09", threshold="1e-09")

        liver = root.addChild("liver")

        liver.addObject("TetrahedronSetTopologyContainer",
                        name="topo", src="@../meshLoaderCoarse")
        liver.addObject("TetrahedronSetGeometryAlgorithms",
                        template="Vec3d", name="GeomAlgo")
        liver.addObject("MechanicalObject",
                        template="Vec3d",
                        name="MechanicalModel", showObject="1", showObjectScale="3")

        liver.addObject("TetrahedronFEMForceField", name="fem", youngModulus="1000",
                        poissonRatio="0.4", method="large")

        liver.addObject("MeshMatrixMass", massDensity="1")
        liver.addObject("FixedConstraint", indices="2 3 50")
        visual = liver.addChild("visual")
        visual.addObject('MeshObjLoader', name="meshLoader_0", filename="mesh/liver-smooth.obj", handleSeams="1")
        visual.addObject('OglModel', name="VisualModel", src="@meshLoader_0", color='red')
        visual.addObject('BarycentricMapping', input="@..", output="@VisualModel", name="visual mapping")

        # place light and a camera
        self.root.addObject("LightManager")
        self.root.addObject("DirectionalLight", direction=[0, 1, 0])
        self.root.addObject("InteractiveCamera", name="camera", fieldOfView=45, computeZClip=False)

        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.step_sim)
        self.simulation_timer.setInterval(self.root.getDt())
        self.is_animating = False

    def init_sim(self):
        # start the simulator
        SSim.init(self.root)

    def start_sim(self):
        self.simulation_timer.start()
        self.is_animating = True

    def stop_sim(self):
        self.simulation_timer.stop()
        self.is_animating = False

    def step_sim(self):
        self.animation_start.emit()
        SSim.animate(self.root, self.root.getDt())
        SSim.updateVisual(self.root)  # updates the visual mappings
        self.animation_end.emit()

    def reset(self):
        SSim.reset(self.root)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.sofa_sim = SofaSim()  # class to hold the scene
        self.sofa_sim.init_sim()  # initialize the scene

        # create an opengl view to display a node from sofa and control a camera
        self.sofa_view = QSofaGLView(sofa_visuals_node=self.sofa_sim.root,
                                     camera=self.sofa_sim.root.camera,
                                     auto_place_camera=True,
                                     internal_refresh_freq=20)

        self.sofa_view.set_background_color([0, 0, 0, 0])  # [1,1,1,1] for white

        # set the view to be the main widget of the window. In the future, this should be done in a layout
        self.setCentralWidget(self.sofa_view)

        self.sofa_sim.animation_end.connect(self.sofa_view.update)  # set a qt signal to update the view after sim step

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.sofa_sim.is_animating:
                self.sofa_sim.stop_sim()
            else:
                self.sofa_sim.start_sim()
        elif event.key() == Qt.Key.Key_J:
            self.sofa_view.save_image("test.png")
        elif event.key() == Qt.Key.Key_R:
            self.sofa_sim.reset()

        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        super(MainWindow, self).keyPressEvent(event)


if __name__ == '__main__':
    app = QApplication(['Yo'])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
