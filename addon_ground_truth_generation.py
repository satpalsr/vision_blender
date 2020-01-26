# bl_info
bl_info = {
        "name":"Ground Truth Generation",
        "description":"Generate ground truth data (e.g., depth map) for Computer Vision applications.",
        "author":"Joao Cartucho, YP Li",
        "version":(1, 0),
        "blender":(2, 81, 16),
        "location":"PROPERTIES",
        "warning":"", # used for warning icon and text in addons panel
        "wiki_url":"",
        "support":"TESTING",
        "category":"Render"
    }

import bpy
import os
import numpy as np # TODO: check if Blender has numpy by default
from bpy.props import (StringProperty, # TODO: not being used
                   BoolProperty,
                   IntProperty, # TODO: not being used
                   FloatProperty, # TODO: not being used
                   EnumProperty, # TODO: not being used
                   PointerProperty
                   )
from bpy.types import (Panel,
                   Operator,
                   PropertyGroup
                   )
from bpy.app.handlers import persistent


def get_scene_resolution(scene):
    resolution_scale = (scene.render.resolution_percentage / 100.0)
    resolution_x = scene.render.resolution_x * resolution_scale # [pixels]
    resolution_y = scene.render.resolution_y * resolution_scale # [pixels]
    return int(resolution_x), int(resolution_y)


def get_sensor_size(sensor_fit, sensor_x, sensor_y):
    if sensor_fit == 'VERTICAL':
        return sensor_y
    return sensor_x


def get_sensor_fit(sensor_fit, size_x, size_y):
    if sensor_fit == 'AUTO':
        if size_x >= size_y:
            return 'HORIZONTAL'
        else:
            return 'VERTICAL'
    return sensor_fit


def get_camera_parameters_intrinsic(scene):
    """ Get intrinsic camera parameters: focal length and principal point. """
    # ref: https://blender.stackexchange.com/questions/38009/3x4-camera-matrix-from-blender-camera/120063#120063
    focal_length = scene.camera.data.lens # [mm]
    res_x, res_y = get_scene_resolution(scene)
    cam_data = scene.camera.data
    sensor_size_in_mm = get_sensor_size(cam_data.sensor_fit, cam_data.sensor_width, cam_data.sensor_height)
    sensor_fit = get_sensor_fit(
        cam_data.sensor_fit,
        scene.render.pixel_aspect_x * res_x,
        scene.render.pixel_aspect_y * res_y
    )
    pixel_aspect_ratio = scene.render.pixel_aspect_y / scene.render.pixel_aspect_x
    if sensor_fit == 'HORIZONTAL':
        view_fac_in_px = res_x
    else:
        view_fac_in_px = pixel_aspect_ratio * res_y
    pixel_size_mm_per_px = sensor_size_in_mm / focal_length / view_fac_in_px
    f_x = 1.0 / pixel_size_mm_per_px
    f_y = 1.0 / pixel_size_mm_per_px / pixel_aspect_ratio
    c_x = (res_x - 1) / 2.0 - cam_data.shift_x * view_fac_in_px
    c_y = (res_y - 1) / 2.0 + cam_data.shift_y * view_fac_in_px / pixel_aspect_ratio
    return f_x, f_y, c_x, c_y


# classes
class MyAddonProperties(PropertyGroup):
    # boolean to choose between saving ground truth data or not
    save_gt_data : BoolProperty(
        name = "Ground truth",
        default = True,
        description = "Save ground truth data",
    )


#class RENDER_OT_save_gt_data(bpy.types.Operator):
#    """ Saves the ground truth data that was created with the add-on """
#    bl_label = "Save ground truth data"
#    bl_idname = "RENDER_OT_" # How Blender refers to this operator

class GroundTruthGeneratorPanel(Panel):
    """Creates a Panel in the Output properties window for exporting ground truth data"""
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"


