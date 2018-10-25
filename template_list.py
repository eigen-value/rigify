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

import os

from . import utils


def get_templates(base_path, path):
    """ Searches for template types, and returns a list.
    """
    templates = {}

    files = os.listdir(os.path.join(base_path, path))
    files.sort()

    for f in files:
        if f.endswith(".py"):
            f = f[:-3]
            module_name = os.path.join(path, f).replace(os.sep, ".")
            template = utils.get_resource(module_name, base_path=base_path)
            templates[f] = template
    return templates


def fill_ui_template_list(obj):
    """Fill rig's UI template list
    """
    armature = obj.data
    for i in range(0, len(armature.rigify_templates)):
        armature.rigify_templates.remove(0)

    for t in templates:
        a = armature.rigify_templates.add()
        a.name = t


# Public variables
MODULE_DIR = os.path.dirname(os.path.dirname(__file__))

templates = get_templates(MODULE_DIR, os.path.join(os.path.basename(os.path.dirname(__file__)), utils.TEMPLATE_DIR, ''))


def get_external_templates(feature_sets_path):
    # Clear and get internal templates
    templates.clear()
    templates.update(get_templates(MODULE_DIR, os.path.join(os.path.basename(os.path.dirname(__file__)), utils.TEMPLATE_DIR, '')))

    # Get external templates
    for feature_set in os.listdir(feature_sets_path):
        if feature_set:
            external_templates_list = get_templates(feature_sets_path, os.path.join(feature_set, utils.TEMPLATE_DIR))
            templates.update(external_templates_list)
