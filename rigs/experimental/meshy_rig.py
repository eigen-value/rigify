#########################################################################
# Meshy rig is a base-class for subchain-based rigs with snapping ctrls #
# and glue bones                                                        #
#########################################################################

from .control_snapper import ControlSnapper
from .chainy_rig import ChainyRig


class MeshyRig(ChainyRig):
    """
    MeshyRig basically adds an aggregate_ctrls pass to ChainyRig generate
    """
    def __init__(self, obj, bone_name, params):
        super().__init__(obj, bone_name, params)

        self.control_snapper = ControlSnapper(self.obj, self.bones)

    def aggregate_ctrls(self):
        self.control_snapper.aggregate_ctrls(same_parent=True)

    def generate(self):
        self.create_mch()
        self.create_def()
        self.create_controls()
        self.parent_bones()

        # ctrls snapping pass
        self.aggregate_ctrls()

        self.assign_layers()
        self.make_constraints()
        self.create_widgets()
        self.cleanup()

        rig_ui_script = self.make_drivers()

        return rig_ui_script
