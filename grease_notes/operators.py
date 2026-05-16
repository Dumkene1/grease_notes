# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty

from .properties import NOTE_TYPES
from . import storage, thumbnail


def _active_gp_layer_name(obj):
    if not obj or obj.type not in {"GREASEPENCIL", "GPENCIL"}:
        return ""
    data = getattr(obj, "data", None)
    layers = getattr(data, "layers", None)
    if not layers:
        return ""

    active = getattr(layers, "active", None)
    if active:
        return getattr(active, "name", "")

    active_index = getattr(layers, "active_index", None)
    if active_index is not None:
        try:
            return layers[active_index].name
        except Exception:
            return ""
    return ""


def _default_title(note_type, context):
    frame = context.scene.frame_current
    obj = context.object
    if note_type == "OBJECT" and obj:
        return f"Object Note - {obj.name}"
    if note_type == "FRAME":
        return f"Frame {frame} Note"
    if note_type == "GP_FRAME":
        return f"GP Frame {frame} Note"
    if note_type == "SCENE":
        return f"Scene Note - {context.scene.name}"
    return "New Note"


class GN_OT_add_note(bpy.types.Operator):
    bl_idname = "grease_notes.add_note"
    bl_label = "Add Grease Note"
    bl_description = "Create a new Grease Note from the current context"
    bl_options = {"REGISTER", "UNDO"}

    note_type: EnumProperty(name="Note Type", items=NOTE_TYPES, default="GENERAL")

    def execute(self, context):
        scene = context.scene
        note = scene.grease_notes.add()
        note.uid = storage.new_uid()
        note.title = _default_title(self.note_type, context)
        note.note_type = self.note_type
        note.scene_name = scene.name
        note.created_at = storage.now_string()
        note.updated_at = note.created_at

        obj = context.object
        if self.note_type in {"OBJECT", "GP_FRAME", "MATERIAL", "CAMERA"} and obj:
            note.object_name = obj.name

        if self.note_type in {"FRAME", "GP_FRAME", "CAMERA"}:
            note.has_frame_link = True
            note.frame_number = scene.frame_current

        if self.note_type == "GP_FRAME":
            note.gp_layer_name = _active_gp_layer_name(obj)
            if obj and obj.type not in {"GREASEPENCIL", "GPENCIL"}:
                self.report({"WARNING"}, "Created GP Frame note, but active object is not Grease Pencil.")

        scene.grease_notes_settings.active_note_index = len(scene.grease_notes) - 1
        return {"FINISHED"}


class GN_OT_delete_note(bpy.types.Operator):
    bl_idname = "grease_notes.delete_note"
    bl_label = "Delete Grease Note"
    bl_description = "Delete the selected note and its thumbnail"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        index = self.index if self.index >= 0 else scene.grease_notes_settings.active_note_index
        if index < 0 or index >= len(scene.grease_notes):
            return {"CANCELLED"}

        note = scene.grease_notes[index]
        storage.delete_thumbnail_image(note)
        scene.grease_notes.remove(index)
        storage.clamp_active_index(scene)
        return {"FINISHED"}


