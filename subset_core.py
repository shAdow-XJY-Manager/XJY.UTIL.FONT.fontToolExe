"""Local font subsetting, shared by platform entry points."""
from pathlib import Path
import argparse
import sys

SUPPORTED = {'.ttf', '.otf', '.woff'}


def subset_font(source, output, text_file):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    source, output, text_file = map(Path, (source, output, text_file))
    if source.suffix.lower() not in SUPPORTED:
        raise ValueError('Supported input formats: TTF, OTF, WOFF')
    if not source.is_file() or not text_file.is_file():
        raise ValueError('Source font and UTF-8 character file must exist')
    if source.resolve() == output.resolve():
        raise ValueError('Output must not overwrite the source font')
    if output.exists():
        raise ValueError('Output already exists; choose a new filename')
    if not output.parent.is_dir():
        raise ValueError('Output directory does not exist')
    text = text_file.read_text(encoding='utf-8')
    if not text:
        raise ValueError('Character file is empty')
    font = TTFont(source)
    try:
        extension = output.suffix.lower()
        sfnt_extension = '.otf' if font.sfntVersion == 'OTTO' else '.ttf'
        if extension == '.woff':
            font.flavor = 'woff'
        elif extension == sfnt_extension:
            font.flavor = None
        else:
            raise ValueError(f'Output extension must be {sfnt_extension} or .woff for this font')
        requested = {ord(char) for char in text} | set(range(0x20, 0x30))
        missing = sorted(requested - set(font.getBestCmap() or {}))
        options = subset.Options()
        options.layout_features = ['*']
        worker = subset.Subsetter(options=options)
        worker.populate(unicodes=requested)
        worker.subset(font)
        temporary = output.with_name(output.name + '.partial')
        try:
            font.save(temporary)
            with TTFont(temporary) as checked:
                checked.getBestCmap()
            temporary.rename(output)
        finally:
            temporary.unlink(missing_ok=True)
        print(f'OUTPUT: {output}')
        print(f'SIZE: {source.stat().st_size} -> {output.stat().st_size}')
        if missing:
            print('MISSING: ' + ', '.join(f'U+{code:04X}' for code in missing[:100]))
        return missing
    finally:
        font.close()


def main(base_path):
    parser = argparse.ArgumentParser(description='Subset a font locally; inputs are never uploaded.')
    parser.add_argument('--source')
    parser.add_argument('--output')
    parser.add_argument('--text-file')
    args = parser.parse_args()
    try:
        config = Path(base_path) / 'config'
        source = args.source or (config / 'sourcePath.txt').read_text(encoding='utf-8').strip()
        output = args.output or (config / 'outputPath.txt').read_text(encoding='utf-8').strip()
        text_file = args.text_file or config / 'fontcontent.txt'
        subset_font(source, output, text_file)
        return 0
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
