"""Size the supplied artwork for Android and Play without redrawing it."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = "#003c2e"


def export(source):
    logo = Image.open(source).convert("RGBA")
    if logo.width != logo.height:
        raise ValueError("The approved logo must be square")
    resources = ROOT / "app/src/main/res"
    listing = ROOT / "play-store"
    listing.mkdir(exist_ok=True)

    def square(size, coverage=1, background=BACKGROUND):
        canvas = Image.new("RGBA", (size, size), background)
        side = round(size * coverage)
        resized = logo.resize((side, side), Image.Resampling.LANCZOS)
        canvas.alpha_composite(resized, ((size - side) // 2, (size - side) // 2))
        return canvas

    for density, size in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)]:
        directory = resources / ("mipmap-" + density)
        directory.mkdir(exist_ok=True)
        icon = square(size)
        silhouette = Image.new("L", (size, size), 0)
        ImageDraw.Draw(silhouette).rounded_rectangle((0, 0, size - 1, size - 1), radius=size * .18, fill=255)
        icon.putalpha(silhouette)
        icon.save(directory / "ic_launcher.png")
        ImageDraw.Draw(silhouette).rectangle((0, 0, size, size), fill=0)
        ImageDraw.Draw(silhouette).ellipse((0, 0, size - 1, size - 1), fill=255)
        icon.putalpha(silhouette)
        icon.save(directory / "ic_launcher_round.png")
    directory = resources / "drawable-nodpi"
    directory.mkdir(exist_ok=True)
    # Android displays the central 72dp of a 108dp adaptive icon layer.
    foreground = square(432, .70, (0, 0, 0, 0))
    foreground.save(directory / "logo_foreground.png")
    square(512).convert("RGB").save(listing / "icon-512.png")
    feature = Image.new("RGB", (1024, 500), BACKGROUND)
    feature.paste(square(500).convert("RGB"), (262, 0))
    feature.save(listing / "feature-graphic.png")
    preview = Image.new("RGBA", (432, 432), BACKGROUND)
    preview.alpha_composite(foreground)
    preview = preview.crop((72, 72, 360, 360)).resize((512, 512), Image.Resampling.LANCZOS)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 511, 511), fill=255)
    preview.putalpha(mask)
    preview.save(listing / "launcher-preview.png")
    print(f"Exported approved {logo.width}x{logo.height} artwork to Android and Play assets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, nargs="?", default=ROOT / "branding/logo-source.png")
    export(parser.parse_args().source)
