"""Write version identifiers only; never dump environment or pip URL metadata."""
import importlib.metadata
import json
import platform
from pathlib import Path

if __name__ == '__main__':
    destination = Path('verification')
    destination.mkdir(exist_ok=True)
    versions = sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions() if d.metadata['Name'])
    (destination / 'inventory.json').write_text(json.dumps({'python': platform.python_version(), 'dependencies': versions}, indent=2), encoding='utf-8')
