import bpy
from enum import Enum
from ...utils import copy_bone, strip_org, make_mechanism_name, make_deformer_name
from ...utils import put_bone, make_constraints_from_string, create_sphere_widget


class ChainType(Enum):
    TYPE_IK = 'ik'
    TYPE_FK = 'fk'
    TYPE_MCH_BASED = 'mch_based'
    TYPE_DEF_BASED = 'def_based'


class Chain:

    CTRL_SCALE = 0.5   # size of ctrls relative to orientation_bone
    MCH_SCALE = 0.3     # size of mchs relative to chain bone from which mch is spawned

    def __init__(self, obj, base_bone, orientation_bone=None, chain_type=None, parent=None):
        """

        :param obj:
        :param base_bone:
        :param orientation_bone:
        :param chain_type:
        :type chain_type: ChainType
        :param parent:
        :type parent: Chain
        """

        self.chain_type = chain_type or ChainType.TYPE_MCH_BASED
        self.obj = obj
        self._base_bone = base_bone
        self.base_name = strip_org(self._base_bone)
        self.orientation_bone = orientation_bone or self._base_bone
        self.parent = parent

        self._bones = dict()
        self._bones['org'] = self._get_chain_org_bones()

        self.active = True

    def _get_chain_org_bones(self):
        """
        Get all the bone names belonging to a chain or subchain starting with first_name.
        The chain stops on the last bone or where the bones fork
        :return:
        :rtype: list
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        first_name = self._base_bone

        chain = [first_name]
        # chain.extend(connected_children_names(self.obj, first_name)) DON'T USE THIS it works BAD

        bone = edit_bones[first_name]

        while True:
            connects = 0
            con_name = ""

            for child in bone.children:
                if child.use_connect:
                    connects += 1
                    con_name = child.name

            if connects == 1:
                chain += [con_name]
                bone = edit_bones[con_name]
            else:
                break

        return chain

    @property
    def length(self):
        return len(self._bones['org'])

    def make_mch_chain(self):
        """
        Create all MCHs needed on a single chain
        :return:
        :rtype: list
        """

        if not self.active:
            return []

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        chain = self._bones['org']

        self._bones['mch'] = []

        if self.chain_type == ChainType.TYPE_MCH_BASED:
            for chain_bone in chain:
                mch = make_mechanism_name(strip_org(chain_bone))
                mch = copy_bone(self.obj, chain_bone, assign_name=mch)
                edit_bones[mch].parent = None
                edit_bones[mch].use_connect = False
                edit_bones[mch].length *= self.MCH_SCALE
                self._bones['mch'].append(mch)

        return self._bones['mch']

    def make_def_chain(self):
        """
        Creates all DEFs in chain
        :return:
        :rtype:list
        """

        if not self.active:
            return []

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        chain = self._bones['org']

        self._bones['def'] = []

        if self.chain_type == ChainType.TYPE_MCH_BASED:
            for chain_bone in chain:
                def_bone = make_deformer_name(strip_org(chain_bone))
                def_bone = copy_bone(self.obj, chain_bone, assign_name=def_bone)
                edit_bones[def_bone].parent = None
                edit_bones[def_bone].use_connect = False
                self._bones['def'].append(def_bone)

        return self._bones['def']

    def make_ctrl_chain(self):
        """
        Create all ctrls in chain
        :return:
        """

        if not self.active:
            return []

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        chain = self._bones['org']

        self._bones['ctrl'] = []

        if self.chain_type == ChainType.TYPE_MCH_BASED:
            for chain_bone in chain:
                ctrl = strip_org(chain_bone)
                ctrl = copy_bone(self.obj, self.orientation_bone, assign_name=ctrl)
                put_bone(self.obj, ctrl, edit_bones[chain_bone].head)
                edit_bones[ctrl].length = edit_bones[self.orientation_bone].length * self.CTRL_SCALE
                edit_bones[ctrl].parent = None
                edit_bones[ctrl].use_connect = False
                self._bones['ctrl'].append(ctrl)

            last_name = chain[-1]
            last_ctrl = copy_bone(self.obj, self.orientation_bone, assign_name=strip_org(last_name))
            put_bone(self.obj, last_ctrl, edit_bones[last_name].tail)
            edit_bones[last_ctrl].length = edit_bones[self.orientation_bone].length * self.CTRL_SCALE
            edit_bones[last_ctrl].parent = None
            edit_bones[last_ctrl].use_connect = False
            self._bones['ctrl'].append(last_ctrl)

        return self._bones['ctrl']

    def parent_bones(self):
        """
        Non-overwriting parenting pass
        :return:
        """

        if not self.active:
            return []

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        if self.chain_type == ChainType.TYPE_MCH_BASED:
            # Parent mchs to controls
            mch_bones = self.get_chain_bones_by_type('mch')
            for i, name in enumerate(mch_bones):
                mch_bone = edit_bones[name]
                parent = self.get_chain_bone_by_index(index=i, bone_type='ctrl')
                if parent and mch_bone.parent is None:
                    mch_bone.parent = edit_bones[parent]

            ctrl_bones = self.get_chain_bones_by_type('ctrl')
            for ctrl in ctrl_bones:
                if edit_bones[ctrl].parent is None:
                    edit_bones[ctrl].parent = edit_bones[self._base_bone].parent
                    edit_bones[ctrl].use_connect = False

    def make_constraints(self):
        """
        make constraints
        :return:
        """

        if not self.active:
            return []

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        if self.chain_type == ChainType.TYPE_MCH_BASED:
            def_bones = self.get_chain_bones_by_type('def')
            mch_bones = self.get_chain_bones_by_type('mch')
            for i, name in enumerate(def_bones):
                owner_pb = pose_bones[name]
                subtarget = mch_bones[i]
                make_constraints_from_string(owner_pb, self.obj, subtarget, "CT1.0WW")

                tail_subtarget = self.get_chain_bone_by_index(index=i+1, bone_type='ctrl')
                if tail_subtarget:
                    make_constraints_from_string(owner_pb, self.obj, tail_subtarget, "DT1.0#ST1.0")

    def create_widgets(self, ctrl_wgt_function=create_sphere_widget, **kwargs):
        """
        Creates ctrl widgets
        A custom create wgt function can be passed as argument together with its own kwargs
        :return:
        """

        if not self.active:
            return []

        bpy.ops.object.mode_set(mode='OBJECT')

        if self.chain_type == ChainType.TYPE_MCH_BASED:
            ctrl_bones = self.get_chain_bones_by_type('ctrl')
            for name in ctrl_bones:
                ctrl_wgt_function(self.obj, name, **kwargs)

    def get_chain_bones_by_type(self, bone_type='org'):
        """
        Returns a list of bones generated by the chain with bone_type
        :param bone_type:
        :return:
        :rtype: list(str)
        """

        return self._bones[bone_type]

    def get_chain_bone_by_index(self, index, bone_type='org'):
        """
        Returns the nth bone
        :param index:
        :param bone_type:
        :return: str
        """

        size = len(self._bones[bone_type])
        if index < -size or index >= size:
            return ""

        return self._bones[bone_type][index]
