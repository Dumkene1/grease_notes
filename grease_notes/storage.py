# SPDX-License-Identifier: GPL-3.0-or-later
import uuid
from datetime import datetime


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_uid():
    return uuid.uuid4().hex


def clamp_active_index(scene):
    notes = scene.grease_notes
    settings = scene.grease_notes_settings
    if not notes:
        settings.active_note_index = -1
        return -1
    if settings.active_note_index < 0:
        settings.active_note_index = 0
    if settings.active_note_index >= len(notes):
        settings.active_note_index = len(notes) - 1
    return settings.active_note_index


def get_active_note(scene):
    index = clamp_active_index(scene)
    if index < 0:
        return None
    return scene.grease_notes[index]


def note_matches_filters(note, settings):
    if settings.filter_type != "ALL" and note.note_type != settings.filter_type:
        return False
    if settings.filter_status != "ALL" and note.status != settings.filter_status:
        return False

    query = settings.search_text.strip().lower()
    if query:
        haystack = " ".join([
            note.title,
            note.body,
            note.tags,
            note.scene_name,
            note.object_name,
            note.gp_layer_name,
            note.note_type,
            note.status,
        ]).lower()
        return query in haystack

    return True


def delete_thumbnail_image(note):
    """Remove the thumbnail image datablock if it exists and is not used elsewhere."""
    import bpy

    image_name = note.thumbnail_image_name
    if not image_name:
        return False

    image = bpy.data.images.get(image_name)
    note.thumbnail_image_name = ""

    if image:
        bpy.data.images.remove(image)
        return True
    return False
