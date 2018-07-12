#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

import bpy
import imp
import importlib
import importlib.util
import math
import random
import time
import re
import os
from mathutils import Vector, Matrix, Color
from rna_prop_ui import rna_idprop_ui_prop_get

#=============================================
# Glue utilities
#=============================================


def make_constraints_from_string(owner, target, subtarget, fstring):
    """
    Creates and applies constraints on owner bone based on formatted string
    :param owner: the owner pose_bone
    :param target: the target object
    :param subtarget: the bone subtarget name
    :param fstring: formatted string
    :return:
    """

    separator = '#'
    cns_blocks = fstring.split(separator)

    transform_type = ['CL', 'CR', 'CS', 'CT']
    limit_type = ['LL', 'LR', 'LS']
    track_type = ['DT', 'TT', 'ST']
    relationship_type = ['PA']

    for cns in cns_blocks:

        if cns[0:2] in transform_type:
            make_transform_constraint_from_string(owner, target, subtarget, cns)

        if cns[0:2] in limit_type:
            make_limit_constraint_from_string(owner, cns)

        if cns[0:2] in track_type:
            make_track_constraint_from_string(owner, target, subtarget, cns)

        if cns[0:2] in relationship_type:
            make_relation_constraint_from_string(owner, target, subtarget, cns)


def make_transform_constraint_from_string(owner, target, subtarget, fstring):

    # regex is (type)(influence*)(space-space*)(use_offset*)(head_tail*)
    regex = '^(CL|CR|CS|CT)([0-9]*\.?[0-9]+)*([LWP]{2})*(O*)([0-9]*\.?[0-9]+)*$'

    constraint_type = {'CL': 'COPY_LOCATION', 'CR': 'COPY_ROTATION', 'CS': 'COPY_SCALE', 'CT': 'COPY_TRANSFORMS'}
    constraint_space = {'L': 'LOCAL', 'W': 'WORLD', 'P': 'POSE'}

    re_object = re.match(regex, fstring)
    if not re_object:
        return
    else:
        cns_props = re_object.groups()

    cns_type = constraint_type[cns_props[0]]
    const = owner.constraints.new(cns_type)
    const.target = target
    const.subtarget = subtarget

    if cns_type == 'COPY_LOCATION':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.target_space = constraint_space[cns_props[2][0]] if bool(cns_props[2]) else "LOCAL"
        const.owner_space = constraint_space[cns_props[2][1]] if bool(cns_props[2]) else "LOCAL"
        const.use_offset = bool(cns_props[3])
        const.head_tail = float(cns_props[4]) if bool(cns_props[4]) else 0.0
    if cns_type == 'COPY_ROTATION':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.target_space = constraint_space[cns_props[2][0]] if bool(cns_props[2]) else "LOCAL"
        const.owner_space = constraint_space[cns_props[2][1]] if bool(cns_props[2]) else "LOCAL"
        const.use_offset = bool(cns_props[3])
    if cns_type == 'COPY_SCALE':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.target_space = constraint_space[cns_props[2][0]] if bool(cns_props[2]) else "LOCAL"
        const.owner_space = constraint_space[cns_props[2][1]] if bool(cns_props[2]) else "LOCAL"
        const.use_offset = bool(cns_props[3])
    if cns_type == 'COPY_TRANSFORMS':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.target_space = constraint_space[cns_props[2][0]] if bool(cns_props[2]) else "LOCAL"
        const.owner_space = constraint_space[cns_props[2][1]] if bool(cns_props[2]) else "LOCAL"
        const.head_tail = float(cns_props[4]) if bool(cns_props[4]) else 0.0


