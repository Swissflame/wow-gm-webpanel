from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import mpyq
from PIL import Image


CLIENT_MPQ_ORDER = [
    "Data/deDE/locale-deDE.MPQ",
    "Data/deDE/expansion-locale-deDE.MPQ",
    "Data/deDE/lichking-locale-deDE.MPQ",
    "Data/deDE/patch-deDE.MPQ",
    "Data/deDE/patch-deDE-2.MPQ",
    "Data/deDE/patch-deDE-3.MPQ",
]

ITEM_DISPLAY_DBC_ORDER = [
    "Data/deDE/locale-deDE.MPQ",
    "Data/deDE/patch-deDE.MPQ",
    "Data/deDE/patch-deDE-2.MPQ",
    "Data/deDE/patch-deDE-3.MPQ",
]


def mpq_files(client_dir: Path, order: list[str]) -> list[Path]:
    return [client_dir / rel for rel in order if (client_dir / rel).exists()]


def decode_name(raw: bytes) -> str:
    return raw.decode("utf-8", "ignore").replace("/", "\\")


def icon_slug(icon_name: str) -> str:
    return Path(icon_name.replace("\\", "/")).stem.lower()


def extract_icons(client_dir: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    skipped = 0
    seen: set[str] = set()
    for mpq_path in mpq_files(client_dir, CLIENT_MPQ_ORDER):
        archive = mpyq.MPQArchive(str(mpq_path))
        icon_files = [
            name for name in archive.files
            if name.lower().startswith(b"interface\\icons\\") and name.lower().endswith(b".blp")
        ]
        for raw_name in icon_files:
            icon_name = decode_name(raw_name)
            slug = icon_slug(icon_name)
            if not slug:
                continue
            target = output_dir / f"{slug}.png"
            data = archive.read_file(raw_name)
            if not data:
                skipped += 1
                continue
            temp_blp = output_dir / f".{slug}.blp"
            temp_blp.write_bytes(data)
            try:
                with Image.open(temp_blp) as image:
                    image.convert("RGBA").save(target, "PNG", optimize=True)
            except Exception:
                skipped += 1
                continue
            finally:
                temp_blp.unlink(missing_ok=True)
            seen.add(slug)
            count += 1
    if skipped:
        print(f"Skipped {skipped} unreadable icon entries")
    return len(seen) or count


def read_c_string(block: bytes, offset: int) -> str:
    if offset <= 0 or offset >= len(block):
        return ""
    end = block.find(b"\0", offset)
    if end < 0:
        end = len(block)
    return block[offset:end].decode("utf-8", "ignore")


def parse_item_display_info(data: bytes) -> dict[str, str]:
    magic, row_count, field_count, record_size, string_block_size = struct.unpack("<4sIIII", data[:20])
    if magic != b"WDBC" or field_count < 7:
        raise ValueError("ItemDisplayInfo.dbc hat kein erwartetes WDBC-Format.")
    records_start = 20
    records_end = records_start + row_count * record_size
    records = data[records_start:records_end]
    strings = data[records_end:records_end + string_block_size]
    result: dict[str, str] = {}
    for index in range(row_count):
        start = index * record_size
        values = struct.unpack("<" + "I" * field_count, records[start:start + record_size])
        display_id = values[0]
        icon = read_c_string(strings, values[5]) or read_c_string(strings, values[6])
        if display_id and icon:
            result[str(display_id)] = icon_slug(icon)
    return result


def extract_icon_map(client_dir: Path, output_dir: Path) -> int:
    selected = None
    for mpq_path in mpq_files(client_dir, ITEM_DISPLAY_DBC_ORDER):
        archive = mpyq.MPQArchive(str(mpq_path))
        dbc_name = next((name for name in archive.files if name.lower().endswith(b"itemdisplayinfo.dbc")), None)
        if dbc_name:
            selected = archive.read_file(dbc_name)
    if not selected:
        raise FileNotFoundError("DBFilesClient\\ItemDisplayInfo.dbc wurde im Client nicht gefunden.")
    icon_map = parse_item_display_info(selected)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "icon_map.json").write_text(json.dumps(icon_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(icon_map)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract WoW 3.3.5a item icons and displayid icon mapping.")
    parser.add_argument("--client", default="WoW_3.3.5a_rising-gods.de", help="Path to the WoW client folder.")
    parser.add_argument("--output", default="app/static/item-icons", help="Output folder for PNG icons and icon_map.json.")
    args = parser.parse_args()

    client_dir = Path(args.client).resolve()
    output_dir = Path(args.output).resolve()
    icon_count = extract_icons(client_dir, output_dir)
    map_count = extract_icon_map(client_dir, output_dir)
    print(f"Extracted {icon_count} unique icons to {output_dir}")
    print(f"Wrote {map_count} display-id mappings to {output_dir / 'icon_map.json'}")


if __name__ == "__main__":
    main()
