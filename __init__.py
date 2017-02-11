#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

bl_info = {
    "name": "Rigify",
    "version": (0, 4),
    "author": "Nathan Vegdahl",
    "blender": (2, 66, 0),
    "description": "Automatic rigging from building-block components",
    "location": "Armature properties, Bone properties, View3d tools panel, Armature Add menu",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/"
                "Scripts/Rigging/Rigify",
    "tracker_url": "http://github.com/cessen/rigify/issues",
    "category": "Rigging"}


if "bpy" in locals():
    import importlib
    importlib.reload(generate)
    importlib.reload(ui)
    importlib.reload(utils)
    importlib.reload(metarig_menu)
    importlib.reload(rig_lists)
else:
    from . import utils, rig_lists, generate, ui, metarig_menu

import bpy


class RigifyName(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty()


class RigifyColorSet(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(name="Color Set", default=" ")
    active = bpy.props.FloatVectorProperty(
                                   name="object_color",
                                   subtype='COLOR',
                                   default=(1.0, 1.0, 1.0),
                                   min=0.0, max=1.0,
                                   description="color picker"
                                   )
    normal = bpy.props.FloatVectorProperty(
                                   name="object_color",
                                   subtype='COLOR',
                                   default=(1.0, 1.0, 1.0),
                                   min=0.0, max=1.0,
                                   description="color picker"
                                   )
    select = bpy.props.FloatVectorProperty(
                                   name="object_color",
                                   subtype='COLOR',
                                   default=(1.0, 1.0, 1.0),
                                   min=0.0, max=1.0,
                                   description="color picker"
                                   )
    standard_colors_lock = bpy.props.BoolProperty(default=True)


class RigifySelectionColors(bpy.types.PropertyGroup):

    select = bpy.props.FloatVectorProperty(
                                           name="object_color",
                                           subtype='COLOR',
                                           default=(0.314, 0.784, 1.0),
                                           min=0.0, max=1.0,
                                           description="color picker"
                                           )

    active = bpy.props.FloatVectorProperty(
                                           name="object_color",
                                           subtype='COLOR',
                                           default=(0.549, 1.0, 1.0),
                                           min=0.0, max=1.0,
                                           description="color picker"
                                           )


class RigifyParameters(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty()


class RigifyArmatureLayer(bpy.types.PropertyGroup):

    def get_group(self):
        return self['group_prop']

    def set_group(self, value):
        arm = bpy.context.object.data
        if value > len(arm.rigify_colors):
            self['group_prop'] = len(arm.rigify_colors)
        else:
            self['group_prop'] = value

    name = bpy.props.StringProperty(name="Layer Name", default=" ")
    row = bpy.props.IntProperty(name="Layer Row", default=1, min=1, max=32, description='UI row for this layer')
    set = bpy.props.BoolProperty(name="Selection Set", default=False, description='Add Selection Set for this layer')
    group = bpy.props.IntProperty(name="Bone Group", default=0, min=0, max=32,
                                  get=get_group, set=set_group, description='Assign Bone Group to this layer')

##### REGISTER #####

def register():
    ui.register()
    metarig_menu.register()

    bpy.utils.register_class(RigifyName)
    bpy.utils.register_class(RigifyParameters)

    bpy.utils.register_class(RigifyColorSet)
    bpy.utils.register_class(RigifySelectionColors)
    bpy.utils.register_class(RigifyArmatureLayer)
    bpy.types.Armature.rigify_layers = bpy.props.CollectionProperty(type=RigifyArmatureLayer)

    bpy.types.PoseBone.rigify_type = bpy.props.StringProperty(name="Rigify Type", description="Rig type for this bone")
    bpy.types.PoseBone.rigify_parameters = bpy.props.PointerProperty(type=RigifyParameters)

    bpy.types.Armature.rigify_colors = bpy.props.CollectionProperty(type=RigifyColorSet)

    bpy.types.Armature.rigify_selection_colors = bpy.props.PointerProperty(type=RigifySelectionColors)

    bpy.types.Armature.rigify_colors_index = bpy.props.IntProperty(default=-1)
    bpy.types.Armature.rigify_colors_lock = bpy.props.BoolProperty(default=True)
    bpy.types.Armature.rigify_theme_to_add = bpy.props.EnumProperty(items=(('THEME01', 'THEME01', ''),
                                                                          ('THEME02', 'THEME02', ''),
                                                                          ('THEME03', 'THEME03', ''),
                                                                          ('THEME04', 'THEME04', ''),
                                                                          ('THEME05', 'THEME05', ''),
                                                                          ('THEME06', 'THEME06', ''),
                                                                          ('THEME07', 'THEME07', ''),
                                                                          ('THEME08', 'THEME08', ''),
                                                                          ('THEME09', 'THEME09', ''),
                                                                          ('THEME10', 'THEME10', ''),
                                                                          ('THEME11', 'THEME11', ''),
                                                                          ('THEME12', 'THEME12', ''),
                                                                          ('THEME13', 'THEME13', ''),
                                                                          ('THEME14', 'THEME14', ''),
                                                                          ('THEME15', 'THEME15', ''),
                                                                          ('THEME16', 'THEME16', ''),
                                                                          ('THEME17', 'THEME17', ''),
                                                                          ('THEME18', 'THEME18', ''),
                                                                          ('THEME19', 'THEME19', ''),
                                                                          ('THEME20', 'THEME20', '')
                                                                           ), name='Theme')

    IDStore = bpy.types.WindowManager
    IDStore.rigify_collection = bpy.props.EnumProperty(items=rig_lists.col_enum_list, default="All",
                                                       name="Rigify Active Collection",
                                                       description="The selected rig collection")

    IDStore.rigify_types = bpy.props.CollectionProperty(type=RigifyName)
    IDStore.rigify_active_type = bpy.props.IntProperty(name="Rigify Active Type", description="The selected rig type")

    # Add rig parameters
    for rig in rig_lists.rig_list:
        r = utils.get_rig_type(rig)
        try:
            r.add_parameters(RigifyParameters)
        except AttributeError:
            pass


def unregister():
    del bpy.types.PoseBone.rigify_type
    del bpy.types.PoseBone.rigify_parameters

    IDStore = bpy.types.WindowManager
    del IDStore.rigify_collection
    del IDStore.rigify_types
    del IDStore.rigify_active_type

    bpy.utils.unregister_class(RigifyName)
    bpy.utils.unregister_class(RigifyParameters)
    bpy.utils.unregister_class(RigifyArmatureLayer)

    metarig_menu.unregister()
    ui.unregister()
