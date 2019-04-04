import bpy
from ...utils import strip_org
from ...utils import MetarigError, get_rig_type

from .chain import Chain, ChainType
from .base_rig import BaseRig
from .control_layers_generator import ControlLayersGenerator


class ChainyRig(BaseRig):

    def __init__(self, obj, bone_name, params, single=False, chain_type=None):

        super().__init__(obj, bone_name, params)

        self.single = single
        self.chain_type = chain_type or ChainType.TYPE_MCH_BASED
        self.orientation_bone = self.get_orientation_bone()

        self.chain_objects = dict()
        self.chains = self.get_chains()

        self.layer_generator = ControlLayersGenerator(self)

    def get_unconnected_children(self, bone=None):

        if not bone:
            bone = self.base_bone

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones
        bones = filter(lambda child: not child.use_connect, edit_bones[bone].children)
        names = list(map(lambda b: b.name, bones))

        return names

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
                        chain = Chain(self.obj, name, self.orientation_bone, chain_type=self.chain_type)
                        self.chain_objects[chain.base_name] = chain
                        chains[name] = self.get_subchains(name)
            else:
                name = self.bones['org'][0]
                chain = Chain(self.obj, name, self.orientation_bone, chain_type=self.chain_type)
                self.chain_objects[chain.base_name] = chain
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

    def get_subchains(self, name, exclude=None):
        """

        :param name:
        :type name: parent chain bone name
        :parameter exclude: list of subchains to exclude
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        if exclude is None:
            exclude = []

        print("exclude:")
        print(exclude)

        subchains = []

        chain = self.get_chain_object_by_name(name)

        for bone in edit_bones[name].children:
            if self.obj.pose.bones[bone.name].rigify_type == "" and not bone.use_connect and bone.name not in exclude:
                subchain = Chain(self.obj, bone.name, self.orientation_bone, chain_type=chain.chain_type, parent=chain)
                if subchain.length != chain.length:
                    raise MetarigError("Subchains of chain starting with %s are not the same length! assign a rig_type/"
                                       "unconnected children of main bone of chain" % name)
                else:
                    subchains.append(bone.name)
                    self.chain_objects[subchain.base_name] = subchain

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

    def get_chain_object_by_name(self, name):
        """
        returns a chain object by the name of the first org w/o ORG prefix
        :return:
        :rtype: Chain
        """

        name = strip_org(name)
        return self.chain_objects[name]

    def set_chain_active(self, name, active=True):
        """
        Activates / deactivates a chain. Inactive chains will not generate independently
        :param name:
        :param active:
        :return:
        """

        chain = self.get_chain_object_by_name(name)
        chain.active = active

    def create_mch(self):

        for name in self.chains:
            chain = self.get_chain_object_by_name(name)
            self.bones['mch'][chain.base_name] = chain.make_mch_chain()

            for subname in self.chains[name]:
                subchain = self.get_chain_object_by_name(subname)
                self.bones['mch'][subchain.base_name] = subchain.make_mch_chain()

    def create_def(self):

        for name in self.chains:
            chain = self.get_chain_object_by_name(name)
            self.bones['def'][chain.base_name] = chain.make_def_chain()

            for subname in self.chains[name]:
                subchain = self.get_chain_object_by_name(subname)
                self.bones['def'][subchain.base_name] = subchain.make_def_chain()

    def create_controls(self):

        for name in self.chains:
            chain = self.get_chain_object_by_name(name)
            self.bones['ctrl'][chain.base_name] = chain.make_ctrl_chain()

            for subname in self.chains[name]:
                subchain = self.get_chain_object_by_name(subname)
                self.bones['ctrl'][subchain.base_name] = subchain.make_ctrl_chain()

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

        for chain in self.chain_objects:
            chain_object = self.chain_objects[chain]
            chain_object.parent_bones()

            if chain_object.parent is not None:         # subchains ctrls need reparenting
                parent_chain_object = chain_object.parent
                subchain_ctrls = chain_object.get_chain_bones_by_type('ctrl')
                for i, ctrl in enumerate(subchain_ctrls):
                    subchain_ctrl_bone = edit_bones[ctrl]
                    parent_ctrl = parent_chain_object.get_chain_bone_by_index(index=i, bone_type='ctrl')
                    if parent_ctrl:
                        subchain_ctrl_bone.parent = edit_bones[parent_ctrl].parent

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

        for chain_object in self.chain_objects:
            self.chain_objects[chain_object].make_constraints()

    def create_widgets(self):

        bpy.ops.object.mode_set(mode='OBJECT')

        for chain_object in self.chain_objects:
            self.chain_objects[chain_object].create_widgets()

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
        self.orient_org_bones()
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
