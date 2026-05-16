# SPDX-License-Identifier: GPL-3.0-or-later
"""Viewport thumbnail helpers.

v0.1 intentionally captures the active viewport as a memo image. It does not
try to isolate Grease Pencil objects, layers, or final render output.
"""

import os
import tempfile

import bpy

from . import storage


def _safe_image_name(note):
    base = note.title.strip().replace(" ", "_") or "Note"
    base = "".join(ch for ch in base if ch.isalnum() or ch in "_-" )[:40]
    return f"GN_thumb_{note.uid[:8]}_{base}"


def capture_active_viewport(context, note):
    """Capture the active 3D Viewport as a packed Blender image datablock.

    Returns (success, message).
    """
    area = context.area
    if not area or area.type != "VIEW_3D":
        return False, "Capture must be run from the 3D Viewport."

    scene = context.scene
    old_filepath = scene.render.filepath

    fd, filepath = tempfile.mkstemp(prefix="grease_notes_thumb_", suffix=".png")
    os.close(fd)

    try:
        scene.render.filepath = filepath

        # OpenGL viewport render: captures the visible viewport context.
        bpy.ops.render.opengl(write_still=True, view_context=True)

        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return False, "Viewport capture did not create an image file."

        # Replace old thumbnail datablock, if any.
        storage.delete_thumbnail_image(note)

        image = bpy.data.images.load(filepath, check_existing=False)
        image.name = _safe_image_name(note)
        try:
            image.pack()
        except Exception:
            # The image still exists as a datablock. Packing can fail in some
            # Blender states, so do not make the whole operator fail here.
            pass

        note.thumbnail_image_name = image.name
        note.updated_at = storage.now_string()
        return True, "Thumbnail captured."

    except Exception as exc:  # Blender ops may fail depending on context.
        return False, f"Viewport capture failed: {exc}"

    finally:
        scene.render.filepath = old_filepath
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass
