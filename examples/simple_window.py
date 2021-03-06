from QSofaGLViewTools import create_simple_window, QSofaGLView
import Sofa
from SofaRuntime import PluginRepository, importPlugin
import time


def create_scene(root):
    """
    Function to fill a SOFA scene given a root node.
    Parameters
    ----------
    root : Sofa.Core.Node
            A SOFA node to fill with a scene.

    Returns
    -------
    None
    """

    importPlugin('SofaOpenglVisual')
    importPlugin("SofaGeneralLoader")
    importPlugin("SofaImplicitOdeSolver")
    importPlugin("SofaLoader")
    importPlugin("SofaSimpleFem")
    importPlugin("SofaBoundaryCondition")
    importPlugin("SofaMiscForceField")
    importPlugin("SofaBaseLinearSolver")
    importPlugin("SofaBaseMechanics")
    root.dt = 0.01
    root.gravity = [0, -1., 0]
    root.addObject("VisualStyle", displayFlags="showBehaviorModels showAll")
    root.addObject("MeshGmshLoader", name="meshLoaderCoarse", filename="../test/liver.msh")
    root.addObject("MeshObjLoader", name="meshLoaderFine", filename="mesh/liver-smooth.obj")
    root.addObject("EulerImplicitSolver")
    root.addObject("CGLinearSolver", iterations="200", tolerance="1e-09", threshold="1e-09")

    liver = root.addChild("liver")
    liver.addObject("TetrahedronSetTopologyContainer", name="topo", src="@../meshLoaderCoarse")
    liver.addObject("TetrahedronSetGeometryAlgorithms", template="Vec3d", name="GeomAlgo")
    liver.addObject("MechanicalObject", template="Vec3d", name="MechanicalModel", showObject="1", showObjectScale="3")
    liver.addObject("TetrahedronFEMForceField", name="fem", youngModulus="1000", poissonRatio="0.4", method="large")
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
    """
    Main function that will run as the typical python script
    Parameters
    ----------
    node : Sofa.Core.Node
    viewer : QSofaGLView
    """
    viewer.set_background_color([0, 0, 0, 1])
    input("\nPress enter to simulate 10 seconds:")
    start = time.time()
    last = start
    while time.time() - start < 10:
        while time.time() - last < node.getDt():
            time.sleep(0.0001)
        Sofa.Simulation.animate(node, node.getDt())
        # Sofa.Simulation.updateVisual(node)  # idk why this isn't working right now.
        last = time.time()
    input("\nPress enter to quit:")
    viewer.hide()
    viewer.close()


if __name__ == '__main__':
    root_node = Sofa.Core.Node("Root")  # create root node
    create_scene(root_node)  # fill the scene
    create_simple_window(main, root_node)  # create a window and call the main function
