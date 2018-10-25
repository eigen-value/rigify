import bpy
from ...utils import copy_bone


class ControlSnapper:
    """
    Control Snapper compatible with BaseRig definition
    """

    POSITION_RELATIVE_ERROR = 1e-3  # error below which two positions are considered equal (relative to bone len)

    def __init__(self, obj, bones):
        """

        :param obj:
        :param bones:
        """

        self.obj = obj
        self.bones = bones

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

    def update_parent(self, old_parent, new_parent):
        """
        Moving parent from old to new
        :param old_parent:
        :param new_parent:
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for child in edit_bones[old_parent].children:
            child.parent = edit_bones[new_parent]

    def aggregate_ctrls(self, same_parent=True):
        """
        Aggregate controls should be called before constraining but AFTER parenting
        two ctrls are aggregated only if they are close enough and have the same parent
        or same_parent = False
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        aggregates = []

        all_ctrls = self.flatten(self.bones['ctrl'])

        while 1:
            ctrl = all_ctrls[0]
            aggregate = [ctrl]
            for ctrl2 in all_ctrls[1:]:
                error = edit_bones[ctrl].length * self.POSITION_RELATIVE_ERROR
                if (edit_bones[ctrl].head - edit_bones[ctrl2].head).magnitude <= error \
                        and (not same_parent or edit_bones[ctrl].parent == edit_bones[ctrl2].parent):
                    aggregate.append(ctrl2)
            for element in aggregate:
                all_ctrls.remove(element)
            if len(aggregate) > 1:
                aggregates.append(aggregate)
            if not all_ctrls:
                break

        if aggregates:
            self.bones['ctrl']['aggregate'] = []

        for aggregate in aggregates:
            name = self.get_aggregate_name(aggregate)
            aggregate_ctrl = copy_bone(self.obj, aggregate[0], name)
            self.bones['ctrl']['aggregate'].append(aggregate_ctrl)
            for ctrl in aggregate:
                self.update_parent(ctrl, aggregate_ctrl)
                edit_bones.remove(edit_bones[ctrl])
                for chain in self.bones['ctrl']:
                    if chain == 'aggregate':
                        continue
                    if ctrl in self.bones['ctrl'][chain]:
                        i = self.bones['ctrl'][chain].index(ctrl)
                        self.bones['ctrl'][chain][i] = aggregate_ctrl
                        continue

    def get_aggregate_name(self, aggregate):
        """
        Returns the collective name for an aggregatable bones name list
        :param aggregate:
        :type aggregate: list(str)
        :return:
        """

        total = '.'.join(aggregate)

        root = aggregate[0].split('.')[0]
        for name in aggregate[1:]:
            if name.split('.')[0] not in root:
                root = '.'.join([root, name.split('.')[0]])

        name = root

        t_b = ''
        if 'T' in total and 'B' in total:
            t_b = ''
        elif 'T' in total:
            t_b = 'T'
        elif 'B' in total:
            t_b = 'B'

        if t_b:
            name = '.'.join([name, t_b])

        l_r = ''
        if 'L' in total and 'R' in total:
            l_r = ''
        elif 'L' in total:
            l_r = 'L'
        elif 'R' in total:
            l_r = 'R'

        if l_r:
            name = '.'.join([name, l_r])

        return name
