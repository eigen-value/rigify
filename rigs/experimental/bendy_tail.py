import bpy

from .chainy_rig import ChainyRig
from .control_layers_generator import ControlLayersGenerator
from ...utils import make_mechanism_name, make_constraints_from_string
from ...utils import flip_bone, org, strip_org, copy_bone, put_bone, align_bone_y_axis
from ...utils import create_sphere_widget, create_circle_widget
from ..widgets import create_ballsocket_widget


class Rig(ChainyRig):

    TWEAK_SCALE = 0.5       # tweak size relative to orientation bone

    def __init__(self, obj, bone_name, params):
        super().__init__(obj, bone_name, params, single=True)

        self.layer_generator = ControlLayersGenerator(self)

    def create_mch(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        super().create_mch()

        self.bones['tail_mch'] = {}

        org_chain = self.get_chain_bones(self.base_bone)

        if edit_bones[org_chain[0]].parent:
            bone_to_copy = edit_bones[org_chain[0]].parent.name
        else:
            bone_to_copy = self.orientation_bone

        mch_rot_tail = make_mechanism_name('ROT-' + strip_org(self.base_bone))
        mch_rot_tail = copy_bone(self.obj, bone_to_copy, assign_name=mch_rot_tail)
        self.bones['tail_mch']['rot_tail_mch'] = mch_rot_tail
        main_chain = self.get_chain_bones(self.base_bone)
        flip_bone(self.obj, mch_rot_tail)
        edit_bones[mch_rot_tail].parent = None
        put_bone(self.obj, mch_rot_tail, edit_bones[main_chain[0]].head)

    def create_def(self):
        super().create_def()

        chain = strip_org(self.base_bone)

        for def_bone in self.bones['def'][chain]:
            flip_bone(self.obj, def_bone)

        self.bones['def'][chain].reverse()

    def create_controls(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        super().create_controls()

        self.bones['tweaks'] = {}
        self.bones['tail_ctrl'] = {}

        chain = strip_org(self.base_bone)
        ctrl_chain = self.bones['ctrl'][chain]
        self.bones['tweaks'][chain] = []
        orgs = self.get_chain_bones(org(chain))

        for org_bone, ctrl in zip(orgs, ctrl_chain):
            edit_bones[ctrl].length = edit_bones[org_bone].length
            align_bone_y_axis(self.obj, ctrl, edit_bones[org_bone].y_axis)
            tweak_name = 'tweak_' + ctrl
            tweak_name = copy_bone(self.obj, org_bone, assign_name=tweak_name)
            edit_bones[tweak_name].length = edit_bones[self.orientation_bone].length * self.TWEAK_SCALE
            self.bones['tweaks'][chain].append(tweak_name)

        tweak_name = 'tweak_' + ctrl_chain[-1]
        tweak_name = copy_bone(self.obj, orgs[-1], assign_name=tweak_name)
        edit_bones[tweak_name].parent = None
        put_bone(self.obj, tweak_name, edit_bones[orgs[-1]].tail)
        edit_bones[tweak_name].length = edit_bones[self.orientation_bone].length * self.TWEAK_SCALE
        self.bones['tweaks'][chain].append(tweak_name)

        edit_bones[ctrl_chain[-1]].head = edit_bones[orgs[0]].head
        edit_bones[ctrl_chain[-1]].tail = edit_bones[orgs[0]].tail
        tail_master = strip_org(self.base_bone) + '_master'
        edit_bones[ctrl_chain[-1]].name = tail_master
        self.bones['tail_ctrl']['tail_master'] = tail_master
        ctrl_chain[-1] = tail_master

    def parent_bones(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        super().parent_bones()

        ctrl_chain = self.bones['ctrl'][strip_org(self.base_bone)]
        tweak_chain = self.bones['tweaks'][strip_org(self.base_bone)]
        def_chain = self.bones['def'][strip_org(self.base_bone)]

        edit_bones[tweak_chain[0]].parent = None

        for ctrl, tweak in zip(ctrl_chain[1:-1], tweak_chain[1:-1]):
            edit_bones[tweak].use_connect = False
            edit_bones[tweak].parent = edit_bones[ctrl]

        edit_bones[tweak_chain[-1]].use_connect = False
        edit_bones[tweak_chain[-1]].parent = edit_bones[ctrl_chain[-2]]

        for i, def_bone in enumerate(def_chain[1:]):
            edit_bones[def_bone].use_connect = True
            edit_bones[def_bone].parent = edit_bones[def_chain[i]]

        for i, ctrl in enumerate(ctrl_chain[1:-1]):
            edit_bones[ctrl].parent = edit_bones[ctrl_chain[i]]

        edit_bones[ctrl_chain[0]].parent = edit_bones[self.bones['tail_mch']['rot_tail_mch']]

        edit_bones[self.bones['tail_mch']['rot_tail_mch']].parent = edit_bones[tweak_chain[0]]

    def assign_layers(self):

        primary_ctrls = []
        primary_ctrls.append(self.bones['tail_ctrl']['tail_master'])

        all_ctrls = self.get_all_ctrls()
        self.layer_generator.assign_layer(primary_ctrls, all_ctrls)

        tweaks = self.flatten(self.bones['tweaks'])
        self.layer_generator.assign_tweak_layers(tweaks)

    def make_constraints(self):

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        super().make_constraints()

        def_chain = self.bones['def'][strip_org(self.base_bone)]
        tweak_chain = self.bones['tweaks'][strip_org(self.base_bone)]
        ctrl_chain = self.bones['ctrl'][strip_org(self.base_bone)]

        for i, def_bone in enumerate(def_chain):
            pose_bones[def_bone].constraints[0].subtarget = tweak_chain[-i-1]
            pose_bones[def_bone].constraints[1].subtarget = tweak_chain[-i-2]
            pose_bones[def_bone].constraints[2].subtarget = tweak_chain[-i-2]

        for i, ctrl in enumerate(ctrl_chain):
            if ctrl != ctrl_chain[-1]:
                owner = pose_bones[ctrl]
                if i == 0:
                    subtarget = ctrl_chain[-1]
                else:
                    subtarget = ctrl_chain[i-1]
                make_constraints_from_string(owner, self.obj, subtarget, "CR1.0LLO")
                owner.constraints[-1].use_y = False

        first_org = self.get_chain_bones(self.base_bone)[0]
        if pose_bones[first_org].parent:
            owner = pose_bones[self.bones['tail_mch']['rot_tail_mch']]
            subtarget = pose_bones[first_org].parent.name
            make_constraints_from_string(owner, self.obj, subtarget, "CR1.0WW")

    def create_widgets(self):

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        ctrl_chain = self.bones['ctrl'][strip_org(self.base_bone)]
        for i, bone in enumerate(ctrl_chain):
            if i != len(ctrl_chain) - 1:
                create_circle_widget(self.obj, bone, radius=0.5, head_tail=0.75, with_line=False)
            else:
                create_ballsocket_widget(self.obj, bone, size=0.7)

        for bone in self.bones['tweaks'][strip_org(self.base_bone)]:
            create_sphere_widget(self.obj, bone)

        pose_bones[ctrl_chain[-1]].custom_shape_transform = \
            pose_bones[self.bones['tweaks'][strip_org(self.base_bone)][-1]]

        super().create_widgets()

    def cleanup(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for mch in self.bones['mch'][strip_org(self.base_bone)]:
            edit_bones.remove(edit_bones[mch])

    def generate(self):
        return super().generate()


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('spine')
    bone.head[:] = 0.0000, 1.1044, 0.7633
    bone.tail[:] = 0.0000, 0.9624, 0.7412
    bone.roll = 0.0000
    bone.use_connect = False
    bones['spine'] = bone.name
    bone = arm.edit_bones.new('spine.001')
    bone.head[:] = 0.0000, 0.9624, 0.7412
    bone.tail[:] = 0.0000, 0.7755, 0.7418
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine']]
    bones['spine.001'] = bone.name
    bone = arm.edit_bones.new('spine.002')
    bone.head[:] = 0.0000, 0.7755, 0.7418
    bone.tail[:] = 0.0000, 0.5547, 0.7568
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.001']]
    bones['spine.002'] = bone.name
    bone = arm.edit_bones.new('spine.003')
    bone.head[:] = 0.0000, 0.5547, 0.7568
    bone.tail[:] = 0.0000, 0.4418, 0.7954
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.002']]
    bones['spine.003'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['spine']]
    pbone.rigify_type = 'experimental.bendy_tail'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    try:
        pbone.rigify_parameters.tweak_layers = [False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.use_tail = True
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.tail_pos = 4
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.pivot_pos = 8
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.neck_pos = 10
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.copy_rotation_axes = [True, False, True]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['spine.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    try:
        pbone.rigify_parameters.tweak_extra_layers = False
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.tweak_layers = [False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['spine.003']]
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

    ControlLayersGenerator.add_layer_parameters(params)
    ControlLayersGenerator.add_tweak_layer_parameters(params)


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters."""

    ControlLayersGenerator.add_layers_ui(layout, params)
    ControlLayersGenerator.add_tweak_layers_ui(layout, params)
