#########################################################################
# Meshy rig is a base-class for subchain-based rigs with snapping ctrls #
# and glue bones                                                        #
#########################################################################

from .control_snapper import ControlSnapper
from .chainy_rig import ChainyRig


class MeshyRig(ChainyRig):

    def __init__(self, obj, bone_name, params):
        super().__init__(obj, bone_name, params)

        self.control_snapper = ControlSnapper(self.obj, self.bones)

    def generate(self):

        self.create_mch()
        self.create_def()
        self.create_controls()
        self.parent_bones()

        self.control_snapper.aggregate_ctrls()

        self.make_constraints()
        self.create_widgets()

        return [""]

