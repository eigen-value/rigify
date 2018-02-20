import bpy


class BaseRig(object):

    def __init__(self, obj, bone_name, params):
        """
        Rig Base class the bones struct is a dict with 'org' as a list and 'def' 'mch' and 'ctrl' dicts
        ctrls mchs and defs must be organized in groups. If your Rig Class has just one group you can call it all_ctrls
        :param obj:
        :param bone_name:
        :param params:
        """

        self.obj = obj
        self.params = params
        self.bones = dict()
        self.bones['org'] = [bone_name]
        self.base_bone = bone_name

        # Get all the recursive ORG children of the base bone BUT the rig_type trees
        for edit_bone in self.obj.data.edit_bones[bone_name].children:
            if self.obj.pose.bones[edit_bone.name].rigify_type != "":
                continue
            else:
                self.bones['org'].append(edit_bone.name)
            for child in edit_bone.children_recursive:
                self.bones['org'].append(child.name)

        self.bones['ctrl'] = dict()
        self.bones['mch'] = dict()
        self.bones['def'] = dict()

    def orient_org_bones(self):
        """
        This function re-orients org bones so that created bones are properly aligned and cns can work
        :return:
        """
        pass

    def create_mch(self):
        pass

    def create_def(self):
        pass

    def create_controls(self):
        pass

    def create_widgets(self):
        pass

    def make_constraints(self):
        pass

    def parent_bones(self):
        pass

    def generate(self):
        pass

    def flatten(self, bones):
        """
        Flattens a bones dictionary
        :param bones:
        :return:
        :rtype: list
        """

        all_bones = []

        if isinstance(bones, dict):
            for key in bones:
                all_bones.extend(self.flatten(bones[key]))
            return all_bones
        else:
            return bones

    def get_all_ctrls(self):
        return self.flatten(self.bones['ctrl'])

    @staticmethod
    def add_parameters(params):
        """
        This method add more parameters to params
        :param params: rigify_parameters of a pose_bone
        :return:
        """

        pass

    @staticmethod
    def parameters_ui(layout, params):
        """
        This method draws the UI of the rigify_parameters defined on the pose_bone
        :param layout:
        :param params:
        :return:
        """

        pass
