#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.conf import settings

from sounds.models import Sound
from utils.pagination import build_paginator_template_context, paginate

# Sort options for editable sound grids (collection/pack edit). Sorting happens here,
# server-side, over lightweight metadata; the "featured" option is only exposed when
# the grid tracks featured sounds (max_featured is set).
EDITABLE_GRID_SORT_OPTIONS = {
    "featured": "Featured first",
    "created_desc": "Date added (newest first)",
    "created_asc": "Date added (oldest first)",
    "name": "Name (A to Z)",
}


def parse_id_list(value):
    """Ordered, de-duplicated int ids from a comma-separated string."""
    seen = set()
    ids = []
    for part in value.split(","):
        if part.isdigit() and int(part) not in seen:
            seen.add(int(part))
            ids.append(int(part))
    return ids


def editable_sound_grid_context(
    request, saved_sounds_meta, addable_sounds_qs, object_name, max_featured=None, saved_featured_ids=None
):
    """Template context for molecules/editable_sound_grid_content.html with the pending delta baked in.

    The client keeps no copy of the saved sound list: on every grid refresh it only
    sends the pending delta (``added_sounds``/``removed_sounds``/``featured_sounds``,
    mirrored from the form's hidden inputs) plus ``q``/``s``/``page``, and gets back
    the grid rendered with that state applied (added sounds included, removed ones
    marked for removal, featured buttons active). See editableSoundGrid.js.

    Args:
        saved_sounds_meta: [{"id", "name", "username", "date_added"}] of the saved members.
        addable_sounds_qs: Sound queryset that pending-added ids must belong to
            (e.g. only the pack owner's sounds); others are silently dropped.
        object_name: "collection" or "pack", used in grid texts.
        max_featured: enables the featured action and sort when set.
        saved_featured_ids: saved featured order, used until the client sends a pending one.
    """
    params = request.POST if request.method == "POST" else request.GET
    added_ids = parse_id_list(params.get("added_sounds", ""))
    removed_ids = set(parse_id_list(params.get("removed_sounds", "")))
    if "featured_sounds" in params:
        featured_ids = parse_id_list(params["featured_sounds"])
    else:
        featured_ids = list(saved_featured_ids or [])

    sounds_meta = list(saved_sounds_meta)
    saved_ids = {m["id"] for m in sounds_meta}
    pending_added = [sid for sid in added_ids if sid not in saved_ids]
    if pending_added:
        added_meta = {
            row["id"]: row
            for row in addable_sounds_qs.filter(id__in=pending_added).values(
                "id", "original_filename", "user__username", "created"
            )
        }
        pending_added = [sid for sid in pending_added if sid in added_meta]
        sounds_meta += [
            {
                "id": sid,
                "name": added_meta[sid]["original_filename"],
                "username": added_meta[sid]["user__username"],
                "date_added": added_meta[sid]["created"],
            }
            for sid in pending_added
        ]
    all_ids = saved_ids | set(pending_added)

    sort_options = dict(EDITABLE_GRID_SORT_OPTIONS)
    if max_featured is None:
        del sort_options["featured"]
    sort_key = params.get("s") or ""
    if sort_key not in sort_options:
        sort_key = next(iter(sort_options))

    search = params.get("q", "").strip()
    if search:
        q = search.lower()
        sounds_meta = [m for m in sounds_meta if q in m["name"].lower() or q in m["username"].lower()]

    if sort_key == "featured":
        featured_index = {sid: i for i, sid in enumerate(featured_ids)}
        sounds_meta.sort(key=lambda m: (featured_index.get(m["id"], len(featured_index)), m["date_added"]))
    elif sort_key == "name":
        sounds_meta.sort(key=lambda m: m["name"].lower())
    else:
        sounds_meta.sort(key=lambda m: m["date_added"], reverse=sort_key == "created_desc")

    pagination = paginate(request, [m["id"] for m in sounds_meta], settings.BOOKMARKS_PER_PAGE)
    page_ids = list(pagination["page"])
    sounds_by_id = {s.id: s for s in Sound.objects.bulk_query_id_public(page_ids)} if page_ids else {}
    sounds = [sounds_by_id[sid] for sid in page_ids if sid in sounds_by_id]

    featured_set = set(featured_ids)
    featured_count = len(featured_set & all_ids - removed_ids)
    at_limit = max_featured is not None and featured_count >= max_featured
    for sound in sounds:
        sound.is_featured = sound.id in featured_set
        sound.marked_removed = sound.id in removed_ids
        sound.featured_disabled = sound.marked_removed or (not sound.is_featured and at_limit)

    tvars = {
        "sounds": sounds,
        "grid_object_name": object_name,
        "sort_options": sort_options,
        "current_sort": sort_key,
        "current_search": search,
        "show_featured": max_featured is not None,
        "max_featured": max_featured,
        "total_count": len(all_ids),
        "present_count": len(all_ids - removed_ids),
        "featured_count": featured_count,
        "grid_is_empty": not all_ids,
    }
    tvars.update(build_paginator_template_context(pagination["page"], base_path=request.path, base_query=request.GET))
    return tvars
