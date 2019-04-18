#######################################################################################################################
# Bendy jaws contruction rules:
# - make a main bone with a connected children. The tail of the connected children
# is the chin point its head is the jaw pivot
# - make 4 chains for the mouth of the same length. Parent them unconnected to the main bone
#######################################################################################################################

import bpy
from rna_prop_ui import rna_idprop_ui_prop_get

from ...utils import copy_bone, align_bone_z_axis, align_bone_y_axis
from ...utils import strip_org, make_mechanism_name
from ...utils import MetarigError
from ...utils import make_constraints_from_string, create_cube_widget
from ..widgets import create_jaw_widget
from .meshy_rig import MeshyRig
from .control_layers_generator import ControlLayersGenerator
from mathutils import Vector

script = """
all_controls   = [%s]
jaw_ctrl_name  = '%s'

if is_selected(all_controls):
    layout.prop(pose_bones[jaw_ctrl_name],  '["%s"]', slider=True)
"""


class Rig(MeshyRig):

    def __init__(self, obj, bone_name, params):

        super().__init__(obj, bone_name, params)

        self.main_mch = self.get_jaw()
        self.lip_len = None
        self.mouth_bones = self.get_mouth()
        self.rotation_mode = params.rotation_mode

        self.layer_generator = ControlLayersGenerator(self)

    def get_jaw(self):
        """
        Gets the main bone of the jaw-chin chain
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        name = ""
        for child in edit_bones[self.bones['org'][0]].children:
            if child.use_connect:
                name = child.name

        return name

    def get_mouth(self):
        """
        Returns the main bones of the mouth chain
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        lip_bones = []
        for child in edit_bones[self.bones['org'][0]].children:
            if not child.use_connect:
                lip_bones.append(child.name)

        # Rule check
        if len(lip_bones) != 4:
            raise MetarigError("Exactly 4 disconnected chains (lips) must be parented to main bone")

        mouth_bones_dict = {'top': [], 'bottom': []}
        self.lip_len = len(self.get_chain_bones(lip_bones[0]))

        # Check all half-lips have same length
        for lip in lip_bones:
            if len(self.get_chain_bones(lip)) != self.lip_len:
                raise MetarigError("All lip chains must be the same length")

        m_b_head_positions = [edit_bones[name].head for name in lip_bones]
        head_sum = m_b_head_positions[0]
        for h in m_b_head_positions[1:]:
            head_sum = head_sum + h
        mouth_center = head_sum / 4

        chin_tail_position = edit_bones[self.main_mch].tail
        mouth_chin_distance = (mouth_center - chin_tail_position).magnitude
        for m_b in lip_bones:
            head = edit_bones[m_b].head
            if (head - chin_tail_position).magnitude < mouth_chin_distance:
                mouth_bones_dict['bottom'].append(m_b)
            elif (head - chin_tail_position).magnitude > mouth_chin_distance:
                mouth_bones_dict['top'].append(m_b)

        if not (len(mouth_bones_dict['top']) == len(mouth_bones_dict['bottom']) == 2):
            raise MetarigError("Badly drawn mouth")

        return mouth_bones_dict

    def orient_org_bones(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        if self.rotation_mode == 'automatic':
            alignment_axis = edit_bones[self.main_mch].tail - edit_bones[self.base_bone].head
            align_bone_z_axis(self.obj, self.main_mch, alignment_axis)

    def create_mch(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        main_bone_name = strip_org(self.bones['org'][0])
        mouth_lock_name = make_mechanism_name(main_bone_name + "_lock")
        mouth_lock = copy_bone(self.obj, self.main_mch, mouth_lock_name)

        self.bones['jaw_mch'] = dict()
        self.bones['jaw_mch']['mouth_lock'] = mouth_lock
        self.bones['jaw_mch']['jaw_masters'] = []

        jaw_masters_number = self.lip_len + 3

        for i in range(0, jaw_masters_number):
            jaw_m_name = make_mechanism_name("jaw_master")
            jaw_m = copy_bone(self.obj, self.main_mch, jaw_m_name)
            div_len = (edit_bones[mouth_lock].length/(jaw_masters_number + 1))
            edit_bones[jaw_m].length = (jaw_masters_number - i) * div_len
            edit_bones[jaw_m].use_connect = False

            self.bones['jaw_mch']['jaw_masters'].append(jaw_m)

        # create remaining subchain mch-s
        super().create_mch()

    def create_def(self):
        # create remaining subchain def-s
        super().create_def()

    def create_controls(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        self.bones['jaw_ctrl'] = dict()

        jaw_ctrl_name = "jaw_master"

        jaw_ctrl = copy_bone(self.obj, self.main_mch, jaw_ctrl_name)
        self.bones['jaw_ctrl']['jaw'] = jaw_ctrl
        edit_bones[jaw_ctrl].use_connect = False

        super().create_controls()

        ctrls = self.get_all_ctrls()

        for ctrl in ctrls:
            align_bone_y_axis(self.obj, ctrl, Vector((0, 0, 1)))

    def make_constraints(self):
        """
        Make constraints
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        owner = pose_bones[self.bones['jaw_mch']['mouth_lock']]
        subtarget = self.bones['jaw_ctrl']['jaw']
        make_constraints_from_string(owner, self.obj, subtarget, "CT0.2WW0.0")

        influence_div = 1/len(self.bones['jaw_mch']['jaw_masters'])
        for i, j_m in enumerate(self.bones['jaw_mch']['jaw_masters']):
            owner = pose_bones[j_m]
            subtarget = self.bones['jaw_ctrl']['jaw']
            influence = 1 - i * influence_div
            make_constraints_from_string(owner, self.obj, subtarget, "CT%sWW0.0" % influence)
            if j_m != self.bones['jaw_mch']['jaw_masters'][-1]:
                owner = pose_bones[j_m]
                subtarget = self.bones['jaw_mch']['mouth_lock']
                make_constraints_from_string(owner, self.obj, subtarget, "CT0.0WW0.0")
            # add limits on upper_lip jaw_master
            if j_m == self.bones['jaw_mch']['jaw_masters'][-2]:
                make_constraints_from_string(owner, self.obj, "", "LLmY0mZ0#LRmX0MX%f" % (3.14/2))

        lip_bones = []
        lip_bones.extend(self.mouth_bones['top'])
        lip_bones.extend(self.mouth_bones['bottom'])

        for lip_bone in lip_bones:
            lip_bone = strip_org(lip_bone)
            total_len = 0
            influence_share = []
            for def_b in self.bones['def'][lip_bone]:
                total_len += pose_bones[def_b].length
                influence_share.append(total_len)
            influence_share = [val / total_len for val in influence_share]
            for i, ctrl in enumerate(self.bones['ctrl'][lip_bone][1:-1]):
                owner = pose_bones[self.bones['ctrl'][lip_bone][i+1]]
                subtarget = self.bones['ctrl'][lip_bone][-1]
                infl = influence_share[i]
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLLO0.0" % infl)
                subtarget = self.bones['ctrl'][lip_bone][0]
                infl = 1 - influence_share[i]
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLLO0.0" % infl)
                make_constraints_from_string(owner, self.obj, subtarget, "CR1.0LLO0.0")
                make_constraints_from_string(owner, self.obj, subtarget, "CS1.0LLO0.0")

        # make the standard bendy rig constraints
        super().make_constraints()

    def make_drivers(self):

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        # Add mouth_lock property on jaw_master
        jaw_master = pose_bones[self.bones['jaw_ctrl']['jaw']]
        prop_name = 'mouth_lock'
        jaw_master[prop_name] = 0.0
        prop = rna_idprop_ui_prop_get(jaw_master, prop_name)
        prop["min"] = 0.0
        prop["max"] = 1.0
        prop["soft_min"] = 0.0
        prop["soft_max"] = 1.0
        prop["description"] = prop_name

        for bone in self.bones['jaw_mch']['jaw_masters'][:-1]:
            drv = pose_bones[bone].constraints[1].driver_add("influence").driver
            drv.type = 'SUM'

            var = drv.variables.new()
            var.name = prop_name
            var.type = "SINGLE_PROP"
            var.targets[0].id = self.obj
            var.targets[0].data_path = jaw_master.path_from_id() + '[' + '"' + prop_name + '"' + ']'

        all_ctrls = self.control_snapper.flatten(self.bones['ctrl'])
        all_ctrls.append(self.bones['jaw_ctrl']['jaw'])

        controls_string = ", ".join(["'" + x + "'" for x in all_ctrls])

        return [script % (controls_string, self.bones['jaw_ctrl']['jaw'], prop_name)]

    def parent_bones(self):
        """
        Parent jaw bones
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        # Parenting to jaw MCHs
        jaw_masters = self.bones['jaw_mch']['jaw_masters']
        b_lip_1 = strip_org(self.mouth_bones['bottom'][0])     # 1st bottom lip quarter
        b_lip_2 = strip_org(self.mouth_bones['bottom'][1])

        for i, lip_def in enumerate(self.bones['def'][b_lip_1]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrl_by_index(b_lip_1, i)
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i]]
            if lip_def == self.bones['def'][b_lip_1][-1]:
                lip_ctrl = self.get_ctrl_by_index(b_lip_1, i+1)
                edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i + 1]]

        for i, lip_def in enumerate(self.bones['def'][b_lip_2]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrl_by_index(b_lip_2, i)
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i]]
            if lip_def == self.bones['def'][b_lip_2][-1]:
                lip_ctrl = self.get_ctrl_by_index(b_lip_2, i+1)
                edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i + 1]]

        t_lip_1 = strip_org(self.mouth_bones['top'][0])     # 1st top lip quarter
        t_lip_2 = strip_org(self.mouth_bones['top'][1])

        for i, lip_def in enumerate(self.bones['def'][t_lip_1]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrl_by_index(t_lip_1, i)
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[-2]]
            if lip_def == self.bones['def'][t_lip_1][-1]:
                lip_ctrl = self.get_ctrl_by_index(t_lip_1, i+1)
                edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i + 1]]

        for i, lip_def in enumerate(self.bones['def'][t_lip_2]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrl_by_index(t_lip_2, i)
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[-2]]
            if lip_def == self.bones['def'][t_lip_2][-1]:
                lip_ctrl = self.get_ctrl_by_index(t_lip_2, i+1)
                edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i + 1]]

        # parenting what's connected to main jaw mch to jaw ctrl
        for child in edit_bones[self.main_mch].children:
            child.parent = edit_bones[self.bones['jaw_ctrl']['jaw']]

        super().parent_bones()

    def aggregate_ctrls(self):
        self.control_snapper.aggregate_ctrls(same_parent=False)

    def assign_layers(self):

        top_main = self.get_ctrl_by_index(strip_org(self.mouth_bones['top'][0]), 0)
        corner_1 = self.get_ctrl_by_index(strip_org(self.mouth_bones['top'][0]), -1)
        corner_2 = self.get_ctrl_by_index(strip_org(self.mouth_bones['top'][1]), -1)
        bottom_main = self.get_ctrl_by_index(strip_org(self.mouth_bones['bottom'][0]), 0)

        primary_ctrls = []
        primary_ctrls.append(top_main)
        primary_ctrls.append(corner_1)
        primary_ctrls.append(corner_2)
        primary_ctrls.append(bottom_main)
        primary_ctrls.append(self.bones['jaw_ctrl']['jaw'])

        all_ctrls = self.control_snapper.flatten(self.bones['ctrl'])
        self.layer_generator.assign_layer(primary_ctrls, all_ctrls)

    def create_widgets(self):

        top_main = self.get_ctrl_by_index(strip_org(self.mouth_bones['top'][0]), 0)
        corner_1 = self.get_ctrl_by_index(strip_org(self.mouth_bones['top'][0]), -1)
        corner_2 = self.get_ctrl_by_index(strip_org(self.mouth_bones['top'][1]), -1)
        bottom_main = self.get_ctrl_by_index(strip_org(self.mouth_bones['bottom'][0]), 0)

        create_cube_widget(self.obj, top_main)
        create_cube_widget(self.obj, corner_1)
        create_cube_widget(self.obj, corner_2)
        create_cube_widget(self.obj, bottom_main)

        jaw_ctrl = self.bones['jaw_ctrl']['jaw']
        create_jaw_widget(self.obj, jaw_ctrl)

        super().create_widgets()

    def generate(self):
        return super().generate()


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('mouth')
    bone.head[:] = 0.0000, -0.0700, 0.0962
    bone.tail[:] = 0.0000, -0.0295, 0.0962
    bone.roll = 0.0000
    bone.use_connect = False
    bones['mouth'] = bone.name
    bone = arm.edit_bones.new('lip.T.L')
    bone.head[:] = 0.0000, -0.1022, 0.0563
    bone.tail[:] = 0.0131, -0.0986, 0.0567
    bone.roll = 0.0000
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['mouth']]
    bones['lip.T.L'] = bone.name
    bone = arm.edit_bones.new('lip.B.L')
    bone.head[:] = 0.0000, -0.0993, 0.0455
    bone.tail[:] = 0.0124, -0.0938, 0.0488
    bone.roll = -0.0789
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['mouth']]
    bones['lip.B.L'] = bone.name
    bone = arm.edit_bones.new('lip.T.R')
    bone.head[:] = -0.0000, -0.1022, 0.0563
    bone.tail[:] = -0.0131, -0.0986, 0.0567
    bone.roll = -0.0000
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['mouth']]
    bones['lip.T.R'] = bone.name
    bone = arm.edit_bones.new('lip.B.R')
    bone.head[:] = -0.0000, -0.0993, 0.0455
    bone.tail[:] = -0.0124, -0.0938, 0.0488
    bone.roll = 0.0789
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['mouth']]
    bones['lip.B.R'] = bone.name
    bone = arm.edit_bones.new('mouth.001')
    bone.head[:] = 0.0000, -0.0295, 0.0962
    bone.tail[:] = 0.0000, -0.0923, 0.0044
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['mouth']]
    bones['mouth.001'] = bone.name
    bone = arm.edit_bones.new('lip.T.L.001')
    bone.head[:] = 0.0131, -0.0986, 0.0567
    bone.tail[:] = 0.0236, -0.0877, 0.0519
    bone.roll = 0.0236
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lip.T.L']]
    bones['lip.T.L.001'] = bone.name
    bone = arm.edit_bones.new('lip.B.L.001')
    bone.head[:] = 0.0124, -0.0938, 0.0488
    bone.tail[:] = 0.0236, -0.0877, 0.0519
    bone.roll = 0.0731
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lip.B.L']]
    bones['lip.B.L.001'] = bone.name
    bone = arm.edit_bones.new('lip.T.R.001')
    bone.head[:] = -0.0131, -0.0986, 0.0567
    bone.tail[:] = -0.0236, -0.0877, 0.0519
    bone.roll = -0.0236
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lip.T.R']]
    bones['lip.T.R.001'] = bone.name
    bone = arm.edit_bones.new('lip.B.R.001')
    bone.head[:] = -0.0124, -0.0938, 0.0488
    bone.tail[:] = -0.0236, -0.0877, 0.0519
    bone.roll = -0.0731
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lip.B.R']]
    bones['lip.B.R.001'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['mouth']]
    pbone.rigify_type = 'experimental.bendy_jaw'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.T.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.B.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.T.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.B.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['mouth.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.T.L.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.B.L.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.T.R.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lip.B.R.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
    for b in bones:
        bone = arm.edit_bones[bones[b]]
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        arm.edit_bones.active = bone


def add_parameters(params):
    """ Add the parameters of this rig type to the
        RigifyParameters PropertyGroup
    """
    items = [
        ('manual', 'Manual', ''),
        ('automatic', 'Automatic', '')
    ]

    params.rotation_mode = bpy.props.EnumProperty(
        items=items,
        name="Rotation Mode",
        description="Auto will align z-axis of jaw ctrl along the plane defined by the main and jaw bones",
        default='automatic'
    )

    ControlLayersGenerator.add_layer_parameters(params)


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters."""

    r = layout.row()
    r.prop(params, "rotation_mode")

    ControlLayersGenerator.add_layers_ui(layout, params)
