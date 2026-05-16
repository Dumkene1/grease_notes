# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
)


NOTE_TYPES = [
    ("GENERAL", "General", "General Blender note"),
    ("SCENE", "Scene", "Note linked to the current scene"),
    ("OBJECT", "Object", "Note linked to the selected object"),
    ("FRAME", "Frame", "Note linked to the current timeline frame"),
    ("GP_FRAME", "GP Frame", "Note linked to a Grease Pencil object/layer/frame"),
    ("TASK", "Task", "Todo, fix, cleanup, or production task"),
    ("MATERIAL", "Material", "Material/shader note"),
    ("CAMERA", "Camera / Shot", "Camera or shot planning note"),
]

STATUSES = [
    ("NONE", "None", "No status"),
    ("TODO", "Todo", "Needs work"),
    ("DOING", "Doing", "In progress"),
    ("REVIEW", "Review", "Needs review/checking"),
    ("DONE", "Done", "Completed"),
    ("REFERENCE", "Reference", "Reference note"),
    ("PROBLEM", "Problem", "Something needs fixing"),
]


class GN_Note(bpy.types.PropertyGroup):
    uid: StringProperty(name="ID", default="")
    title: StringProperty(name="Title", default="Untitled Note")
    body: StringProperty(name="Note", default="")
    note_type: EnumProperty(name="Type", items=NOTE_TYPES, default="GENERAL")
    status: EnumProperty(name="Status", items=STATUSES, default="NONE")
    tags: StringProperty(name="Tags", default="")

    scene_name: StringProperty(name="Scene", default="")
    object_name: StringProperty(name="Object", default="")
    gp_layer_name: StringProperty(name="GP Layer", default="")

    has_frame_link: BoolProperty(name="Linked to Frame", default=False)
    frame_number: IntProperty(name="Frame", default=1)

    thumbnail_image_name: StringProperty(name="Thumbnail Image", default="")
    thumbnail_frame_number: IntProperty(name="Thumbnail Frame", default=-1)
    created_at: StringProperty(name="Created", default="")
    updated_at: StringProperty(name="Updated", default="")


class GN_Settings(bpy.types.PropertyGroup):
    active_note_index: IntProperty(name="Active Note", default=-1)
    search_text: StringProperty(name="Search", default="")
    filter_type: EnumProperty(
        name="Type",
        items=[("ALL", "All Types", "Show all note types")] + NOTE_TYPES,
        default="ALL",
    )
    filter_status: EnumProperty(
        name="Status",
        items=[("ALL", "All Statuses", "Show all statuses")] + STATUSES,
        default="ALL",
    )
    show_details: BoolProperty(name="Show Details", default=True)


classes = (
    GN_Note,
    GN_Settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.grease_notes = CollectionProperty(type=GN_Note)
    bpy.types.Scene.grease_notes_settings = PointerProperty(type=GN_Settings)


def unregister():
    if hasattr(bpy.types.Scene, "grease_notes_settings"):
        del bpy.types.Scene.grease_notes_settings
    if hasattr(bpy.types.Scene, "grease_notes"):
        del bpy.types.Scene.grease_notes

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
