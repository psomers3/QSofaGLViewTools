from QSofaGLViewTools import create_simple_window, QSofaGLView
import Sofa
from SofaRuntime import PluginRepository, importPlugin
import time


def create_scene(root):
    importPlugin('SofaOpenglVisual')
    importPlugin("SofaGeneralLoader")
    importPlugin("SofaImplicitOdeSolver")
    importPlugin("SofaLoader")
    importPlugin("SofaSimpleFem")
    importPlugin("SofaBoundaryCondition")
    importPlugin("SofaMiscForceField")
    importPlugin("SofaBaseLinearSolver")
    importPlugin("SofaBaseMechanics")
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
    visual.addObject('BarycentricMapping', input="@../MechanicalModel", output="@VisualModel", name="visual mapping")

    # place light and a camera
    root.addObject("LightManager")
    root.addObject("DirectionalLight", direction=[0, 1, 0])


def main(node: Sofa.Core.Node, viewer: QSofaGLView):
    viewer.set_background_color([0,0,0,1])
    node.init()
    Sofa.Simulation.updateVisual(node)
    input("\nPress enter to simulate 10 seconds:")
    start = time.time()
    last = start
    while time.time() - start < 10:
        Sofa.Simulation.animate(node, time.time() - last)
        Sofa.Simulation.updateVisual(node)
        last = time.time()
        time.sleep(0.01)
    input("\nPress enter to quit:")
    viewer.hide()
    viewer.close()


if __name__ == '__main__':
    root_node = Sofa.Core.Node("Root")
    create_scene(root_node)
    create_simple_window(main, root_node)