class RENDER_PT_gt_generator(GroundTruthGeneratorPanel):
    """Parent panel"""
    global intrinsic_mat
    bl_label = "Ground Truth Generator"
    bl_idname = "RENDER_PT_gt_generator"
    COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE'}#, 'BLENDER_WORKBENCH'} # TODO: see what happens when using the WORKBENCH render
    bl_options = {'DEFAULT_CLOSED'}


    def draw_header(self, context):
        rd = context.scene.render
        self.layout.prop(context.scene.my_addon, "save_gt_data", text="")


    def draw(self, context):
        layout = self.layout
        layout.active = context.scene.my_addon.save_gt_data

        layout.use_property_split = False
        layout.use_property_decorate = False  # No animation.

        # Get camera parameters
        """ show intrinsic parameters """
        layout.label(text="Intrinsic parameters [pixels]:")
        f_x, f_y, c_x, c_y = get_camera_parameters_intrinsic(context.scene)

        box_intr = self.layout.box()
        col_intr = box_intr.column()

        row_intr_0 = col_intr.split()
        row_intr_0.label(text=str(f_x))# "{}".format(round(f_x, 3))
        row_intr_0.label(text='0')
        row_intr_0.label(text=str(c_x))

        row_intr_1 = col_intr.split()
        row_intr_1.label(text='0')
        row_intr_1.label(text=str(f_y))
        row_intr_1.label(text=str(c_y))

        row_intr_2 = col_intr.split()
        row_intr_2.label(text='0')
        row_intr_2.label(text='0')
        row_intr_2.label(text='1')

        """ show extrinsic parameters """
        layout.label(text="Extrinsic parameters [pixels]:")

        cam_mat_world = context.scene.camera.matrix_world.inverted()
        
        box_ext = self.layout.box()
        col_ext = box_ext.column()

        row_ext_0 = col_ext.split()
        row_ext_0.label(text=str(cam_mat_world[0][0]))
        row_ext_0.label(text=str(cam_mat_world[0][1]))
        row_ext_0.label(text=str(cam_mat_world[0][2]))
        row_ext_0.label(text=str(cam_mat_world[0][3]))

        row_ext_1 = col_ext.split()
        row_ext_1.label(text=str(cam_mat_world[1][0]))
        row_ext_1.label(text=str(cam_mat_world[1][1]))
        row_ext_1.label(text=str(cam_mat_world[1][2]))
        row_ext_1.label(text=str(cam_mat_world[1][3]))

        row_ext_2 = col_ext.split()
        row_ext_2.label(text=str(cam_mat_world[2][0]))
        row_ext_2.label(text=str(cam_mat_world[2][1]))
        row_ext_2.label(text=str(cam_mat_world[2][2]))
        row_ext_2.label(text=str(cam_mat_world[2][3]))

classes = (
    RENDER_PT_gt_generator,
    MyAddonProperties,
    #RENDER_OT_save_gt_data
)


def get_node(tree, node_type, node_name):
    node_ind = tree.nodes.find(node_name)
    if node_ind == -1:
        v = tree.nodes.new(node_type)
        v.name = node_name
    else:
        v = tree.nodes[node_ind]
    return v


@persistent # TODO: not sure if I should be using @persistent
def load_handler_render_init(scene):
    #print("Initializing a render job...")
    # 1. Set-up Passes
    if not scene.use_nodes:
        scene.use_nodes = True
    if not scene.view_layers["View Layer"].use_pass_z:
        scene.view_layers["View Layer"].use_pass_z = True
    if not scene.view_layers["View Layer"].use_pass_normal:
        scene.view_layers["View Layer"].use_pass_normal = True

    if scene.render.engine == 'CYCLES':
        if not scene.view_layers["View Layer"].use_pass_object_index:
            scene.view_layers["View Layer"].use_pass_object_index = True
        if not scene.view_layers["View Layer"].use_pass_vector:
            scene.view_layers["View Layer"].use_pass_vector = True

    # 2. Set-up nodes
    tree = scene.node_tree
    rl = scene.node_tree.nodes["Render Layers"]
    node_norm_and_z = get_node(tree, "CompositorNodeViewer", "normal_and_zmap")

    if scene.render.engine == "CYCLES":
        node_obj_ind = get_node(tree, "CompositorNodeOutputFile", "obj_ind")
        node_opt_flow = get_node(tree, "CompositorNodeOutputFile", "opt_flow")
        path_render = scene.render.filepath
        node_obj_ind.base_path = os.path.join(path_render, "obj_ind_mask/")
        print(node_obj_ind.base_path)
        node_opt_flow.base_path = os.path.join(path_render, "vector/")

    # 3. Set-up links between nodes
    ## create new links if necessary
    links = tree.links
    ## Trick: we already have the RGB image so we can connect the Normal to Image
    ##        and the Z to the Alpha channel
    if not node_norm_and_z.inputs["Image"].is_linked:
        links.new(rl.outputs["Normal"], node_norm_and_z.inputs["Image"])
    if not node_norm_and_z.inputs["Alpha"].is_linked:
        links.new(rl.outputs["Depth"], node_norm_and_z.inputs["Alpha"])

    if scene.render.engine == "CYCLES":
        if not node_obj_ind.inputs["Image"].is_linked:
            links.new(rl.outputs["IndexOB"], node_obj_ind.inputs["Image"])
        ## The optical flow needs to be connected to both `Image` and `Alpha`
        if not node_opt_flow.inputs["Image"].is_linked:
            links.new(rl.outputs["Vector"], node_opt_flow.inputs["Image"])


