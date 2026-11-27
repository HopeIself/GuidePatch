"""Build, inspect, verify and search GuidePatch records."""
import argparse
import json
import sys

from core import apply, build, next_prompt, read, search, validate_patch, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='cmd', required=True)
    make = commands.add_parser('build')
    make.add_argument('case')
    make.add_argument('out')
    advance = commands.add_parser('next', help='Show one action or the evidence needed to continue')
    advance.add_argument('patch')
    verify = commands.add_parser('verify')
    verify.add_argument('patch')
    verify.add_argument('feedback')
    verify.add_argument('out')
    lookup = commands.add_parser('search')
    lookup.add_argument('history')
    lookup.add_argument('query')
    args = parser.parse_args()
    if args.cmd == 'search':
        output = search(args.history, read(args.query))
    elif args.cmd == 'next':
        output = next_prompt(read(args.patch))
    else:
        if args.cmd == 'build':
            patch = build(read(args.case))
        else:
            patch = apply(validate_patch(read(args.patch)), read(args.feedback))
        validate_patch(patch)
        write(args.out, patch)
        output = {'revision':patch['revision'], 'status':patch['status'],
                  'steps':[{key:step[key] for key in ('id','label','decision','status')}
                           for step in patch['steps']]}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        sys.exit('Rejected: '+str(exc))
