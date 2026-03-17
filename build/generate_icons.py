from __future__ import annotations

from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
SOURCE_ICON = ASSETS_DIR / "app.png"
WINDOWS_ICON = ASSETS_DIR / "app.ico"
MAC_ICON = ASSETS_DIR / "app.icns"

WINDOWS_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
MAC_SIZES = [(32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)]
CONTENT_RATIO = 0.86


def _normalized_icon_canvas(source: Image.Image) -> Image.Image:
    rgba_image = source.convert("RGBA")
    alpha_bbox = rgba_image.getchannel("A").getbbox()
    if alpha_bbox is None:
        trimmed_image = rgba_image
    else:
        trimmed_image = rgba_image.crop(alpha_bbox)

    canvas_size = max(rgba_image.size)
    target_edge = max(1, round(canvas_size * CONTENT_RATIO))
    fitted_image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    resized_image = trimmed_image.resize((target_edge, target_edge), Image.Resampling.LANCZOS)
    offset_x = (canvas_size - target_edge) // 2
    offset_y = (canvas_size - target_edge) // 2
    fitted_image.alpha_composite(resized_image, (offset_x, offset_y))
    return fitted_image


def _save_windows_icon(source: Image.Image) -> None:
    source.save(
        WINDOWS_ICON,
        format="ICO",
        sizes=WINDOWS_SIZES,
        bitmap_format="bmp",
    )


def _save_mac_icon(source: Image.Image) -> None:
    base_image = source.resize(MAC_SIZES[0], Image.Resampling.LANCZOS)
    extra_images = [source.resize(size, Image.Resampling.LANCZOS) for size in MAC_SIZES[1:]]
    base_image.save(
        MAC_ICON,
        format="ICNS",
        append_images=extra_images,
    )


def main() -> int:
    if not SOURCE_ICON.exists():
        raise FileNotFoundError(f"Source icon not found: {SOURCE_ICON}")

    with Image.open(SOURCE_ICON) as source_image:
        normalized_image = _normalized_icon_canvas(source_image)
        _save_windows_icon(normalized_image)
        _save_mac_icon(normalized_image)

    print(f"Generated {WINDOWS_ICON}")
    print(f"Generated {MAC_ICON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
