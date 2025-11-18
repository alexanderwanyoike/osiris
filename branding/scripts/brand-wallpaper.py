#!/usr/bin/env python3
"""
Osiris OS Wallpaper Branding Tool

Creates branded wallpapers by overlaying the Osiris logo on any image.
"""

import argparse
import sys
from pathlib import Path
from PIL import Image


def get_logo_path(logo_type: str, script_dir: Path) -> Path:
    """Get the path to the logo file based on type."""
    logo_paths = {
        'dark': script_dir.parent / 'logo-dark.png',  # White logo for dark backgrounds
        'light': script_dir.parent / 'logo-light.png'  # Black logo for light backgrounds
    }

    logo_path = logo_paths.get(logo_type.lower())
    if not logo_path or not logo_path.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}")

    return logo_path


def brand_wallpaper(input_path: str, output_path: str, logo_type: str = 'dark',
                    scale: float = 1.0, opacity: int = 255):
    """
    Overlay Osiris logo on an image.

    Args:
        input_path: Path to input image
        output_path: Path to save branded image
        logo_type: 'dark' for white logo or 'light' for black logo
        scale: Logo scale factor (1.0 = original size)
        opacity: Logo opacity (0-255, 255 = fully opaque)
    """
    script_dir = Path(__file__).parent

    # Load input image
    print(f"Loading image: {input_path}")
    try:
        background = Image.open(input_path).convert('RGBA')
    except Exception as e:
        print(f"Error loading image: {e}")
        sys.exit(1)

    # Load logo
    logo_path = get_logo_path(logo_type, script_dir)
    print(f"Loading logo: {logo_path}")
    logo = Image.open(logo_path).convert('RGBA')

    # Scale logo if needed
    if scale != 1.0:
        new_size = (int(logo.width * scale), int(logo.height * scale))
        logo = logo.resize(new_size, Image.Resampling.LANCZOS)
        print(f"Logo scaled to: {new_size}")

    # Adjust logo opacity if needed
    if opacity < 255:
        # Split the logo into RGB and alpha channels
        r, g, b, a = logo.split()
        # Adjust alpha channel
        a = a.point(lambda x: int(x * (opacity / 255)))
        # Merge back
        logo = Image.merge('RGBA', (r, g, b, a))
        print(f"Logo opacity set to: {opacity}/255")

    # Calculate position to center the logo
    bg_width, bg_height = background.size
    logo_width, logo_height = logo.size

    position = (
        (bg_width - logo_width) // 2,
        (bg_height - logo_height) // 2
    )

    # Create a composite image
    print(f"Placing logo at center: {position}")
    background.paste(logo, position, logo)

    # Convert back to RGB for saving (if needed)
    if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
        background = background.convert('RGB')

    # Save the result
    print(f"Saving branded wallpaper: {output_path}")
    background.save(output_path, quality=95)
    print("✓ Done!")


def main():
    parser = argparse.ArgumentParser(
        description='Brand wallpapers with Osiris logo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Brand a dark wallpaper with white logo
  %(prog)s -i wallpaper.jpg -o branded.png -l dark

  # Brand a light wallpaper with black logo
  %(prog)s -i wallpaper.jpg -o branded.png -l light

  # Brand with scaled logo (50%% size)
  %(prog)s -i wallpaper.jpg -o branded.png -l dark -s 0.5

  # Brand with semi-transparent logo
  %(prog)s -i wallpaper.jpg -o branded.png -l dark -a 180
        '''
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input wallpaper image path'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output branded wallpaper path'
    )

    parser.add_argument(
        '-l', '--logo',
        choices=['dark', 'light'],
        default='dark',
        help='Logo type: dark (white) for dark backgrounds, light (black) for light backgrounds (default: dark)'
    )

    parser.add_argument(
        '-s', '--scale',
        type=float,
        default=1.0,
        help='Logo scale factor (default: 1.0)'
    )

    parser.add_argument(
        '-a', '--alpha',
        type=int,
        default=255,
        choices=range(0, 256),
        metavar='0-255',
        help='Logo opacity (0=transparent, 255=opaque, default: 255)'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Brand the wallpaper
    brand_wallpaper(
        args.input,
        args.output,
        args.logo,
        args.scale,
        args.alpha
    )


if __name__ == '__main__':
    main()
