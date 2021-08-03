# QSofaGLViewTools
A small PyQt widget library for viewing [SOFA simulation](https://www.sofa-framework.org/) cameras and controlling them.

### Install
```bash
git clone https://github.com/psomers3/QSofaGLViewTools.git && cd QSofaGLViewTools
pip install .
```

## QSofaGLView
The main widget to be used for creating the view. This requires just the node for visualization and the camera object to display.
```python
viewer = QSofaGLView(sofa_visuals_node=rootNode, camera=rootNode.camera)  # camera is the name of a BaseCamera added to the scene
```
Alternatively, a camera may be added to a node for you and simultaneously sets up a MechanicalObject to keep track of the degrees of freedom of the camera. This is handy to work with built-in Sofa engines (see example script EndoscopicLight.py)
```python
viewer, camera, camera_dofs = QSofaGLView.create_view_and_camera(rootNode, initial_position=[0, 15, 0, -0.70710678, 0., 0,0.70710678])
```

## QSofaViewKeyboardController
Use the keyboard to control the view from a camera with the arrow keys (rotations) and awsd keys (translations). To get the 3rd axes for both rotation and translation, hold the ctrl key.
```python
view_ctrl = QSofaViewKeyboardController()
view_ctrl.set_viewers(viewer)
view_ctrl.start_auto_update()  # continuously sends a pyqt signal to paint the scene.
```
## QSofaViewXBoxController
Use an xbox controller to control a view. Same use as keyboard controller.
