import bpy
from .utils import MetarigError, make_constraints_from_string


class GlueBucket:

    """
    Object used for glueing with glue bones
    """

    POSITION_RELATIVE_ERROR = 1e-3  # error below which two positions are considered equal (relative to bone len)

    def __init__(self, obj):

        self.obj = obj

        self.base_bone = 'root'
        self.bones = dict()
        self.bones['ctrl'] = dict()
        self.bones['ctrl']['all_ctrls'] = self.get_all_armature_ctrls()

        self.bones['glue'] = self.get_glue_bones()

    def get_glue_bones(self):
        """
        Get names of metarig pose bones with glue prop
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        glue_bones = []

        for pose_bone in pose_bones:
            if pose_bone.rigify_glue != "":
                if pose_bone.bone.children or pose_bone.bone.parent.name != self.base_bone:
                    raise MetarigError("ERROR on %s: Glue bones must have no parent or children!" % pose_bone.name)
                else:
                    glue_bones.append(pose_bone.name)

        return glue_bones

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

    def make_glue_constraints(self):

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        # Glue bones Constraints
        for glue_bone in self.bones['glue']:
            head_ctrls = self.get_ctrls_by_position(pose_bones[glue_bone].head)
            if not head_ctrls:
                continue
            tail_ctrls = self.get_ctrls_by_position(pose_bones[glue_bone].tail)
            if not tail_ctrls:
                continue

            # todo solve for tail_ctrls and head_ctrl len > 1
            owner_pb = pose_bones[tail_ctrls[0]]
            make_constraints_from_string(owner_pb, target=self.obj, subtarget=head_ctrls[0],
                                         fstring=pose_bones[glue_bone].rigify_glue)
