#######################################################################################################################
# Bendy eye contruction rules:
#
#######################################################################################################################

import bpy
from mathutils import Vector
from rna_prop_ui import rna_idprop_ui_prop_get
from ...utils import copy_bone, put_bone
from ...utils import org, strip_org, make_deformer_name, make_mechanism_name
from ...utils import create_circle_widget, create_cube_widget
from ...utils import MetarigError
from ...utils import make_constraints_from_string, align_bone_y_axis, align_bone_z_axis
from ..widgets import create_eye_widget, create_eyes_widget, create_widget_from_cluster, create_gear_widget
from .meshy_rig import MeshyRig
from .control_snapper import ControlSnapper
from .control_layers_generator import ControlLayersGenerator

script = """
all_controls   = [%s]
eyes_ctrl_name = '%s'

if is_selected(all_controls):
    layout.prop(pose_bones[eyes_ctrl_name], '["%s"]', slider=True)
"""


class Rig(MeshyRig):

    def __init__(self, obj, bone_name, params):

        super().__init__(obj, bone_name, params)
        self.control_snapper = ControlSnapper(self.obj, self.bones)

        self.lid_len = None
        self.lid_bones = self.get_eyelids()

        self.paired_eye = self.get_paired_eye()
        self.needs_driver = self.get_driver_condition()
        self.add_eyefollow = params.add_eyefollow

        self.layer_generator = ControlLayersGenerator(self)

    def get_eyelids(self):
        """
        Returns the main bones of the lids chain
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        lid_bones = []
        for child in edit_bones[self.bones['org'][0]].children:
            if not child.use_connect:
                lid_bones.append(child.name)

        # Rule check
        if len(lid_bones) != 2:
            raise MetarigError("Exactly 2 disconnected chains (lids) must be parented to main bone")

        eyelids_bones_dict = {'top': [], 'bottom': []}
        self.lid_len = len(self.get_chain_bones(lid_bones[0]))

        # Check both have same length
        for lid in lid_bones:
            if len(self.get_chain_bones(lid)) != self.lid_len:
                raise MetarigError("All lid chains must be the same length")

        if edit_bones[lid_bones[0]].tail.z < edit_bones[lid_bones[1]].tail.z:
            eyelids_bones_dict['top'].append(lid_bones[1])
            eyelids_bones_dict['bottom'].append(lid_bones[0])
        else:
            eyelids_bones_dict['top'].append(lid_bones[0])
            eyelids_bones_dict['bottom'].append(lid_bones[1])

        if not (len(eyelids_bones_dict['top']) == len(eyelids_bones_dict['bottom']) == 1):
            raise MetarigError("Badly drawn eyelids on %s" % self.bones['org'][0])

        return eyelids_bones_dict

    def get_paired_eye(self):
        """
        A paired eye must follow the name rule: <bone_name>.<suffix>.<extra> where suffix = L or R and
        the other elements must be the same
        :return:
        """

        if not self.params.paired_eye:
            return ''

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        paired_eye = org(self.params.paired_eye)

        if pose_bones[paired_eye].rigify_parameters.paired_eye == strip_org(self.base_bone):
            return paired_eye

        return ''

    def get_common_name(self):
        """
        Returns an aggregate name for an eyes pair
        :return:
        :rtype: str
        """

        cluster = []

        if self.is_clustered():
            cluster = self.get_cluster_names()
        else:
            base = strip_org(self.base_bone)
            pair = strip_org(self.paired_eye)
            cluster = [base, pair]

        return self.control_snapper.get_aggregate_name(cluster)

    def get_paired_eye_ctrls_name(self):
        """
        utility function for pairing with another eye. Gives all the expected ctrl names
        :return: list of ctrl names
        :rtype: list
        """

        if not self.paired_eye:
            return []

        base_name = strip_org(self.paired_eye)

        target = base_name
        master = 'master_' + base_name

        return [target, master]

    def get_driver_condition(self):
        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        has_parent = bool(pose_bones[self.base_bone].parent)

        is_clustered = self.is_clustered()

        paired_follows = False
        has_paired = bool(self.paired_eye)
        if has_paired:
            paired_follows = pose_bones[self.paired_eye].rigify_parameters.add_eyefollow

        condition = (not has_paired or paired_follows or is_clustered) and has_parent and self.params.add_eyefollow

        return condition

    def is_clustered(self):
        """
        True if is a clustered eye
        :return:
        :rtype: bool
        """

        return self.obj.pose.bones[self.base_bone].rigify_parameters.clustered_eye

    def get_cluster_names(self, all_ctrls=False):
        """
        Names of bones in the cluster
        :return:
        :rtype: list(str)
        """

        names = []
        pose_bones = self.obj.pose.bones

        for pb in pose_bones:
            if pb.rigify_type == 'experimental.bendy_eye' and pb.rigify_parameters.clustered_eye\
                    and pb.parent == pose_bones[self.base_bone].parent:
                base_name = strip_org(pb.name)
                names.append(base_name)
                if all_ctrls:
                    names.append('master_' + base_name)

        return names

    def get_cluster_positions(self):
        positions = []

        pose_bones = self.obj.pose.bones

        for pb in pose_bones:
            if pb.rigify_type == 'experimental.bendy_eye' and pb.rigify_parameters.clustered_eye \
                    and pb.parent == pose_bones[self.base_bone].parent:
                positions.append(pb.head)

        return positions

    def get_cluster_data(self):
        """
        Returns the center position and common direction of an eye-cluster
        :return: [position, direction]
        :rtype: list(Vector)
        """

        edit_bones = self.obj.data.edit_bones

        positions = []
        sum_position = Vector((0, 0, 0))

        y_direction = None
        z_direction = Vector((0, 0, 0))

        for name in self.get_cluster_names():
            did_generate_ctrl = strip_org(name) in edit_bones
            if not did_generate_ctrl:
                # this is not the last eye in the cluster, delay
                return [None, None, None]
            else:
                positions.append(edit_bones[strip_org(name)].head)
                sum_position += edit_bones[strip_org(name)].head
                y_direction = edit_bones[strip_org(name)].y_axis
                z_direction += edit_bones[strip_org(name)].z_axis

        if positions and y_direction and z_direction:
            position = sum_position / len(positions)
            z_direction = z_direction / len(positions)
        else:
            return [None, None, None]

        return [position, y_direction, z_direction]

    def create_mch(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        self.bones['eye_mch'] = dict()
        self.bones['eye_mch']['eyelid_top'] = []
        self.bones['eye_mch']['eyelid_bottom'] = []
        self.bones['eye_mch']['eye_master'] = ''
        self.bones['eye_mch']['eye_master_tip'] = ''

        main_bone_name = strip_org(self.bones['org'][0])
        eye_mch_name = make_mechanism_name(main_bone_name)
        eye_mch_name = copy_bone(self.obj, self.bones['org'][0], eye_mch_name)
        self.bones['eye_mch']['eye_master'] = eye_mch_name

        eye_tip_mch_name = copy_bone(self.obj, self.orientation_bone, eye_mch_name)
        self.bones['eye_mch']['eye_master_tip'] = eye_tip_mch_name
        put_bone(self.obj, eye_tip_mch_name, edit_bones[eye_mch_name].tail)
        if self.orientation_bone == self.base_bone:
            align_bone_y_axis(self.obj, eye_tip_mch_name, Vector((0, 0, 1)))
        edit_bones[eye_tip_mch_name].length = 0.25 * edit_bones[eye_mch_name].length

        # top lid
        top_lid_chain = self.get_chain_bones(self.lid_bones['top'][0])
        for l_b in top_lid_chain:
            lid_m_name = copy_bone(self.obj, self.bones['org'][0], eye_mch_name)
            edit_bones[lid_m_name].tail = edit_bones[l_b].tail
            self.bones['eye_mch']['eyelid_top'].append(lid_m_name)

        # bottom lid
        bottom_lid_chain = self.get_chain_bones(self.lid_bones['bottom'][0])
        for l_b in bottom_lid_chain:
            lid_m_name = copy_bone(self.obj, self.bones['org'][0], eye_mch_name)
            edit_bones[lid_m_name].tail = edit_bones[l_b].tail
            self.bones['eye_mch']['eyelid_bottom'].append(lid_m_name)

        # create mch for eye_follow driver
        if self.needs_driver:
            if self.paired_eye or self.is_clustered():
                eye_follow_mch = self.get_common_name()
            else:
                eye_follow_mch = strip_org(self.base_bone)
            eye_follow_mch = make_mechanism_name(eye_follow_mch)
            eye_follow_mch += "_parent"

            if eye_follow_mch not in edit_bones:
                parent = edit_bones[self.base_bone].parent.name
                eye_follow_mch = copy_bone(self.obj, parent, eye_follow_mch)
                edit_bones[eye_follow_mch].length = 0.25 * edit_bones[parent].length
            self.bones['eye_mch']['eyefollow'] = eye_follow_mch

        super().create_mch()

    def create_def(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        self.bones['eye_def'] = dict()

        if self.params.make_deform:
            main_eye_def = make_deformer_name(strip_org(self.bones['org'][0]))
            main_eye_def = copy_bone(self.obj, self.bones['org'][0], main_eye_def)
            self.bones['eye_def']['eyeball_def'] = main_eye_def

        super().create_def()

    def create_controls(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        self.bones['eye_ctrl'] = dict()

        if self.orientation_bone == self.base_bone:
            axis = Vector((0, 0, 1))
        else:
            axis = edit_bones[self.orientation_bone].y_axis

        eye_ctrl_name = "master_" + strip_org(self.bones['org'][0])
        eye_ctrl = copy_bone(self.obj, self.bones['org'][0], eye_ctrl_name)
        self.bones['eye_ctrl']['master_eye'] = eye_ctrl

        if self.params.make_control:
            eye_hook_name = strip_org(self.bones['org'][0]) + "_hook"
            eye_hook = copy_bone(self.obj, self.bones['org'][0], eye_hook_name)
            self.bones['eye_ctrl']['eye_hook'] = eye_hook

        eye_target_name = strip_org(self.bones['org'][0])
        eye_target = copy_bone(self.obj, self.orientation_bone, eye_target_name)
        self.bones['eye_ctrl']['eye_target'] = eye_target
        position = edit_bones[eye_ctrl].tail + 5 * edit_bones[eye_ctrl].length * edit_bones[eye_ctrl].y_axis
        put_bone(self.obj, eye_target, position)
        edit_bones[eye_target].length = 0.5 * edit_bones[self.base_bone].length
        align_bone_y_axis(self.obj, eye_target, Vector((0, 0, 1)))
        align_bone_z_axis(self.obj, eye_target, edit_bones[self.base_bone].y_axis)

        # make standard controls
        super().create_controls()

        # add extra lid ctrls
        top_chain = strip_org(self.lid_bones['top'][0])
        bottom_chain = strip_org(self.lid_bones['bottom'][0])

        if self.lid_len % 2 != 0:
            mid_index = int((self.lid_len + 1)/2)

            top_lid_master = copy_bone(self.obj, self.bones['ctrl'][top_chain][0])
            # edit_bones[top_lid_master].length *= 1.5
            self.bones['eye_ctrl']['top_lid_master'] = top_lid_master
            mid_bone_1 = edit_bones[self.bones['ctrl'][top_chain][mid_index - 1]]
            mid_bone_2 = edit_bones[self.bones['ctrl'][top_chain][mid_index]]
            put_bone(self.obj, top_lid_master, (mid_bone_1.head + mid_bone_2.head)/2)
            align_bone_y_axis(self.obj, top_lid_master, axis)

            bottom_lid_master = copy_bone(self.obj, self.bones['ctrl'][bottom_chain][0])
            # edit_bones[bottom_lid_master].length *= 1.5
            self.bones['eye_ctrl']['bottom_lid_master'] = bottom_lid_master
            mid_bone_1 = edit_bones[self.bones['ctrl'][bottom_chain][mid_index - 1]]
            mid_bone_2 = edit_bones[self.bones['ctrl'][bottom_chain][mid_index]]
            put_bone(self.obj, bottom_lid_master, (mid_bone_1.head + mid_bone_2.head)/2)
            align_bone_y_axis(self.obj, bottom_lid_master, axis)

        else:
            mid_index = int((self.lid_len) / 2)
            top_lid_master = self.bones['ctrl'][top_chain][mid_index]
            bottom_lid_master = self.bones['ctrl'][bottom_chain][mid_index]
            # edit_bones[top_lid_master].length *= 1.5
            # edit_bones[bottom_lid_master].length *= 1.5
            self.bones['eye_ctrl']['top_lid_master'] = top_lid_master
            self.bones['eye_ctrl']['bottom_lid_master'] = bottom_lid_master

        # create eyes master if eye has company
        create_common_ctrl = False
        if self.paired_eye and strip_org(self.paired_eye) in edit_bones:
            other_eye = strip_org(self.paired_eye)
            position = (edit_bones[eye_target].head + edit_bones[other_eye].head) / 2
            y_direction = edit_bones[eye_target].y_axis
            z_direction = edit_bones[eye_target].z_axis + edit_bones[other_eye].z_axis
            create_common_ctrl = True
        elif self.is_clustered():
            [position, y_direction, z_direction] = self.get_cluster_data()
            if position and y_direction:
                create_common_ctrl = True

        if create_common_ctrl:
            common_ctrl = self.get_common_name() + '_common'
            common_ctrl = copy_bone(self.obj, eye_target, common_ctrl)
            self.bones['eye_ctrl']['common'] = common_ctrl
            put_bone(self.obj, common_ctrl, position)
            align_bone_y_axis(self.obj, common_ctrl, y_direction)
            align_bone_z_axis(self.obj, common_ctrl, z_direction)

        for ctrl in self.bones['ctrl'][top_chain]:
            align_bone_y_axis(self.obj, ctrl, axis)

        for ctrl in self.bones['ctrl'][bottom_chain]:
            align_bone_y_axis(self.obj, ctrl, axis)

    def parent_bones(self):
        """
        Parent eye bones
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        master_ctrl = self.bones['eye_ctrl']['master_eye']

        eye_mchs = []
        eye_mchs.extend(self.bones['eye_mch']['eyelid_top'])
        eye_mchs.extend(self.bones['eye_mch']['eyelid_bottom'])
        eye_mchs.append(self.bones['eye_mch']['eye_master'])
        eye_mchs.append(self.bones['eye_mch']['eye_master_tip'])

        for mch in eye_mchs:
            edit_bones[mch].parent = edit_bones[master_ctrl]

        eye_ctrls = []
        for chain in self.bones['ctrl']:
            eye_ctrls.extend(self.bones['ctrl'][chain])

        for ctrl in eye_ctrls:
            edit_bones[ctrl].parent = edit_bones[master_ctrl]

        super().parent_bones()

        # adjust parenting
        top_lid_chain = strip_org(self.lid_bones['top'][0])

        for i, lid_def in enumerate(self.bones['def'][top_lid_chain]):
            if i == 0:
                edit_bones[lid_def].parent = edit_bones[self.bones['eye_mch']['eyelid_bottom'][-1]]
            else:
                edit_bones[lid_def].parent = edit_bones[self.bones['eye_mch']['eyelid_top'][i-1]]

        bottom_lid_chain = strip_org(self.lid_bones['bottom'][0])

        for i, lid_def in enumerate(self.bones['def'][bottom_lid_chain]):
            if i == 0:
                edit_bones[lid_def].parent = edit_bones[self.bones['eye_mch']['eyelid_top'][-1]]
            else:
                edit_bones[lid_def].parent = edit_bones[self.bones['eye_mch']['eyelid_bottom'][i-1]]

        if 'common' in self.bones['eye_ctrl']:
            common_ctrl = self.bones['eye_ctrl']['common']
            eye_target = self.bones['eye_ctrl']['eye_target']
            edit_bones[eye_target].parent = edit_bones[common_ctrl]
            if not self.is_clustered():
                other_eye = strip_org(self.paired_eye)
                edit_bones[other_eye].parent = edit_bones[common_ctrl]
            else:
                for name in self.get_cluster_names():
                    edit_bones[name].parent = edit_bones[common_ctrl]
            if 'eyefollow' in self.bones['eye_mch']:
                edit_bones[common_ctrl].parent = edit_bones[self.bones['eye_mch']['eyefollow']]
        elif 'eyefollow' in self.bones['eye_mch']:
            eye_target = self.bones['eye_ctrl']['eye_target']
            edit_bones[eye_target].parent = edit_bones[self.bones['eye_mch']['eyefollow']]
        if 'eyefollow' in self.bones['eye_mch']:
            edit_bones[self.bones['eye_mch']['eyefollow']].parent = None

        if 'eyeball_def' in self.bones['eye_def']:
            eye_hook = self.bones['eye_def']['eyeball_def']
            edit_bones[eye_hook].parent = edit_bones[self.bones['eye_mch']['eye_master']]

        if 'eye_hook' in self.bones['eye_ctrl']:
            eye_hook = self.bones['eye_ctrl']['eye_hook']
            edit_bones[eye_hook].parent = edit_bones[self.bones['eye_mch']['eye_master']]

    def aggregate_ctrls(self):
        self.control_snapper.aggregate_ctrls(same_parent=False)

    def assign_layers(self):

        primary_ctrls = []
        primary_ctrls.append(self.bones['eye_ctrl']['top_lid_master'])
        primary_ctrls.append(self.bones['eye_ctrl']['bottom_lid_master'])
        primary_ctrls.append(self.bones['eye_ctrl']['master_eye'])

        if 'eye_hook' in self.bones['eye_ctrl']:
            primary_ctrls.append(self.bones['eye_ctrl']['eye_hook'])

        primary_ctrls.append(self.bones['eye_ctrl']['eye_target'])

        if 'common' in self.bones['eye_ctrl']:
            primary_ctrls.append(self.bones['eye_ctrl']['common'])

        all_ctrls = self.get_all_ctrls()
        self.layer_generator.assign_layer(primary_ctrls, all_ctrls)

    def make_constraints(self):

        """
        Make constraints
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        tip = self.bones['eye_mch']['eye_master_tip']
        owner = pose_bones[tip]
        subtarget = self.bones['eye_mch']['eye_master']
        make_constraints_from_string(owner, self.obj, subtarget, 'CL1.0WW1.0')

        for i, e_m in enumerate(self.bones['eye_mch']['eyelid_top']):
            owner = pose_bones[e_m]
            subtarget = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i+1)
            make_constraints_from_string(owner, self.obj, subtarget, "DT1.0Y0.0")

        for i, e_m in enumerate(self.bones['eye_mch']['eyelid_bottom']):
            owner = pose_bones[e_m]
            subtarget = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i+1)
            make_constraints_from_string(owner, self.obj, subtarget, "DT1.0Y0.0")

        eye_mch_name = pose_bones[self.bones['eye_mch']['eye_master']]
        subtarget = self.bones['eye_ctrl']['eye_target']
        make_constraints_from_string(eye_mch_name, self.obj, subtarget, "DT1.0Y0.0")

        # eye_follow cns
        if 'eyefollow' in self.bones['eye_mch']:
            owner = pose_bones[self.bones['eye_mch']['eyefollow']]
            subtarget = pose_bones[self.base_bone].parent.name
            if not owner.constraints:   # this is important in paired eyes not to have repeated cns
                make_constraints_from_string(owner, self.obj, subtarget, "CT1.0WW0.0")

        if self.lid_len % 2 == 0:
            i = int(self.lid_len/2)
            central_ctrl_top = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i)
            owner = pose_bones[central_ctrl_top]
            subtarget = tip
            make_constraints_from_string(owner, self.obj, subtarget, "CL0.5LLO0.0")
            central_ctrl_bottom = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i)
            owner = pose_bones[central_ctrl_bottom]
            subtarget = tip
            make_constraints_from_string(owner, self.obj, subtarget, "CL0.5LLO0.0")
            influence = 0.6
            j = 1
            while True:
                if i + j == self.lid_len:
                    break

                ctrl_top_1 = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i+j)
                owner = pose_bones[ctrl_top_1]
                subtarget = central_ctrl_top
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)
                ctrl_top_2 = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i-j)
                owner = pose_bones[ctrl_top_2]
                subtarget = central_ctrl_top
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)

                ctrl_bottom_1 = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i+j)
                owner = pose_bones[ctrl_bottom_1]
                subtarget = central_ctrl_bottom
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)
                ctrl_bottom_2 = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i-j)
                owner = pose_bones[ctrl_bottom_2]
                subtarget = central_ctrl_bottom
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)

                influence -= 0.1
                j += 1

        else:

            top_lid_master = self.bones['eye_ctrl']['top_lid_master']
            owner = pose_bones[top_lid_master]
            subtarget = tip
            make_constraints_from_string(owner, self.obj, subtarget, "CL0.5LLO0.0")

            bottom_lid_master = self.bones['eye_ctrl']['bottom_lid_master']
            owner = pose_bones[bottom_lid_master]
            subtarget = tip
            make_constraints_from_string(owner, self.obj, subtarget, "CL0.5LLO0.0")

            influence = 0.6
            i = int((self.lid_len + 1)/2)
            j = 0

            while True:
                if i + j == self.lid_len:
                    break

                ctrl_top_1 = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i + j)
                owner = pose_bones[ctrl_top_1]
                subtarget = top_lid_master
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)
                ctrl_top_2 = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i - 1 - j)
                owner = pose_bones[ctrl_top_2]
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)

                ctrl_bottom_1 = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i + j)
                owner = pose_bones[ctrl_bottom_1]
                subtarget = bottom_lid_master
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)
                ctrl_bottom_2 = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i - 1 - j)
                owner = pose_bones[ctrl_bottom_2]
                make_constraints_from_string(owner, self.obj, subtarget, "CL%sLL0.0" % influence)

                influence -= 0.1
                j += 1

        if 'eyeball_def' in self.bones['eye_def']:
            owner = pose_bones[self.bones['eye_def']['eyeball_def']]
            target = self.obj
            subtarget = self.bones['eye_mch']['eye_master']
            make_constraints_from_string(owner, target, subtarget, "CT1.0")

        # make the standard chainy rig constraints
        super().make_constraints()

        # adjust constraints
        top_lid_chain = strip_org(self.lid_bones['top'][0])

        for i, lid_def in enumerate(self.bones['def'][top_lid_chain]):
            for cns in pose_bones[lid_def].constraints:
                if cns.type != "DAMPED_TRACK" and cns.type != "STRETCH_TO":
                    pose_bones[lid_def].constraints.remove(cns)
                else:
                    cns.subtarget = self.bones['eye_mch']['eyelid_top'][i]
                    cns.head_tail = 1.0

        bottom_lid_chain = strip_org(self.lid_bones['bottom'][0])

        for i, lid_def in enumerate(self.bones['def'][bottom_lid_chain]):
            for cns in pose_bones[lid_def].constraints:
                if cns.type != "DAMPED_TRACK" and cns.type != "STRETCH_TO":
                    pose_bones[lid_def].constraints.remove(cns)
                else:
                    cns.subtarget = self.bones['eye_mch']['eyelid_bottom'][i]
                    cns.head_tail = 1.0

    def make_drivers(self):
        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        eye_target = self.bones['eye_ctrl']['eye_target']

        if self.lid_len % 2 == 0:
            i = int(self.lid_len/2)
            central_ctrl_top = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i)
            central_ctrl_bottom = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i)
        else:
            central_ctrl_top = self.bones['eye_ctrl']['top_lid_master']
            central_ctrl_bottom = self.bones['eye_ctrl']['bottom_lid_master']

        prop_lid_follow_name = 'lid_follow'

        pose_bones[eye_target][prop_lid_follow_name] = 1.0

        prop = rna_idprop_ui_prop_get(pose_bones[eye_target], prop_lid_follow_name)
        prop["min"] = 0.0
        prop["max"] = 1.0
        prop["soft_min"] = 0.0
        prop["soft_max"] = 1.0
        prop["description"] = prop_lid_follow_name

        drv = pose_bones[central_ctrl_top].constraints[0].driver_add("influence").driver
        drv.type = 'SUM'

        var = drv.variables.new()
        var.name = prop_lid_follow_name
        var.type = "SINGLE_PROP"
        var.targets[0].id = self.obj
        var.targets[0].data_path = pose_bones[eye_target].path_from_id() + '[' + '"' + prop_lid_follow_name + '"' + ']'

        drv = pose_bones[central_ctrl_bottom].constraints[0].driver_add("influence").driver
        drv.type = 'SUM'

        var = drv.variables.new()
        var.name = prop_lid_follow_name
        var.type = "SINGLE_PROP"
        var.targets[0].id = self.obj
        var.targets[0].data_path = pose_bones[eye_target].path_from_id() + '[' + '"' + prop_lid_follow_name + '"' + ']'

        all_ctrls = []
        all_ctrls.append(self.bones['eye_ctrl']['eye_target'])
        all_ctrls.append(self.bones['eye_ctrl']['master_eye'])
        default_controls_string = ", ".join(["'" + x + "'" for x in all_ctrls])

        if not self.needs_driver:
            return [script % (default_controls_string, eye_target, prop_lid_follow_name)]

        # eyefollow driver
        if self.paired_eye or self.is_clustered():
            if 'common' in self.bones['eye_ctrl'] and 'eyefollow' in self.bones['eye_mch']:
                bone = self.bones['eye_ctrl']['common']
            else:
                return [script % (default_controls_string, eye_target, prop_lid_follow_name)]
        else:
            bone = self.bones['eye_ctrl']['eye_target']

        prop_name = self.get_common_name() + '_follow'

        pose_bones[bone][prop_name] = 1.0

        prop = rna_idprop_ui_prop_get(pose_bones[bone], prop_name)
        prop["min"] = 0.0
        prop["max"] = 1.0
        prop["soft_min"] = 0.0
        prop["soft_max"] = 1.0
        prop["description"] = prop_name

        # Eyes driver
        mch_eyes_parent = self.bones['eye_mch']['eyefollow']

        drv = pose_bones[mch_eyes_parent].constraints[0].driver_add("influence").driver
        drv.type = 'SUM'

        var = drv.variables.new()
        var.name = prop_name
        var.type = "SINGLE_PROP"
        var.targets[0].id = self.obj
        var.targets[0].data_path = pose_bones[bone].path_from_id() + '[' + '"' + prop_name + '"' + ']'

        # construct the script
        if prop_name:
            main_ctrl = ''
            all_ctrls = []
            all_ctrls.append(self.bones['eye_ctrl']['eye_target'])
            all_ctrls.append(self.bones['eye_ctrl']['master_eye'])
            if 'common' in self.bones['eye_ctrl']:
                all_ctrls.append(self.bones['eye_ctrl']['common'])
                if self.paired_eye:
                    all_ctrls.extend(self.get_paired_eye_ctrls_name())
                elif self.is_clustered():
                    all_ctrls.extend(self.get_cluster_names(all_ctrls=True))
                main_ctrl = self.bones['eye_ctrl']['common']
            elif not self.paired_eye:
                main_ctrl = self.bones['eye_ctrl']['eye_target']

            controls_string = ", ".join(["'" + x + "'" for x in all_ctrls])

            if main_ctrl:
                script_out = script % (default_controls_string, eye_target, prop_lid_follow_name)
                script_out = script_out + (script % (controls_string, main_ctrl, prop_name))
                return [script_out]

        return [script % (default_controls_string, eye_target, prop_lid_follow_name)]

    def create_widgets(self):

        bpy.ops.object.mode_set(mode='OBJECT')

        # master_eye
        eye_ctrl = self.bones['eye_ctrl']['master_eye']
        create_circle_widget(self.obj, eye_ctrl, head_tail=1.0)

        # eye target
        eye_target = self.bones['eye_ctrl']['eye_target']
        create_eye_widget(self.obj, eye_target)

        # eye hook
        if 'eye_hook' in self.bones['eye_ctrl']:
            eye_target = self.bones['eye_ctrl']['eye_hook']
            create_gear_widget(self.obj, eye_target, size=10.0)

        # top lid master
        if 'top_lid_master' in self.bones['eye_ctrl']:
            top_lid_master = self.bones['eye_ctrl']['top_lid_master']
            create_cube_widget(self.obj, top_lid_master)

        # bottom lid master
        if 'bottom_lid_master' in self.bones['eye_ctrl']:
            bottom_lid_master = self.bones['eye_ctrl']['bottom_lid_master']
            create_cube_widget(self.obj, bottom_lid_master)

        if 'common' in self.bones['eye_ctrl']:
            common_ctrl = self.bones['eye_ctrl']['common']
            if self.is_clustered():
                cluster = self.get_cluster_positions()
                create_widget_from_cluster(self.obj, common_ctrl, cluster)
            else:
                create_eyes_widget(self.obj, common_ctrl)

        super().create_widgets()

    def cleanup(self):

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        # cleanup
        for mch in self.bones['mch'][strip_org(self.lid_bones['top'][0])]:
            edit_bones.remove(edit_bones[mch])
        for mch in self.bones['mch'][strip_org(self.lid_bones['bottom'][0])]:
            edit_bones.remove(edit_bones[mch])

    def generate(self):
        return super().generate()


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('eye.L')
    bone.head[:] = 0.0360, -0.0686, 0.1107
    bone.tail[:] = 0.0360, -0.0848, 0.1107
    bone.roll = 0.0000
    bone.use_connect = False
    bones['eye.L'] = bone.name
    bone = arm.edit_bones.new('lid.T.L')
    bone.head[:] = 0.0515, -0.0692, 0.1104
    bone.tail[:] = 0.0474, -0.0785, 0.1136
    bone.roll = 0.1166
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['eye.L']]
    bones['lid.T.L'] = bone.name
    bone = arm.edit_bones.new('lid.B.L')
    bone.head[:] = 0.0237, -0.0826, 0.1058
    bone.tail[:] = 0.0319, -0.0831, 0.1050
    bone.roll = -0.1108
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['eye.L']]
    bones['lid.B.L'] = bone.name
    bone = arm.edit_bones.new('lid.T.L.001')
    bone.head[:] = 0.0474, -0.0785, 0.1136
    bone.tail[:] = 0.0394, -0.0838, 0.1147
    bone.roll = 0.0791
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L']]
    bones['lid.T.L.001'] = bone.name
    bone = arm.edit_bones.new('lid.B.L.001')
    bone.head[:] = 0.0319, -0.0831, 0.1050
    bone.tail[:] = 0.0389, -0.0826, 0.1050
    bone.roll = -0.0207
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.L']]
    bones['lid.B.L.001'] = bone.name
    bone = arm.edit_bones.new('lid.T.L.002')
    bone.head[:] = 0.0394, -0.0838, 0.1147
    bone.tail[:] = 0.0317, -0.0832, 0.1131
    bone.roll = -0.0356
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L.001']]
    bones['lid.T.L.002'] = bone.name
    bone = arm.edit_bones.new('lid.B.L.002')
    bone.head[:] = 0.0389, -0.0826, 0.1050
    bone.tail[:] = 0.0472, -0.0781, 0.1068
    bone.roll = 0.0229
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.L.001']]
    bones['lid.B.L.002'] = bone.name
    bone = arm.edit_bones.new('lid.T.L.003')
    bone.head[:] = 0.0317, -0.0832, 0.1131
    bone.tail[:] = 0.0237, -0.0826, 0.1058
    bone.roll = 0.0245
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.T.L.002']]
    bones['lid.T.L.003'] = bone.name
    bone = arm.edit_bones.new('lid.B.L.003')
    bone.head[:] = 0.0472, -0.0781, 0.1068
    bone.tail[:] = 0.0515, -0.0692, 0.1104
    bone.roll = -0.0147
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['lid.B.L.002']]
    bones['lid.B.L.003'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['eye.L']]
    pbone.rigify_type = 'experimental.bendy_eye'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.T.L.003']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['lid.B.L.003']]
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

    # Add driver
    params.add_eyefollow = bpy.props.BoolProperty(
        name="Add eye-follow driver",
        default=True,
        description="Add an eye-follow driver to this eye(s)"
        )

    # Pairing and clustering
    def set_clustered(self, value):

        if value:
            self['paired_eye'] = ''

        self['clustered'] = value

    def get_clustered(self):

        if 'clustered' in self.keys():
            return self['clustered']
        else:
            return False

    params.clustered_eye = bpy.props.BoolProperty(
        name="Clustered",
        default=False,
        description="This eye belongs to a cluster",
        set=set_clustered,
        get=get_clustered
    )

    params.make_control = bpy.props.BoolProperty(
        name="Control",
        default=True,
        description="Create a control bone for the copy"
    )

    params.make_deform = bpy.props.BoolProperty(
        name="Deform",
        default= True,
        description="Create a deform bone for the copy"
    )

    def set_paired(self, value):
        context = bpy.context
        obj = context.active_object
        pb = context.active_pose_bone

        if not pb:
            return

        name = pb.name

        if value not in obj.pose.bones or obj.pose.bones[value].rigify_type != 'experimental.bendy_eye':
            self['paired_eye'] = ''
            return
        else:
            self['paired_eye'] = value

        if value == name:
            return

        if obj.pose.bones[value].rigify_parameters.paired_eye != name:
            obj.pose.bones[value].rigify_parameters.clustered_eye = False
            obj.pose.bones[value].rigify_parameters.paired_eye = name

    def get_paired(self):
        if 'paired_eye' in self.keys():
            return self['paired_eye']
        else:
            return ''

    class EyeName(bpy.types.PropertyGroup):
        name = bpy.props.StringProperty()

    bpy.utils.register_class(EyeName)

    IDStore = bpy.types.WindowManager
    IDStore.other_eyes = bpy.props.CollectionProperty(type=EyeName)

    params.set_paired = set_paired
    params.get_paired = get_paired

    params.paired_eye = bpy.props.StringProperty(
        name='Paired eye',
        default="",
        description='Name of paired eye',
        set=set_paired,
        get=get_paired
    )


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters."""

    r = layout.row()
    r.prop(params, "add_eyefollow")

    r = layout.row()
    r.prop(params, "make_control")

    r = layout.row()
    r.prop(params, "make_deform")

    r = layout.row()
    r.prop(params, "clustered_eye")

    id_store = bpy.context.window_manager

    for i in range(0, len(id_store.other_eyes)):
        id_store.other_eyes.remove(0)

    bones = bpy.context.active_object.pose.bones
    for t in bones:
        if t.rigify_type == 'experimental.bendy_eye':
            id_store.other_eyes.add()
            id_store.other_eyes[-1].name = t.name

    r = layout.row()
    r.prop_search(params, "paired_eye", id_store, "other_eyes", text="Paired eye", icon='BONE_DATA')

    if params.clustered_eye:
        r.enabled = False

    ControlLayersGenerator.add_layers_ui(layout, params)