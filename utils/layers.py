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


def get_layers(layers):
    """ Does it's best to exctract a set of layers from any data thrown at it.
    """
    if type(layers) == int:
        return [x == layers for x in range(0, 32)]
    elif type(layers) == str:
        s = layers.split(",")
        l = []
        for i in s:
            try:
                l += [int(float(i))]
            except ValueError:
                pass
        return [x in l for x in range(0, 32)]
    elif type(layers) == tuple or type(layers) == list:
        return [x in layers for x in range(0, 32)]
    else:
        try:
            list(layers)
        except TypeError:
            pass
        else:
            return [x in layers for x in range(0, 32)]
