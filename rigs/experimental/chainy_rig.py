import bpy
from ...utils import strip_org, make_mechanism_name, copy_bone, make_deformer_name, put_bone
from ...utils import create_sphere_widget, strip_def
from ...utils import MetarigError, get_rig_type
from ...utils import make_constraints_from_string

from .base_rig import BaseRig
from .control_layers_generator import ControlLayersGenerator


class ChainyRig(BaseRig):

    CTRL_SCALE = 0.05
    MCH_SCALE = 0.3

    def __init__(self, obj, bone_name, params, single=False):

        super().__init__(obj, bone_name, params)

        self.single = single

        self.chains = self.get_chains()

        self.orientation_bone = self.get_orientation_bone()

        self.layer_generator = ControlLayersGenerator(self)

    def get_chains(self):
            """
            Returns all the ORG bones starting a chain in the rig and their subchains start bones
            :return:
            """

            bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = self.obj.data.edit_bones

            chains = dict()

            if not self.single:
                for name in self.bones['org'][1:]:
                    eb = edit_bones[name]
                    if not eb.use_connect and eb.parent == edit_bones[self.base_bone]:
                        chains[name] = self.get_subchains(name)
            else:
                name = self.bones['org'][0]
                chains[name] = self.get_subchains(name)

            return chains

    def get_chain_bones(self, first_name):
        """
        Get all the bone names belonging to a chain or subchain starting with first_name
        :param first_name:
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

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

    def get_subchains(self, name):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        subchains = []

        chain = self.get_chain_bones(name)

        for bone in edit_bones[name].children:
            if self.obj.pose.bones[bone.name].rigify_type == "" and not bone.use_connect:
                if len(self.get_chain_bones(bone.name)) != len(chain):
                    raise MetarigError("Subchains of chain starting with %s are not the same length! assign a rig_type/"
                                       "unconnected children of main bone of chain" % name)
                else:
                    subchains.append(bone.name)

        return subchains

    def get_orientation_bone(self):
        """
        Get bone defining orientation of ctrls
        :return:
        """
        bpy.ops.object.mode_set(mode='EDIT')

        orientation_bone = self.obj.pose.bones[self.base_bone]

        while True:
            if orientation_bone.parent is None:
                break
            elif orientation_bone.parent.rigify_type != "":
                module = get_rig_type(orientation_bone.parent.rigify_type)
                if issubclass(module.Rig, ChainyRig):
                    orientation_bone = orientation_bone.parent
                else:
                    break
            else:
                break

        return orientation_bone.name

    def make_mch_chain(self, first_name):
        """
        Create all MCHs needed on a single chain
        :param first_name: name of the first bone in the chain
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        chain = self.get_chain_bones(first_name)

        self.bones['mch'][strip_org(first_name)] = []

        for chain_bone in chain:
            mch = copy_bone(self.obj, chain_bone, assign_name=make_mechanism_name(strip_org(chain_bone)))
            edit_bones[mch].parent = None
            edit_bones[mch].length *= self.MCH_SCALE
            self.bones['mch'][strip_org(first_name)].append(mch)

    def create_mch(self):

        for name in self.chains:
            self.make_mch_chain(name)

            for subname in self.chains[name]:
                self.make_mch_chain(subname)

    def make_def_chain(self, first_name):
        """
        Creates all DEFs in chain
        :param first_name:
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        chain = self.get_chain_bones(first_name)

        self.bones['def'][strip_org(first_name)] = []

        for chain_bone in chain:
            def_bone = copy_bone(self.obj, chain_bone, assign_name=make_deformer_name(strip_org(chain_bone)))
            edit_bones[def_bone].parent = None
            self.bones['def'][strip_org(first_name)].append(def_bone)

    def create_def(self):

        for name in self.chains:
            self.make_def_chain(name)

            for subname in self.chains[name]:
                self.make_def_chain(subname)

    def make_ctrl_chain(self, first_name):
        """
        Create all ctrls in chain
        :param first_name:
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        chain = self.get_chain_bones(first_name)

        self.bones['ctrl'][strip_org(first_name)] = []

        for chain_bone in chain:
            ctrl = copy_bone(self.obj, self.orientation_bone, assign_name=strip_org(chain_bone))
            put_bone(self.obj, ctrl, edit_bones[chain_bone].head)
            edit_bones[ctrl].length = edit_bones[self.orientation_bone].length * self.CTRL_SCALE
            self.bones['ctrl'][strip_org(first_name)].append(ctrl)

        last_name = chain[-1]
        last_ctrl = copy_bone(self.obj, self.orientation_bone, assign_name=strip_org(last_name))
        put_bone(self.obj, last_ctrl, edit_bones[last_name].tail)
        edit_bones[last_ctrl].length = edit_bones[self.orientation_bone].length * self.CTRL_SCALE
        self.bones['ctrl'][strip_org(first_name)].append(last_ctrl)

    def create_controls(self):

        for name in self.chains:
            self.make_ctrl_chain(name)

            for subname in self.chains[name]:
                self.make_ctrl_chain(subname)

    def get_ctrl_by_index(self, chain, index):
        """
        Return ctrl in index position of chain
        :param chain:
        :param index:
        :return: bone name
        :rtype: str
        """

        ctrl_chain = self.bones['ctrl'][chain]
        if index >= len(ctrl_chain):
            return ""

        return ctrl_chain[index]

    def parent_bones(self):
        """
        Specify bone parenting
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        # PARENT chain MCH-bones
        for subchain in self.bones['mch']:
            for i, name in enumerate(self.bones['mch'][subchain]):
                mch_bone = edit_bones[name]
                parent = self.get_ctrl_by_index(chain=subchain, index=i)
                if parent:
                    mch_bone.parent = edit_bones[parent]

        # PARENT subchain sibling controls
        for chain in self.chains:
            for subchain in self.chains[chain]:
                for i, ctrl in enumerate(self.bones['ctrl'][strip_org(subchain)]):
                    ctrl_bone = edit_bones[ctrl]
                    parent = self.get_ctrl_by_index(chain=strip_org(chain), index=i)
                    if parent:
                        ctrl_bone.parent = edit_bones[parent].parent

    def assign_layers(self):
        """
        Look for primary and secondary ctrls and use self.layer_generator to assign
        :return:
        """
        pass

    def make_constraints(self):
        """
        Make constraints for each bone subgroup
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        # Constrain DEF-bones
        for subchain in self.bones['def']:
            for i, name in enumerate(self.bones['def'][subchain]):
                owner_pb = pose_bones[name]
                subtarget = make_mechanism_name(strip_def(name))
                make_constraints_from_string(owner_pb, self.obj, subtarget, "CT1.0WW")

                tail_subtarget = self.get_ctrl_by_index(chain=subchain, index=i+1)

                if tail_subtarget:
                    make_constraints_from_string(owner_pb, self.obj, tail_subtarget, "DT1.0#ST1.0")

    def create_widgets(self):

        bpy.ops.object.mode_set(mode='OBJECT')
        for chain in self.bones['ctrl']:
            for ctrl in self.bones['ctrl'][chain]:
                create_sphere_widget(self.obj, ctrl)

    def make_drivers(self):
        """
        This method is used to make drivers and returns a snippet to be put in rig_ui.py
        :return:
        :rtype: list
        """
        return [""]

    def cleanup(self):
        pass

    def generate(self):
        self.create_mch()
        self.create_def()
        self.create_controls()
        self.parent_bones()

        # following passes should be made ONLY when ctrls are completely defined
        self.assign_layers()
        self.make_constraints()
        self.create_widgets()
        rig_ui_script = self.make_drivers()

        self.cleanup()

        return rig_ui_script

    @staticmethod
    def add_parameters(params):

        ControlLayersGenerator.add_layer_parameters(params)

    @staticmethod
    def parameters_ui(layout, params):

        ControlLayersGenerator.add_layers_ui(layout, params)
