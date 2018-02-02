#######################################################################################################################
# Bendy eye contruction rules:
#
#######################################################################################################################

import bpy
import re
from mathutils import Vector
from ...utils import copy_bone, flip_bone, put_bone
from ...utils import org, strip_org, strip_def, make_deformer_name, connected_children_names, make_mechanism_name
from ...utils import create_circle_widget, create_sphere_widget, create_widget, create_cube_widget
from ...utils import MetarigError
from ...utils import make_constraints_from_string
from rna_prop_ui import rna_idprop_ui_prop_get
from ..widgets import create_face_widget, create_eye_widget, create_eyes_widget, create_ear_widget, create_jaw_widget, create_teeth_widget
from .chainy_rig import ChainyRig
from .control_snapper import ControlSnapper


class Rig(ChainyRig):

    def __init__(self, obj, bone_name, params):

        super().__init__(obj, bone_name, params)
        self.control_snapper = ControlSnapper(self.obj, self.bones)

        self.lid_len = None
        self.lid_bones = self.get_eyelids()

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
        self.lid_len = len(connected_children_names(self.obj, lid_bones[0])) + 1

        # Check both have same length
        for lid in lid_bones:
            if len(connected_children_names(self.obj, lid)) != self.lid_len - 1:
                raise MetarigError("All lip chains must be the same length")

        if edit_bones[lid_bones[0]].tail.z < edit_bones[lid_bones[1]].tail.z:
            eyelids_bones_dict['top'].append(lid_bones[1])
            eyelids_bones_dict['bottom'].append(lid_bones[0])
        else:
            eyelids_bones_dict['top'].append(lid_bones[0])
            eyelids_bones_dict['bottom'].append(lid_bones[1])

        if not (len(eyelids_bones_dict['top']) == len(eyelids_bones_dict['bottom']) == 1):
            raise MetarigError("Badly drawn eyelids on %s" % self.bones['org'][0])

        return eyelids_bones_dict

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

        eye_tip_mch_name = copy_bone(self.obj, self.bones['org'][0], eye_mch_name)
        self.bones['eye_mch']['eye_master_tip'] = eye_tip_mch_name
        edit_bones[eye_tip_mch_name].head[:] = edit_bones[eye_tip_mch_name].tail
        tip_len = edit_bones[eye_mch_name].length * 0.25
        edit_bones[eye_tip_mch_name].tail[:] = edit_bones[eye_tip_mch_name].head + Vector((0, 0, tip_len))

        # top lid
        top_lid_chain = [self.lid_bones['top'][0]]
        top_lid_chain.extend(connected_children_names(self.obj, top_lid_chain[0]))
        for l_b in top_lid_chain:
            lid_m_name = copy_bone(self.obj, self.bones['org'][0], eye_mch_name)
            edit_bones[lid_m_name].tail = edit_bones[l_b].head
            self.bones['eye_mch']['eyelid_top'].append(lid_m_name)

        # bottom lid
        bottom_lid_chain = [self.lid_bones['bottom'][0]]
        bottom_lid_chain.extend(connected_children_names(self.obj, bottom_lid_chain[0]))
        for l_b in bottom_lid_chain:
            lid_m_name = copy_bone(self.obj, self.bones['org'][0], eye_mch_name)
            edit_bones[lid_m_name].tail = edit_bones[l_b].head
            self.bones['eye_mch']['eyelid_bottom'].append(lid_m_name)

        # create remaining subchain mch-s
        super().create_mch()

    def create_def(self):
        super().create_def()

    def create_controls(self):
        super().create_controls()

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
            subtarget = self.get_ctrl_by_index(strip_org(self.lid_bones['top'][0]), i)
            make_constraints_from_string(owner, self.obj, subtarget, "DT1.0Y0.0")

        for i, e_m in enumerate(self.bones['eye_mch']['eyelid_bottom']):
            owner = pose_bones[e_m]
            subtarget = self.get_ctrl_by_index(strip_org(self.lid_bones['bottom'][0]), i)
            make_constraints_from_string(owner, self.obj, subtarget, "DT1.0Y0.0")

        # make the standard bendy rig constraints
        super().make_constraints()

    def parent_bones(self):
        super().parent_bones()

    def generate(self):
        self.create_mch()
        self.create_def()
        self.create_controls()
        self.parent_bones()

        self.control_snapper.aggregate_ctrls()

        self.make_constraints()
        self.create_widgets()

        return [""]

