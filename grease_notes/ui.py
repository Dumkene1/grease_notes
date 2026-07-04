# SPDX-License-Identifier: GPL-3.0-or-later
import bpy

from . import storage


def _icon_for_note_type(note_type):
    return {
        "GENERAL": "TEXT",
        "SCENE": "SCENE_DATA",
        "OBJECT": "OBJECT_DATA",
        "FRAME": "TIME",
        "GP_FRAME": "OUTLINER_OB_GREASEPENCIL",
        "TASK": "CHECKMARK",
        "MATERIAL": "MATERIAL",
        "CAMERA": "CAMERA_DATA",
    }.get(note_type, "TEXT")


def _draw_thumbnail_preview(layout, note, scale=10.0):
    """Draw a visible thumbnail preview for the selected note when available."""
    if not note.thumbnail_image_name:
        layout.label(text="No thumbnail captured", icon="BLANK1")
        return

    image = bpy.data.images.get(note.thumbnail_image_name)
    if not image:
        layout.label(text="Thumbnail image missing", icon="ERROR")
        return

    try:
        icon_value = layout.icon(image)
        layout.template_icon(icon_value=icon_value, scale=scale)
    except Exception:
        # Fallback: at least show that an image is attached if Blender refuses
        # to draw a preview icon in this specific UI context.
        layout.label(text=image.name, icon="IMAGE_DATA")

    if note.thumbnail_frame_number >= 0:
        layout.label(text=f"Thumbnail frame: {note.thumbnail_frame_number}", icon="TIME")
    elif note.has_frame_link:
        layout.label(text=f"Linked note frame: {note.frame_number}", icon="TIME")


class GN_UL_notes(bpy.types.UIList):
    bl_idname = "GN_UL_notes"

    def filter_items(self, context, data, propname):
        notes = getattr(data, propname)
        settings = context.scene.grease_notes_settings
        flags = []
        for note in notes:
            flags.append(self.bitflag_filter_item if storage.note_matches_filters(note, settings) else 0)
        return flags, []

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        note = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text=note.title or "Untitled", icon=_icon_for_note_type(note.note_type))
            if note.has_frame_link:
                row.label(text=f"F{note.frame_number}")
            if note.thumbnail_image_name:
                row.label(text="", icon="IMAGE_DATA")
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon=_icon_for_note_type(note.note_type))


class GN_PT_main_panel(bpy.types.Panel):
    bl_label = "Grease Notes"
    bl_idname = "GN_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Grease Notes"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.grease_notes_settings
        notes = scene.grease_notes

        col = layout.column(align=True)
        col.label(text="Add Note", icon="ADD")

        grid = col.grid_flow(columns=2, even_columns=True, even_rows=True, align=True)
        op = grid.operator("grease_notes.add_note", text="General")
        op.note_type = "GENERAL"
        op = grid.operator("grease_notes.add_note", text="Scene")
        op.note_type = "SCENE"
        op = grid.operator("grease_notes.add_note", text="Object")
        op.note_type = "OBJECT"
        op = grid.operator("grease_notes.add_note", text="Frame")
        op.note_type = "FRAME"
        op = grid.operator("grease_notes.add_note", text="GP Frame")
        op.note_type = "GP_FRAME"
        op = grid.operator("grease_notes.add_note", text="Task")
        op.note_type = "TASK"

        layout.separator()

        filter_box = layout.box()
        filter_box.label(text="Search / Filter", icon="VIEWZOOM")
        filter_box.prop(settings, "search_text", text="")
        row = filter_box.row(align=True)
        row.prop(settings, "filter_type", text="")
        row.prop(settings, "filter_status", text="")

        layout.label(text="Saved Notes & Frame Thumbnails", icon="PREVIEW_RANGE")
        notes_box = layout.box()
        notes_box.template_list(
            "GN_UL_notes",
            "",
            scene,
            "grease_notes",
            settings,
            "active_note_index",
            rows=7,
        )

        if not notes:
            layout.label(text="No notes yet.", icon="INFO")
            return

        index = storage.clamp_active_index(scene)
        if index < 0:
            return

        note = notes[index]

        layout.separator()
        details = layout.box()
        header = details.row(align=True)
        header.prop(settings, "show_details", text="", icon="TRIA_DOWN" if settings.show_details else "TRIA_RIGHT", emboss=False)
        header.label(text="Selected Note Details", icon=_icon_for_note_type(note.note_type))

        if not settings.show_details:
            return

        details.prop(note, "title", text="Title")
        row = details.row(align=True)
        row.prop(note, "note_type", text="Type")
        row.prop(note, "status", text="Status")

        details.prop(note, "tags", text="Tags")

        body_box = details.box()
        body_box.label(text="Body", icon="TEXT")
        body_col = body_box.column(align=True)
        # Blender StringProperty fields are still single-property text inputs,
        # but scale_y gives the body field more visual room than tags/status.
        body_col.scale_y = 2.3
        body_col.prop(note, "body", text="")

        link_box = details.box()
        link_box.label(text="Links", icon="LINKED")
        link_box.prop(note, "scene_name", text="Scene")
        link_box.prop(note, "object_name", text="Object")
        link_box.prop(note, "has_frame_link", text="Frame Link")
        if note.has_frame_link:
            link_box.prop(note, "frame_number", text="Frame")
        link_box.prop(note, "gp_layer_name", text="GP Layer")
        link_box.operator("grease_notes.refresh_note_context", text="Refresh From Current Context", icon="FILE_REFRESH")

        action_box = details.box()
        action_box.label(text="Actions", icon="TOOL_SETTINGS")
        row = action_box.row(align=True)
        row.enabled = note.has_frame_link
        row.operator("grease_notes.jump_to_frame", text="Jump to Frame", icon="TIME").index = index
        row = action_box.row(align=True)
        row.enabled = bool(note.object_name)
        row.operator("grease_notes.select_linked_object", text="Select Object", icon="RESTRICT_SELECT_OFF").index = index

        thumb_box = details.box()
        thumb_box.label(text="Thumbnail Preview", icon="IMAGE_DATA")
        _draw_thumbnail_preview(thumb_box, note, scale=10.0)

        if note.has_frame_link:
            thumb_box.label(text=f"Note is linked to frame: {note.frame_number}", icon="TIME")
        else:
            thumb_box.label(text="Note has no linked frame; capture uses current timeline frame.", icon="INFO")

        row = thumb_box.row(align=True)
        op = row.operator("grease_notes.capture_thumbnail", text="Capture Note Frame", icon="RENDER_STILL")
        op.index = index
        op.use_note_frame = True
        op = row.operator("grease_notes.capture_thumbnail", text="Capture Current", icon="RENDER_ANIMATION")
        op.index = index
        op.use_note_frame = False

        row = thumb_box.row(align=True)
        view_row = row.operator("grease_notes.view_thumbnail", text="View in Image Editor", icon="IMAGE")
        view_row.index = index
        row.enabled = bool(note.thumbnail_image_name)

        row = thumb_box.row(align=True)
        row.operator("grease_notes.delete_thumbnail", text="Delete Thumbnail", icon="TRASH").index = index

        meta = details.column(align=True)
        if note.created_at:
            meta.label(text=f"Created: {note.created_at}")
        if note.updated_at:
            meta.label(text=f"Updated: {note.updated_at}")

        layout.separator()
        danger = layout.row(align=True)
        danger.operator("grease_notes.delete_note", text="Delete Selected Note", icon="TRASH").index = index


classes = (
    GN_UL_notes,
    GN_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
