#!/usr/bin/env python3
"""Create a fresh, bounded synthetic OpenZL smoke fixture; never run a benchmark."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

MAX_BYTES = 16 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bytes', type=int, default=1024 * 1024)
    parser.add_argument('--element-width', type=int, choices=(1, 2, 4, 8), default=4)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--pattern', choices=('ramp', 'zeroes'), default='ramp')
    parser.add_argument('--parent', type=Path)
    args = parser.parse_args()
    if not 0 < args.bytes <= MAX_BYTES:
        parser.error(f'--bytes must be between 1 and {MAX_BYTES}')
    if args.bytes % args.element_width:
        parser.error('--bytes must be divisible by --element-width')
    if not 0 <= args.seed < 2**64:
        parser.error('--seed must be an unsigned 64-bit integer')
    parent = args.parent.resolve() if args.parent is not None else None
    if parent is not None and not parent.is_dir():
        parser.error('--parent must be an existing directory')

    if args.pattern == 'zeroes':
        data = bytes(args.bytes)
    else:
        period = min(1024, 2 ** (8 * args.element_width))
        block = b''.join(((args.seed + i) % period).to_bytes(
            args.element_width, 'little') for i in range(period))
        data = (block * ((args.bytes + len(block) - 1) // len(block)))[:args.bytes]
    directory = Path(tempfile.mkdtemp(prefix='agentbay-openzl-', dir=parent)).resolve()
    # Exclusive creation inside a newly owned private directory; never reuse a run.
    with (directory / 'input.bin').open('xb') as stream:
        stream.write(data)
    manifest = {
        'schema_version': 1,
        'synthetic': True,
        'pattern': args.pattern,
        'seed': args.seed,
        'byte_order': 'little',
        'element_width': args.element_width,
        'bytes': len(data),
        'elements': len(data) // args.element_width,
        'input': 'input.bin',
        'sha256': hashlib.sha256(data).hexdigest(),
        'purpose': 'Periodic smoke fixture; not representative performance data.',
    }
    with (directory / 'dataset.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    print(directory)


if __name__ == '__main__':
    main()