class GN_OT_capture_thumbnail(bpy.types.Operator):
    bl_idname = "grease_notes.capture_thumbnail"
    bl_label = "Capture Viewport Thumbnail"
    bl_description = "Capture a viewport thumbnail for the selected Grease Note"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(default=-1)
    use_note_frame: BoolProperty(
        name="Use Note Frame",
        description="If the note is linked to a frame, temporarily capture that frame instead of the current timeline frame",
        default=True,
    )


    @classmethod
    def description(cls, context, properties):
        if properties.use_note_frame:
            return "Capture the selected note's linked frame. If Blender is on another frame, Grease Notes temporarily jumps to the note frame, captures it, then returns."
        return "Capture the active 3D Viewport exactly as it is now, using Blender's current timeline frame."

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def execute(self, context):
        scene = context.scene
        index = self.index if self.index >= 0 else scene.grease_notes_settings.active_note_index
        if index < 0 or index >= len(scene.grease_notes):
            self.report({"WARNING"}, "No note selected.")
            return {"CANCELLED"}

        note = scene.grease_notes[index]
        original_frame = scene.frame_current
        captured_frame = original_frame

        try:
            if self.use_note_frame and note.has_frame_link:
                captured_frame = note.frame_number
                if scene.frame_current != captured_frame:
                    scene.frame_set(captured_frame)
                    context.view_layer.update()

            ok, message = thumbnail.capture_active_viewport(context, note)
            if ok:
                note.thumbnail_frame_number = captured_frame
                note.updated_at = storage.now_string()
                message = f"Thumbnail captured from frame {captured_frame}."
            self.report({"INFO" if ok else "WARNING"}, message)
            return {"FINISHED" if ok else "CANCELLED"}
        finally:
            # If we jumped to the note frame only for thumbnail capture, return the
            # animator to the frame they were actually working on.
            if self.use_note_frame and note.has_frame_link and scene.frame_current != original_frame:
                scene.frame_set(original_frame)
                context.view_layer.update()


class GN_OT_delete_thumbnail(bpy.types.Operator):
    bl_idname = "grease_notes.delete_thumbnail"
    bl_label = "Delete Thumbnail"
    bl_description = "Remove the selected note's thumbnail only"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        index = self.index if self.index >= 0 else scene.grease_notes_settings.active_note_index
        if index < 0 or index >= len(scene.grease_notes):
            return {"CANCELLED"}
        note = scene.grease_notes[index]
        removed = storage.delete_thumbnail_image(note)
        note.thumbnail_frame_number = -1
        note.updated_at = storage.now_string()
        self.report({"INFO"}, "Thumbnail deleted." if removed else "No thumbnail to delete.")
        return {"FINISHED"}


class GN_OT_jump_to_frame(bpy.types.Operator):
    bl_idname = "grease_notes.jump_to_frame"
    bl_label = "Jump to Note Frame"
    bl_description = "Move the current scene to this note's linked frame"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        index = self.index if self.index >= 0 else scene.grease_notes_settings.active_note_index
        if index < 0 or index >= len(scene.grease_notes):
            return {"CANCELLED"}
        note = scene.grease_notes[index]
        if not note.has_frame_link:
            self.report({"WARNING"}, "This note is not linked to a frame.")
            return {"CANCELLED"}
        scene.frame_set(note.frame_number)
        return {"FINISHED"}


class GN_OT_select_linked_object(bpy.types.Operator):
    bl_idname = "grease_notes.select_linked_object"
    bl_label = "Select Linked Object"
    bl_description = "Select the object linked to this note"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        index = self.index if self.index >= 0 else scene.grease_notes_settings.active_note_index
        if index < 0 or index >= len(scene.grease_notes):
            return {"CANCELLED"}
        note = scene.grease_notes[index]
        if not note.object_name:
            self.report({"WARNING"}, "This note has no linked object.")
            return {"CANCELLED"}

        obj = bpy.data.objects.get(note.object_name)
        if not obj:
            self.report({"WARNING"}, f"Object not found: {note.object_name}")
            return {"CANCELLED"}

        for selected in context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {"FINISHED"}


class GN_OT_refresh_note_context(bpy.types.Operator):
    bl_idname = "grease_notes.refresh_note_context"
    bl_label = "Refresh Link From Context"
    bl_description = "Update the selected note's frame/object/layer links from the current Blender context"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        note = storage.get_active_note(context.scene)
        if not note:
            return {"CANCELLED"}

        obj = context.object
        note.scene_name = context.scene.name
        note.frame_number = context.scene.frame_current
        note.has_frame_link = True
        note.object_name = obj.name if obj else ""
        note.gp_layer_name = _active_gp_layer_name(obj)
        note.updated_at = storage.now_string()
        return {"FINISHED"}


classes = (
    GN_OT_add_note,
    GN_OT_delete_note,
    GN_OT_capture_thumbnail,
    GN_OT_delete_thumbnail,
    GN_OT_jump_to_frame,
    GN_OT_select_linked_object,
    GN_OT_refresh_note_context,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
