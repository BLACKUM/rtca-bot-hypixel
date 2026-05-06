import io
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

ROOM_PX = 40
GAP_PX = 6
CELL = ROOM_PX + GAP_PX
PADDING = 8

_TYPE_COLORS = {
    "ENTRANCE":  (0x20, 0xC0, 0x20),
    "NORMAL":    (0x79, 0x46, 0x00),
    "PUZZLE":    (0x9B, 0x39, 0xC8),
    "BLOOD":     (0xCC, 0x20, 0x20),
    "TRAP":      (0xF5, 0xA7, 0x42),
    "FAIRY":     (0xDD, 0x44, 0xDD),
    "CHAMPION":  (0xFF, 0xD4, 0x00),
    "RARE":      (0xFF, 0xFF, 0xFF),
    "UNKNOWN":   (0x55, 0x55, 0x55),
    "MIMIC":     (0xFF, 0x66, 0x00),
}

_DOOR_COLORS = {
    "NORMAL": (0x79, 0x46, 0x00),
    "WITHER": (0x11, 0x11, 0x11),
    "BLOOD":  (0xCC, 0x20, 0x20),
}

_BG = (0, 0, 0, 0)
_NAME_COLOR = (255, 255, 255, 255)


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


_FONT = _load_font(10)


def _draw_name(draw: ImageDraw.ImageDraw, name: str, places: list) -> None:
    if not name or not places:
        return
    ps = [(int(p[0]), int(p[1])) for p in places]
    ps_set = set(ps)

    if len(ps) == 3:
        anchor = max(ps, key=lambda p: ((p[0]+1, p[1]) in ps_set) + ((p[0]-1, p[1]) in ps_set)
                                       + ((p[0], p[1]+1) in ps_set) + ((p[0], p[1]-1) in ps_set))
        cx = PADDING + anchor[0] * CELL + ROOM_PX / 2
        cy = PADDING + anchor[1] * CELL + ROOM_PX / 2
    else:
        cols = [c for c, _ in ps]
        rows = [r for _, r in ps]
        cx = PADDING + ((min(cols) + max(cols)) / 2) * CELL + ROOM_PX / 2
        cy = PADDING + ((min(rows) + max(rows)) / 2) * CELL + ROOM_PX / 2

    words = name.split()
    lines = words if len(name) > 6 and len(words) > 1 else [name]

    bbox = draw.textbbox((0, 0), "Mg", font=_FONT)
    line_h = bbox[3] - bbox[1] + 1
    total_h = line_h * len(lines)
    y = cy - total_h / 2

    for line in lines:
        lb = draw.textbbox((0, 0), line, font=_FONT)
        lw = lb[2] - lb[0]
        draw.text((cx - lw / 2, y), line, fill=_NAME_COLOR, font=_FONT)
        y += line_h


def _apply_state(color: tuple, state: str) -> tuple:
    r, g, b = color
    if state in ("UNDISCOVERED", "UNOPENED"):
        return (int(r * 0.5), int(g * 0.5), int(b * 0.5))
    return color


def render_map(map_data: dict) -> Optional[bytes]:
    rooms = map_data.get("rooms", [])
    doors = map_data.get("doors", [])
    if not rooms:
        return None

    map_size = map_data.get("map_size", {"x": 6, "z": 6})
    cols = map_size.get("x", 6)
    rows = map_size.get("z", 6)

    width  = PADDING * 2 + cols * CELL - GAP_PX
    height = PADDING * 2 + rows * CELL - GAP_PX

    img  = Image.new("RGBA", (width, height), _BG)
    draw = ImageDraw.Draw(img)

    cell_color: dict[tuple, tuple] = {}

    for room in rooms:
        rtype  = room.get("type", "UNKNOWN")
        rstate = room.get("state", "UNDISCOVERED")
        mimic  = room.get("mimic", False)
        base   = _TYPE_COLORS["MIMIC"] if mimic else _TYPE_COLORS.get(rtype, (0x55, 0x55, 0x55))
        color  = _apply_state(base, rstate)
        places = room.get("places", [])

        for place in places:
            col, row = int(place[0]), int(place[1])
            cell_color[(col, row)] = color
            x1 = PADDING + col * CELL
            y1 = PADDING + row * CELL
            draw.rectangle([x1, y1, x1 + ROOM_PX - 1, y1 + ROOM_PX - 1], fill=color)

        place_set = {(int(p[0]), int(p[1])) for p in places}
        for (col, row) in place_set:
            if (col + 1, row) in place_set:
                x1 = PADDING + col * CELL + ROOM_PX
                y1 = PADDING + row * CELL
                draw.rectangle([x1, y1, x1 + GAP_PX - 1, y1 + ROOM_PX - 1], fill=color)
            if (col, row + 1) in place_set:
                x1 = PADDING + col * CELL
                y1 = PADDING + row * CELL + ROOM_PX
                draw.rectangle([x1, y1, x1 + ROOM_PX - 1, y1 + GAP_PX - 1], fill=color)
            if (col + 1, row) in place_set and (col, row + 1) in place_set and (col + 1, row + 1) in place_set:
                x1 = PADDING + col * CELL + ROOM_PX
                y1 = PADDING + row * CELL + ROOM_PX
                draw.rectangle([x1, y1, x1 + GAP_PX - 1, y1 + GAP_PX - 1], fill=color)

    for door in doors:
        adj_a = door.get("adj_a")
        adj_b = door.get("adj_b")
        if not adj_a or not adj_b:
            continue

        dtype  = door.get("type", "NORMAL")
        locked = door.get("locked", False)
        if locked and dtype == "WITHER":
            dc = _DOOR_COLORS["WITHER"]
        elif locked and dtype == "BLOOD":
            dc = _DOOR_COLORS["BLOOD"]
        else:
            dc = _DOOR_COLORS.get(dtype, (190, 190, 190))

        ax, az = int(adj_a[0]), int(adj_a[1])
        bx, bz = int(adj_b[0]), int(adj_b[1])
        door_w = 12

        if az == bz and abs(ax - bx) == 1:
            left_col = min(ax, bx)
            gx = PADDING + left_col * CELL + ROOM_PX
            gy = PADDING + az * CELL + (ROOM_PX - door_w) // 2
            draw.rectangle([gx, gy, gx + GAP_PX - 1, gy + door_w - 1], fill=dc)
        elif ax == bx and abs(az - bz) == 1:
            top_row = min(az, bz)
            gx = PADDING + ax * CELL + (ROOM_PX - door_w) // 2
            gy = PADDING + top_row * CELL + ROOM_PX
            draw.rectangle([gx, gy, gx + door_w - 1, gy + GAP_PX - 1], fill=dc)

    for room in rooms:
        _draw_name(draw, room.get("name", ""), room.get("places", []))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
