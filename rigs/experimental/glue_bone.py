import bpy

from ...utils import make_constraints_from_string, make_deformer_name, make_mechanism_name
from ...utils import strip_org, copy_bone, put_bone

from .base_rig import BaseRig


class Rig(BaseRig):

    POSITION_RELATIVE_ERROR = 1e-3  # position relative error (relative to bone length)

    def __init__(self, obj, bone_name, params):
        super().__init__(obj, bone_name, params)

        self.glue_mode = params.glue_mode
        self.bones['ctrl']['all_ctrls'] = self.get_all_armature_ctrls()

        self.bbones = params.bbones

    def get_all_armature_ctrls(self):
        """
        Get all the ctrl bones in self.obj armature
        :return:
        """
        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones
        all_ctrls = []

        for pb in pose_bones:
            forbidden_layers = pb.bone.layers[-4:]
            if not (True in forbidden_layers):
                all_ctrls.append(pb.name)

        return all_ctrls

    def get_ctrls_by_position(self, position, groups=None, relative_error=0):
        """
        Returns the controls closest to position in given relative_error range and subchain
        checking subchain first and then aggregates
        :param groups:
        :type groups: list(str)
        :param position:
        :type position: Vector
        :param relative_error: position error relative to bone length
        :return:
        :rtype: list(str)
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        bones_in_range = []

        if groups:
            keys = groups
        else:
            keys = self.bones['ctrl'].keys()

        if not relative_error:
            relative_error = self.POSITION_RELATIVE_ERROR

        for k in keys:
            for name in self.bones['ctrl'][k]:
                error = edit_bones[name].length * relative_error
                if (edit_bones[name].head - position).magnitude <= error:
                    bones_in_range.append(name)

        return bones_in_range

    def get_def_by_org(self, org_name):
        base_name = strip_org(org_name)
        return make_deformer_name(base_name)

    def create_def(self):
        """
        If add_glue_def is True adds a DEF
        :return:
        """

        if not self.params.add_glue_def:
            return

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        def_bone = make_deformer_name(strip_org(self.base_bone))
        def_bone = copy_bone(self.obj, self.base_bone, def_bone)
        self.bones['glue_def'] = def_bone

        DEF_LAYER = [n == 29 for n in range(0, 32)]
        edit_bones[def_bone].layers = DEF_LAYER
        edit_bones[def_bone].use_deform = True

    def create_mch(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        mch_bone = make_mechanism_name(strip_org(self.base_bone))
        mch_bone = copy_bone(self.obj, self.base_bone, mch_bone)
        self.bones['glue_mch'] = mch_bone

        MCH_LAYER = [n == 30 for n in range(0, 32)]
        edit_bones[mch_bone].layers = MCH_LAYER

        if self.glue_mode == 'bridge':
            self.bones['glue_mch'] = [mch_bone]
            b = self.base_bone
            put_bone(self.obj, mch_bone, edit_bones[b].head - (edit_bones[mch_bone].tail - edit_bones[mch_bone].head))

            mch_bone = make_mechanism_name(strip_org(self.base_bone))
            mch_bone = copy_bone(self.obj, self.base_bone, mch_bone)
            self.bones['glue_mch'].append(mch_bone)
            put_bone(self.obj, mch_bone, edit_bones[b].tail)
            edit_bones[mch_bone].layers = MCH_LAYER

    def make_glue_constraints(self):
        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        # Glue bones Constraints
        glue_bone = self.base_bone
        head_ctrls = self.get_ctrls_by_position(pose_bones[glue_bone].head)
        if not head_ctrls:
            return
        tail_ctrls = self.get_ctrls_by_position(pose_bones[glue_bone].tail)
        if not tail_ctrls:
            return

        # todo solve for tail_ctrls and head_ctrl len > 1
        owner_pb = pose_bones[tail_ctrls[0]]
        make_constraints_from_string(owner_pb, target=self.obj, subtarget=head_ctrls[0],
                                     fstring=self.params.glue_string)

        if 'glue_def' in self.bones:
            owner_pb = pose_bones[self.bones['glue_def']]
            make_constraints_from_string(owner_pb, target=self.obj, subtarget=head_ctrls[0],
                                         fstring="CL1.0WW0.0")
            make_constraints_from_string(owner_pb, target=self.obj, subtarget=tail_ctrls[0],
                                         fstring="DT1.0#ST1.0")

    def make_def_mediation(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        def_parent = self.get_def_by_org(edit_bones[self.base_bone].parent.name)
        def_child = ""
        for bone in edit_bones[def_parent].children:
            if bone.use_connect:
                def_child = self.get_def_by_org(bone.name)

        if def_child == "":
            return

        edit_bones[self.bones['glue_mch']].parent = edit_bones[def_parent]

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        owner_pb = pose_bones[self.bones['glue_mch']]
        subtarget = def_child
        make_constraints_from_string(owner_pb, target=self.obj, subtarget=subtarget,
                                     fstring="CR0.5LLO")

        owner_pb = pose_bones[self.base_bone]
        subtarget = self.bones['glue_mch']
        make_constraints_from_string(owner_pb, target=self.obj, subtarget=subtarget,
                                     fstring="CT1.0WW")

    def make_bridge(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        glue_bone = self.base_bone
        head_ctrls = self.get_ctrls_by_position(edit_bones[glue_bone].head)
        if not head_ctrls:
            return
        tail_ctrls = self.get_ctrls_by_position(edit_bones[glue_bone].tail)
        if not tail_ctrls:
            return

        head = head_ctrls[0]
        tail = tail_ctrls[0]

        # Parenting
        edit_bones[self.bones['glue_mch'][0]].parent = edit_bones[head]
        edit_bones[self.bones['glue_mch'][1]].parent = edit_bones[tail]
        edit_bones[self.bones['glue_def']].parent = edit_bones[self.bones['glue_mch'][0]]

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        self.obj.data.bones[self.bones['glue_def']].bbone_segments = self.bbones

        # CNS
        def_pb = pose_bones[self.bones['glue_def']]
        make_constraints_from_string(def_pb, target=self.obj, subtarget=tail, fstring="ST1.0")

        owner_pb = pose_bones[glue_bone]
        make_constraints_from_string(owner_pb, target=self.obj, subtarget=head, fstring="CT1.0WW")

        if 'bbone_custom_handle_start' in dir(def_pb) and 'bbone_custom_handle_end' in dir(def_pb):
            def_pb.bbone_custom_handle_start = pose_bones[self.bones['glue_mch'][0]]
            def_pb.bbone_custom_handle_end = pose_bones[self.bones['glue_mch'][1]]
            def_pb.use_bbone_custom_handles = True

    def glue(self):
        """
        Glue pass
        :return:
        """

        if self.glue_mode == "glue":
            self.create_def()
            self.make_glue_constraints()
        elif self.glue_mode == "def_mediator":
            self.create_mch()
            self.make_def_mediation()
        elif self.glue_mode == "bridge":
            self.create_def()
            self.create_mch()
            self.make_bridge()


    def generate(self):
        """
        Glue bones generate must do nothing. Glue bones pass is meant to happen after all other rigs are generated
        :return:
        """
        return [""]


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Bone')
    bone.head[:] = 0.0000, 0.0000, 0.0000
    bone.tail[:] = 0.0000, 0.0000, 1.0000
    bone.roll = 0.0000
    bone.use_connect = False
    bones['Bone'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Bone']]
    pbone.rigify_type = 'experimental.glue_bone'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    try:
        pbone.rigify_parameters.add_glue_def = False
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.glue_string = ""
    except AttributeError:
        pass

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
        ('def_mediator', 'DEF-mediator', ''),
        ('bridge', 'Bridge', ''),
        ('glue', 'Glue', '')
    ]

    params.bbones = bpy.props.IntProperty(
        name='bbone segments',
        default=10,
        min=1,
        description='Number of segments'
    )

    params.glue_mode = bpy.props.EnumProperty(
        items=items,
        name="Glue Mode",
        description="Glue adds constraints on generated ctrls DEF mediator is a DEF helper",
        default='glue'
    )

    params.glue_string = bpy.props.StringProperty(name="Rigify Glue String",
                                                  description="Defines a set of cns between controls")

    # Add DEF on glue
    params.add_glue_def = bpy.props.BoolProperty(name="Add DEF on glue bone",
                                                 default=True, description="Add an eye-follow driver to this eye(s)")


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters."""
    row = layout.row()
    row.prop(params, "glue_mode")

    if params.glue_mode == 'bridge':
        r = layout.row()
        r.prop(params, "bbones")

    if params.glue_mode == 'glue':
        row = layout.row()
        row.prop(params, "glue_string", text="Glue string")

        row = layout.row()
        row.prop(params, "add_glue_def", text="Add DEF bone")
