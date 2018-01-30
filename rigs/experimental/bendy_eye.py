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
        self.lid_len = len(edit_bones[lid_bones[0]].children_recursive) + 1

        # Check both have same length
        for lid in lid_bones:
            if len(edit_bones[lid].children_recursive) != self.lid_len - 1:
                raise MetarigError("All lip chains must be the same length")

        l_b_head_positions = [edit_bones[name].head for name in lid_bones]
        head_sum = l_b_head_positions[0]
        for h in l_b_head_positions[1:]:
            head_sum = head_sum + h
        eyelids_center = head_sum / 4

        for l_b in lid_bones:
            head = edit_bones[l_b].head
            if (head - eyelids_center).z < 0:
                eyelids_bones_dict['bottom'].append(l_b)
            elif (head - eyelids_center).magnitude > 0:
                eyelids_bones_dict['top'].append(l_b)
            else:
                raise MetarigError("Badly drawn eyelids on %s" % self.bones['org'][0])

        if not (len(eyelids_bones_dict['top']) == len(eyelids_bones_dict['bottom']) == 2):
            raise MetarigError("Badly drawn eyelids on %s" % self.bones['org'][0])

        return eyelids_bones_dict

    def create_mch(self):
        super().create_mch()

    def create_def(self):
        super().create_def()

    def create_controls(self):
        super().create_controls()

    def make_constraints(self):
        super().make_constraints()

    def parent_bones(self):
        super().parent_bones()

    def generate(self):
        return super().generate()

