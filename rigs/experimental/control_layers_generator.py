import bpy


class ControlLayersGenerator:

    def __init__(self, rig):

        self.rig = rig
        self.obj = rig.obj
        self.params = rig.params

        if self.rig.params.primary_layers_extra:
            self.rig.primary_layers = list(self.rig.params.primary_layers)
        else:
            self.rig.primary_layers = None

        if self.rig.params.secondary_layers_extra:
            self.rig.secondary_layers = list(self.rig.params.secondary_layers)
        else:
            self.rig.secondary_layers = None

        if self.rig.params.tweak_layers_extra:
            self.rig.tweak_layers = list(self.rig.params.tweak_layers)
        else:
            self.rig.tweak_layers = None

    def assign_layer(self, primary_ctrls, all_ctrls):
        """
        Assign ctrl bones to layer
        :param primary_ctrls:
        :type primary_ctrls: list(str)
        :param all_ctrls:
        :type all_ctrls: list(str)
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for bone in primary_ctrls:
            if self.rig.primary_layers:
                edit_bones[bone].layers = self.rig.params.primary_layers
        for bone in all_ctrls:
            if self.rig.secondary_layers and bone not in primary_ctrls:
                edit_bones[bone].layers = self.rig.params.secondary_layers

    def assign_tweak_layers(self, tweaks):
        """
        Assign tweak bones to layer
        :param tweaks:
        :type tweaks: list(str)
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for bone in tweaks:
            if self.rig.tweak_layers:
                edit_bones[bone].layers = self.rig.params.tweak_layers


    @staticmethod
    def add_layer_parameters(params):
        # Setting up extra layers for the primary & secondary controls
        params.primary_layers_extra = bpy.props.BoolProperty(
            name="primary_layers_extra",
            default=True,
            description=""
        )
        params.primary_layers = bpy.props.BoolVectorProperty(
            size=32,
            description="Layers for the primary controls to be on",
            default=tuple([i == 1 for i in range(0, 32)])
        )
        params.secondary_layers_extra = bpy.props.BoolProperty(
            name="secondary_layers_extra",
            default=True,
            description=""
        )
        params.secondary_layers = bpy.props.BoolVectorProperty(
            size=32,
            description="Layers for the secondary controls to be on",
            default=tuple([i == 1 for i in range(0, 32)])
        )

    @staticmethod
    def add_tweak_layer_parameters(params):
        params.tweak_layers_extra = bpy.props.BoolProperty(
            name="tweak_layers_extra",
            default=True,
            description=""
        )
        params.tweak_layers = bpy.props.BoolVectorProperty(
            size=32,
            description="Layers for the tweak controls to be on",
            default=tuple([i == 1 for i in range(0, 32)])
        )

    @staticmethod
    def add_layers_ui(layout, params):
        layers = ["primary_layers", "secondary_layers"]

        bone_layers = bpy.context.active_pose_bone.bone.layers[:]

        for layer in layers:
            r = layout.row()
            r.prop(params, layer + "_extra")
            r.active = getattr(params, layer + "_extra")

            col = r.column(align=True)
            row = col.row(align=True)
            for i in range(8):
                icon = "NONE"
                if bone_layers[i]:
                    icon = "LAYER_ACTIVE"
                row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

            row = col.row(align=True)
            for i in range(16, 24):
                icon = "NONE"
                if bone_layers[i]:
                    icon = "LAYER_ACTIVE"
                row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

            col = r.column(align=True)
            row = col.row(align=True)

            for i in range(8, 16):
                icon = "NONE"
                if bone_layers[i]:
                    icon = "LAYER_ACTIVE"
                row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

            row = col.row(align=True)
            for i in range(24, 32):
                icon = "NONE"
                if bone_layers[i]:
                    icon = "LAYER_ACTIVE"
                row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

    @staticmethod
    def add_tweak_layers_ui(layout, params):

        layer = "tweak_layers"
        bone_layers = bpy.context.active_pose_bone.bone.layers[:]

        r = layout.row()
        r.prop(params, layer + "_extra")
        r.active = getattr(params, layer + "_extra")

        col = r.column(align=True)
        row = col.row(align=True)
        for i in range(8):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

        row = col.row(align=True)
        for i in range(16, 24):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

        col = r.column(align=True)
        row = col.row(align=True)

        for i in range(8, 16):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)

        row = col.row(align=True)
        for i in range(24, 32):
            icon = "NONE"
            if bone_layers[i]:
                icon = "LAYER_ACTIVE"
            row.prop(params, layer, index=i, toggle=True, text="", icon=icon)