def make_limit_constraint_from_string(owner, fstring):

    regular_expressions = {'LL': '^(LL)([0-9]*\.?[0-9]+)*(([mM]{1}[XYZ]{1}-?[0-9]*\.?[0-9]+)+)*(T)*(W|L|P)*$',
                           'LR': '^(LR)([0-9]*\.?[0-9]+)*(([mM]{1}[XYZ]{1}-?[0-9]*\.?[0-9]+)+)*(T)*(W|L|P)*$',
                           'LS': '^(LS)([0-9]*\.?[0-9]+)*(([mM]{1}[XYZ]{1}-?[0-9]*\.?[0-9]+)+)*(T)*(W|L|P)*$'}

    # regex is (type)(influence*)(limits:mXmYmZMXMYMZxx.xxx*)(use_transform_limit*)(owner_space*)
    regex = regular_expressions[fstring[0:2]]

    constraint_type = {'LL': 'LIMIT_LOCATION', 'LR': 'LIMIT_ROTATION', 'LS': 'LIMIT_SCALE'}
    constraint_space = {'L': 'LOCAL', 'W': 'WORLD', 'P': 'POSE'}

    re_object = re.match(regex, fstring)
    if not re_object:
        return
    else:
        cns_props = re_object.groups()

    cns_type = constraint_type[cns_props[0]]
    const = owner.constraints.new(cns_type)

    if cns_type == 'LIMIT_LOCATION':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.use_transform_limit = bool(cns_props[-2])
        const.owner_space = constraint_space[cns_props[-1]] if bool(cns_props[-1]) else "LOCAL"
        limits = cns_props[2]
        limit = cns_props[3]
        while 1:
            if not limits:
                break
            if limit[0:2] == 'mX':
                const.use_min_x = True
                const.min_x = float(limit[2:])
            if limit[0:2] == 'mY':
                const.use_min_y = True
                const.min_y = float(limit[2:])
            if limit[0:2] == 'mZ':
                const.use_min_z = True
                const.min_z = float(limit[2:])
            if limit[0:2] == 'MX':
                const.use_max_x = True
                const.max_x = float(limit[2:])
            if limit[0:2] == 'MY':
                const.use_max_y = True
                const.max_y = float(limit[2:])
            if limit[0:2] == 'MZ':
                const.use_max_z = True
                const.max_z = float(limit[2:])
            limits = limits[:-len(limit)]
            o = re.search('(([mM]{1}[XYZ]{1}-?[0-9]*\.?[0-9]+)+)*', limits)
            limits = o.groups()[0]
            limit = o.groups()[1]

    if cns_type == 'LIMIT_ROTATION':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.use_transform_limit = bool(cns_props[-2])
        const.owner_space = constraint_space[cns_props[-1]] if bool(cns_props[-1]) else "LOCAL"
        limits = cns_props[2]
        limit = cns_props[3]
        while 1:
            if not limits:
                break
            if limit[0:2] == 'mX':
                const.use_limit_x = True
                const.min_x = float(limit[2:])
            if limit[0:2] == 'mY':
                const.use_limit_y = True
                const.min_y = float(limit[2:])
            if limit[0:2] == 'mZ':
                const.use_limit_z = True
                const.min_z = float(limit[2:])
            if limit[0:2] == 'MX':
                const.use_limit_x = True
                const.max_x = float(limit[2:])
            if limit[0:2] == 'MY':
                const.use_limit_y = True
                const.max_y = float(limit[2:])
            if limit[0:2] == 'MZ':
                const.use_limit_z = True
                const.max_z = float(limit[2:])
            limits = limits[:-len(limit)]
            o = re.search('(([mM]{1}[XYZ]{1}-?[0-9]*\.?[0-9]+)+)*', limits)
            limits = o.groups()[0]
            limit = o.groups()[1]

    if cns_type == 'LIMIT_SCALE':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.use_transform_limit = bool(cns_props[-2])
        const.owner_space = constraint_space[cns_props[-1]] if bool(cns_props[-1]) else "LOCAL"
        limits = cns_props[2]
        limit = cns_props[3]
        while 1:
            if not limits:
                break
            if limit[0:2] == 'mX':
                const.use_min_x = True
                const.min_x = float(limit[2:])
            if limit[0:2] == 'mY':
                const.use_min_y = True
                const.min_y = float(limit[2:])
            if limit[0:2] == 'mZ':
                const.use_min_z = True
                const.min_z = float(limit[2:])
            if limit[0:2] == 'MX':
                const.use_max_x = True
                const.max_x = float(limit[2:])
            if limit[0:2] == 'MY':
                const.use_max_y = True
                const.max_y = float(limit[2:])
            if limit[0:2] == 'MZ':
                const.use_max_z = True
                const.max_z = float(limit[2:])
            limits = limits[:-len(limit)]
            o = re.search('(([mM]{1}[XYZ]{1}-?[0-9]*\.?[0-9]+)+)*', limits)
            limits = o.groups()[0]
            limit = o.groups()[1]


def make_track_constraint_from_string(owner, target, subtarget, fstring):

    # regex is (type)(influence*)(track_axis*)(space-space*)(head_tail*)
    regex = '^(TT|DT|ST)([0-9]*\.?[0-9]+)*(-*[XYZ])*([LWP]{2})*([0-9]*\.?[0-9]+)*$'

    constraint_type = {'DT': 'DAMPED_TRACK', 'TT': 'TRACK_TO', 'ST': 'STRETCH_TO'}
    constraint_space = {'L': 'LOCAL', 'W': 'WORLD', 'P': 'POSE'}
    track_axis = {'X': 'TRACK_X', '-X': 'TRACK_NEGATIVE_X', 'Y': 'TRACK_Y', '-Y': 'TRACK_NEGATIVE_Y',
                  'Z': 'TRACK_Z', '-Z': 'TRACK_NEGATIVE_Z'}

    re_object = re.match(regex, fstring)
    if not re_object:
        return
    else:
        cns_props = re_object.groups()

    cns_type = constraint_type[cns_props[0]]
    const = owner.constraints.new(cns_type)
    const.target = target
    const.subtarget = subtarget

    if cns_type == 'DAMPED_TRACK':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.track_axis = track_axis[cns_props[2]] if bool(cns_props[2]) else "TRACK_Y"
        const.head_tail = float(cns_props[4]) if bool(cns_props[4]) else 0.0

    if cns_type == 'TRACK_TO':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.track_axis = track_axis[cns_props[2]] if bool(cns_props[2]) else "TRACK_Y"
        const.target_space = constraint_space[cns_props[3][0]] if bool(cns_props[3]) else "LOCAL"
        const.owner_space = constraint_space[cns_props[3][1]] if bool(cns_props[3]) else "LOCAL"
        const.head_tail = float(cns_props[4]) if bool(cns_props[4]) else 0.0

    if cns_type == 'STRETCH_TO':
        const.influence = float(cns_props[1]) if bool(cns_props[1]) else 1.0
        const.head_tail = float(cns_props[4]) if bool(cns_props[4]) else 0.0


def make_relation_constraint_from_string(owner, target, subtarget, fstring):

    # regex is (type)
    regex = '^(PA)$'

    constraint_type = {'PA': 'PARENTING'}

    re_object = re.match(regex, fstring)
    if not re_object:
        return
    else:
        cns_props = re_object.groups()

    cns_type = constraint_type[cns_props[0]]

    if cns_type == 'PARENTING':
        target.data.edit_bones[owner.name].parent = target.data.edit_bones[subtarget]
