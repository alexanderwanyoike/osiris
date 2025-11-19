# Osiris OS Branding Scripts

Tools for creating branded Osiris OS assets.

## brand-wallpaper.py

Creates branded wallpapers by overlaying the Osiris logo on any image.

### Setup

```bash
# Create virtual environment (first time only)
python3 -m venv venv

# Install dependencies
./venv/bin/pip install -r requirements.txt
```

### Usage

```bash
# Brand a dark wallpaper with white logo
./venv/bin/python3 brand-wallpaper.py -i wallpaper.jpg -o branded.png -l dark

# Brand a light wallpaper with black logo
./venv/bin/python3 brand-wallpaper.py -i wallpaper.jpg -o branded.png -l light

# Brand with scaled logo (50% size)
./venv/bin/python3 brand-wallpaper.py -i wallpaper.jpg -o branded.png -l dark -s 0.5

# Brand with semi-transparent logo
./venv/bin/python3 brand-wallpaper.py -i wallpaper.jpg -o branded.png -l dark -a 180
```

### Options

- `-i, --input`: Input wallpaper image path (required)
- `-o, --output`: Output branded wallpaper path (required)
- `-l, --logo`: Logo type - `dark` (white logo) or `light` (black logo) (default: dark)
- `-s, --scale`: Logo scale factor (default: 1.0)
- `-a, --alpha`: Logo opacity 0-255 (0=transparent, 255=opaque, default: 255)

### Examples

#### Create a collection of dark wallpapers

```bash
for img in ~/Pictures/wallpapers/*.jpg; do
    filename=$(basename "$img" .jpg)
    ./venv/bin/python3 brand-wallpaper.py -i "$img" -o "../wallpapers/${filename}-osiris-dark.png" -l dark
done
```

#### Create a light wallpaper with subtle logo

```bash
./venv/bin/python3 brand-wallpaper.py \
    -i abstract-light.jpg \
    -o abstract-light-osiris.png \
    -l light \
    -s 0.8 \
    -a 200
```

### Notes

- Use `dark` logo (white) for dark/colorful backgrounds
- Use `light` logo (black) for light/pale backgrounds
- Output format is determined by file extension (PNG recommended for transparency)
- Original images are never modified
