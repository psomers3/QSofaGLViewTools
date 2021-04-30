# QSofaGLViewTools
A small PyQt widget library for viewing [SOFA simulation](https://www.sofa-framework.org/) cameras and controlling them.

### Install
```bash
git clone https://github.com/psomers3/QSofaGLViewTools.git && cd QSofaGLViewTools
pip install .
```

## QSofaGLView
The main widget to be used for creating the view.
```python
viewer = QSofaGLView(sofa_visuals_node=rootNode, camera=rootNode.camera)  # camera is the name of a BaseCamera added to the scene
```
## QSofaViewKeyboardController
Use the keyboard to control the view from a camera with the arrow keys and awsd keys.
```python
view_ctrl = QSofaViewKeyboardController()
view_ctrl.set_viewers(viewer)
view_ctrl.start_auto_update()  # continuously sends a pyqt signal to paint the scene.
```
## QSofaViewXBoxController
Use an xbox controller to control a view. Same use as keyboard controller.
