# QSofaGLViewTools
A small PyQt widget library for viewing [SOFA simulation](https://www.sofa-framework.org/) cameras and controlling them.

### Install
```bash
git clone https://github.com/psomers3/QSofaGLViewTools.git && cd QSofaGLViewTools
pip install .
```

## Usage
The main widget to be used for creating the view is a `QSofaGLView` widget. It can be create in one of two ways:
```python
from QSofaGLViewTools import QSofaGLView

# create sofa scene ...
# create view with a camera in it called 'camera'
viewer = QSofaGLView(sofa_visuals_node=rootNode,  # SOFA node to calculate the visuals from
                     camera=rootNode.camera,  # A BaseCamera object
                     auto_place_camera=True,  # Let the view guess where the camera should be
                     internal_refresh_freq=20,  # Hz, set an internal timer to refresh the view. 
                     ) 
```
or, alternatively, a camera may be added to a node for you and simultaneously sets up a MechanicalObject to keep track of the degrees of freedom of the camera. This is handy to work with built-in Sofa engines (see example script EndoscopicLight.py)
```python
from QSofaGLViewTools import QSofaGLView

# create sofa scene ...
# create view without a camera:
# If no intial position is specified, then it will use auto_place_camera.
viewer, camera, camera_dofs = QSofaGLView.create_view_and_camera(rootNode,
                                                                 initial_position=[0, 15, 0, -0.707, 0., 0,0.707])
# returns: QSofaGLView, SOFA.Component.BaseCamera, SOFA.Component.MechanicalObject 
```
Use the scroll wheel (middle button) and right mouse buttons to control the view or with the arrow keys (rotations) and awsd keys (translations). To get the 3rd axes for both rotation and translation when using the keyboard, hold the ctrl key.

## Simple Window
There is a third usage option that is available for quick and dirty visualization of SOFA python scripts. The provided `create_simple_window` function can be used to launch a QSofaGLView (using `create_view_and_camera` in the background) parallel to the python script that is to be run. For this to work, the main python script needs to be encapsulated in a function. This is because the PYQT backend needs to run in the main thread and, therefore, the desired code needs to run from a different thread. 

Example usage as seen in the `examples/simple_window.py` example:

```python 
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
        Sofa.Simulation.updateVisual(node)  # TODO: Texture does not update with simple_window...
        last = time.time()
    input("\nPress enter to quit:")
    viewer.hide()
    viewer.close()


if __name__ == '__main__':
    root_node = Sofa.Core.Node("Root")  # create root node
    create_scene(root_node)  # fill the scene (assuming no camera is manually added)
    create_simple_window(main, root_node)  # create a window and call the main function
```

### Xbox Control
Use an xbox controller to control a view. Same use as keyboard controller. Not thoroughly tested...

```python
view_ctrl = QSofaViewXBoxController()
view_ctrl.set_viewers(viewer)
view_ctrl.start_auto_update()  # continuously sends a pyqt signal to paint the scene.
```