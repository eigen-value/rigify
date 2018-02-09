from .meshy_rig import MeshyRig


class Rig(MeshyRig):

    def __init__(self, obj, bone_name, params):
        super().__init__(obj, bone_name, params)

    def generate(self):
        super().generate()
