from __future__ import annotations
import argparse
from importlib.resources import files
from pathlib import Path
import sys
from . import __version__
from .bundle import load_inputs, publish, render, verify
from .core import InputError, compute

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Verified sewer-cleaning coverage to geometric draft residual setups.')
    parser.add_argument('--version', action='version', version=f'reachplan {__version__}')
    commands = parser.add_subparsers(dest='command',required=True)
    plan = commands.add_parser('plan', help='Create a portable result bundle; exit 3 means review required')
    plan.add_argument('--pipes',type=Path,required=True)
    plan.add_argument('--passes',type=Path,required=True)
    plan.add_argument('--barriers',type=Path)
    plan.add_argument('--since',required=True,help='Inclusive campaign start YYYY-MM-DD')
    plan.add_argument('--as-of',required=True,help='Inclusive campaign end YYYY-MM-DD')
    plan.add_argument('--out',type=Path,required=True,help='New directory; existing directories are refused')
    check = commands.add_parser('verify',help='Recompute every bundle output, offline and after relocation')
    check.add_argument('bundle',type=Path)
    example = commands.add_parser('example',help='Write the constructed example inputs to a new directory')
    example.add_argument('directory',type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'example':
            data = {n:files('reachplan').joinpath('data',n).read_bytes() for n in ('pipes.csv','passes.csv','barriers.csv')}
            publish(args.directory,data)
            print('Constructed example written. Plan with --since 2026-01-01 --as-of 2026-03-31.')
            return 0
        if args.command == 'verify':
            result = verify(args.bundle)
            print(f"Integrity verified by recomputation; planning status: {result['status']}. No authenticity or field-completion claim.")
            return 0
        inputs = load_inputs(args.pipes,args.passes,args.barriers)
        result = compute(inputs,args.since,args.as_of)
        publish(args.out,render(result,inputs))
        t, unit = result['totals'], result['campaign']['unit']
        print(f"{result['status']}: {t['unique_verified_length']} {unit} unique verified; {t['draft_target_length']} {unit} draft targets; {t['review_length']} {unit} unreachable review. Read {args.out/'report.md'}.")
        return 3 if result['status'] == 'review_required' else 0
    except (InputError,OSError) as exc:
        print(f'reachplan: {exc}',file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