@persistent # TODO: not sure if I should be using @persistent
def load_handler_after_rend_frame(scene): # TODO: not sure if this is the best place to put this function, should it be above the classes?
    """ This script runs after rendering each frame """
    # ref: https://blenderartists.org/t/how-to-run-script-on-every-frame-in-blender-render/699404/2
    # check if user wants to generate the ground truth data
    if scene.my_addon.save_gt_data:
        gt_dir_path = scene.render.filepath
        #print(gt_dir_path)
        # save ground truth data
        #print(scene.frame_current)
        """ Camera parameters """
        ### extrinsic
        cam_mat_world = bpy.context.scene.camera.matrix_world.inverted()
        extrinsic_mat = np.array(cam_mat_world)
        ### intrinsic
        f_x, f_y, c_x, c_y = get_camera_parameters_intrinsic(scene)
        intrinsic_mat = np.array([[f_x, 0, c_x],
                                  [0, f_y, c_y],
                                  [0,   0,   1]])
        """ Zmap + Normal """
        ## get data
        pixels = bpy.data.images['Viewer Node'].pixels
        #print(len(pixels)) # size = width * height * 4 (rgba)
        pixels_numpy = np.array(pixels[:])
        res_x, res_y = get_scene_resolution(scene)
        #   .---> y
        #   |
        #   |
        #   v
        #    x
        pixels_numpy.resize((res_y, res_x, 4)) # Numpy works with (y, x, channels)
        normal = pixels_numpy[:, :, 0:3]
        print("Normal:")
        print(normal[567, 1020])
        z = pixels_numpy[:, :, 3]
        """ Save data """
        # Blender by default assumes a padding of 4 digits
        out_path = os.path.join(gt_dir_path, '{:04d}.npz'.format(scene.frame_current))
        #print(out_path)
        np.savez_compressed(out_path,
                            intr=intrinsic_mat,
                            extr=extrinsic_mat,
                            normal_map=normal,
                            z_map=z
                           )
        # ref: https://stackoverflow.com/questions/35133317/numpy-save-some-arrays-at-once


# registration
def register():
    # register the classes
    for cls in classes:
        bpy.utils.register_class(cls)
    # register the properties
    bpy.types.Scene.my_addon = PointerProperty(type=MyAddonProperties)
    # register the function being called when rendering starts
    bpy.app.handlers.render_init.append(load_handler_render_init)
    # register the function being called after rendering each frame
    bpy.app.handlers.render_post.append(load_handler_after_rend_frame)


def unregister():
    # unregister the classes
    for cls in classes:
        bpy.utils.unregister_class(cls)
    # unregister the properties
    del bpy.types.Scene.my_addon
    # unregister the function being called when rendering each frame
    bpy.app.handlers.render_init.remove(load_handler_render_init)
    # unregister the function being called when rendering each frame
    bpy.app.handlers.render_post.remove(load_handler_after_rend_frame)

if __name__ == "__main__":
    register()

# reference: https://github.com/sobotka/blender/blob/662d94e020f36e75b9c6b4a258f31c1625573ee8/release/scripts/startup/bl_ui/properties_output.py
