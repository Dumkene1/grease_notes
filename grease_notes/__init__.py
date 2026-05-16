# SPDX-License-Identifier: GPL-3.0-or-later
"""Grease Notes - Blender notes with optional viewport thumbnails."""

bl_info = {
    "name": "Grease Notes",
    "author": "Dumkene Izuora",
    "version": (0, 1, 3),
    "blender": (5, 1, 0),
    "location": "3D Viewport > Sidebar > Grease Notes",
    "description": "Create notes linked to scenes, objects, frames, and Grease Pencil animation.",
    "category": "3D View",
}

import importlib

from . import properties, operators, ui

# Helpful while developing/reloading the extension inside Blender.
for _module in (properties, operators, ui):
    importlib.reload(_module)

_modules = (properties, operators, ui)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()
