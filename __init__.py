bl_info = {
    "name": "ICT Face Kit",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > ICT Face Kit",
    "description": "Import ICT face models with blendshapes",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy
from . operators.face_model_loader import BrowseFaceModel, ICTFaceKitPanel

classes = (
    BrowseFaceModel,
    ICTFaceKitPanel,
)

def register():
    # Ensure OBJ importer is enabled
    if not hasattr(bpy.ops.import_scene, 'obj'):
        bpy.ops.preferences.addon_enable(module="io_scene_obj")
    
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()