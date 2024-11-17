# operators/face_model_loader.py
import os
import json
import itertools
import logging

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def import_obj(filepath):
    """Import OBJ file using the appropriate operator based on Blender version"""
    logger.debug(f"Attempting to import OBJ: {filepath}")
    
    # Try the new Blender 4.x operator first
    if hasattr(bpy.ops.wm, 'obj_import'):
        logger.debug("Using Blender 4.x OBJ importer")
        return bpy.ops.wm.obj_import(filepath=filepath)
    
    # Fall back to the old operator for older versions
    elif hasattr(bpy.ops.import_scene, 'obj'):
        logger.debug("Using legacy OBJ importer")
        return bpy.ops.import_scene.obj(filepath=filepath)
    
    else:
        raise ImportError("No OBJ importer found in Blender")

def loadICTFaceModel(folderpath):
    logger.info(f"Starting model load from directory: {folderpath}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    
    # Define names to use
    face_model_name = "ICTFaceModel"
    generic_neutral_filename = "generic_neutral_mesh.obj"
    identity_morph_target_name = "identity{:03d}"
    config_filename = "vertex_indices.json"
    
    # Verify folder path exists
    logger.debug(f"Checking if directory exists: {folderpath}")
    if not os.path.isdir(folderpath):
        logger.error(f"Invalid directory path: {folderpath}")
        raise ValueError(f"Invalid directory path: {folderpath}")
        
    # Specify paths
    generic_neutral_filepath = os.path.join(folderpath, generic_neutral_filename)
    config_filepath = os.path.join(folderpath, config_filename)
    
    logger.debug(f"Neutral mesh path: {generic_neutral_filepath}")
    logger.debug(f"Config file path: {config_filepath}")
    
    # Verify required files exist
    if not os.path.exists(generic_neutral_filepath):
        logger.error(f"Cannot find neutral mesh: {generic_neutral_filepath}")
        raise FileNotFoundError(f"Cannot find neutral mesh: {generic_neutral_filepath}")
    if not os.path.exists(config_filepath):
        logger.error(f"Cannot find config file: {config_filepath}")
        raise FileNotFoundError(f"Cannot find config file: {config_filepath}")
    
    # Load settings
    try:
        with open(config_filepath) as jsonContent:
            config = json.load(jsonContent)    
        if not config:
            logger.error("Empty configuration file")
            raise ValueError("Empty configuration file")
        logger.debug(f"Loaded config: {config}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {config_filepath}")
        logger.error(f"JSON error: {str(e)}")
        raise ValueError(f"Invalid JSON in config file: {config_filepath}")
    
    # Load generic neutral
    try:
        logger.info(f"Attempting to import neutral mesh: {generic_neutral_filepath}")
        
        # Import the neutral mesh
        import_result = import_obj(generic_neutral_filepath)
        logger.debug(f"Import result: {import_result}")
        
        if not bpy.context.selected_objects:
            logger.error("No objects selected after import")
            raise ImportError("Failed to import neutral mesh")
            
        face_model_neutral_object = bpy.context.selected_objects[0]
        face_model_neutral_object.name = face_model_name
        logger.info("Successfully imported neutral mesh")
        
    except Exception as e:
        logger.error(f"Error importing neutral mesh: {str(e)}")
        logger.error("Import error details:", exc_info=True)
        raise ImportError(f"Error importing neutral mesh: {str(e)}")
    
    # Load expression morph targets
    expression_names = []
    expression_models = []
    for expression_name in config['expressions']:
        filename = expression_name + '.obj'
        filepath = os.path.join(folderpath, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Expression morph target not found: {filepath}")
            continue
            
        try:
            logger.info(f"Reading expression morph target: {expression_name}")
            import_obj(filepath)
            
            if not bpy.context.selected_objects:
                logger.warning(f"Failed to import expression {expression_name}")
                continue
                
            imported_object = bpy.context.selected_objects[0]
            imported_object.name = expression_name
        
            expression_names.append(expression_name)
            expression_models.append(imported_object)
        except Exception as e:
            logger.error(f"Error importing expression {expression_name}: {str(e)}")
            continue
    
    identity_names = []
    identity_models = []
    # Load identity morph targets
    for identity_num in itertools.count():
        identity_name = identity_morph_target_name.format(identity_num)
        identity_filename = identity_name + ".obj"
        filepath = os.path.join(folderpath, identity_filename)
        
        if not os.path.exists(filepath):
            if identity_num == 0:
                logger.info("No identity morph targets found")
            else:
                logger.info(f"No more identity morph targets found after {identity_num-1}")
            break
            
        try:
            logger.info(f"Reading identity morph target: {identity_name}")
            import_obj(filepath)
            
            if not bpy.context.selected_objects:
                logger.warning(f"Failed to import identity {identity_name}")
                continue
                
            imported_object = bpy.context.selected_objects[0]
            imported_object.name = identity_name
        
            identity_names.append(identity_name)
            identity_models.append(imported_object)
        except Exception as e:
            logger.error(f"Error loading identity morph target {identity_name}: {str(e)}")
            break
    
    if not expression_models and not identity_models:
        raise ValueError("No valid morph targets found in directory")
    
    # Select all shape models
    for expression_model in expression_models:
        expression_model.select_set(True)
    for identity_model in identity_models:
        identity_model.select_set(True)
    bpy.context.view_layer.objects.active = face_model_neutral_object
   
    # Create blendshapes
    bpy.ops.object.join_shapes()

    # Delete selected shape objects
    bpy.ops.object.delete()
    
    return len(expression_models), len(identity_models)


class BrowseFaceModel(Operator, ImportHelper):
    bl_idname = "ict_face_kit.browsemodel"
    bl_label = "Load model"
    
    filename_ext = ""  # Allow directory selection
    dirpath: StringProperty(
        name="Directory Path",
        description="Choose directory with the face model files",
        default="",
        subtype='DIR_PATH'
    )
    
    filter_glob: StringProperty(
        default="",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        try:
            # Log the filepath and directory
            logger.info(f"Selected filepath: {self.filepath}")
            directory = os.path.dirname(self.filepath)
            logger.info(f"Extracted directory: {directory}")
            
            # Check if directory exists
            logger.debug(f"Directory exists: {os.path.exists(directory)}")
            logger.debug(f"Is directory: {os.path.isdir(directory)}")
            
            # Try to load the model
            num_expressions, num_identities = loadICTFaceModel(directory)
            logger.info(f"Successfully loaded {num_expressions} expressions and {num_identities} identities")
            self.report({'INFO'}, f"Face model loaded successfully with {num_expressions} expressions and {num_identities} identities")
            
        except Exception as e:
            logger.error("Error in execute:", exc_info=True)
            self.report({'ERROR'}, f"Error loading face model: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}


class ICTFaceKitPanel(bpy.types.Panel):
    bl_idname = "panel.ict_face_kit_panel"
    bl_label = "ICT FaceKit"
    
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ICT FaceKit'

    def draw(self, context):
        self.layout.operator("ict_face_kit.browsemodel", icon='FILEBROWSER', text="Load Face Model")