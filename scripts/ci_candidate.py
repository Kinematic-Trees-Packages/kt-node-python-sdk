#!/usr/bin/env python3
"""Seal, stage and recheck unpublished SDK artifacts; never edit KTM's store."""
import argparse
import base64
import hashlib
import json
import pathlib
import shutil
import tarfile
import urllib.parse


def manifest_artifacts(root):
    manifest = json.loads((root / 'package.ktm.json').read_text())
    distribution = manifest['distribution']
    if distribution.get('urlStrategy') != 'local-relative':
        raise ValueError('candidate artifacts must be local-relative')
    artifacts = {}
    for package in distribution['packages']:
        url = urllib.parse.urlsplit(package['url'])
        path = pathlib.PurePosixPath(url.path)
        if (url.scheme or url.netloc or url.query or url.fragment
                or path.is_absolute() or '..' in path.parts or not path.parts):
            raise ValueError('unsafe candidate artifact path')
        artifact = root / path
        content = artifact.read_bytes()
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(content).digest()).decode()
        if integrity != package['integrity'] or len(content) != package['size']:
            raise ValueError('candidate artifact differs from publication manifest')
        environment = package['environment']
        if environment in artifacts:
            raise ValueError('expected one primary artifact per environment')
        artifacts[environment] = artifact
    if set(artifacts) != {env['name'] for env in manifest['runEnvironments']}:
        raise ValueError('candidate artifact environments do not match manifest')
    return artifacts


def inventory(root):
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('candidate symlinks are forbidden')
        if path.is_file():
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if 'package.ktm.json' not in files:
        raise ValueError('candidate manifest missing')
    manifest_artifacts(root)
    return files


def verify(root, receipt):
    if inventory(root) != json.loads(receipt.read_text()):
        raise ValueError('candidate changed after sealing')


def stage(root, receipt, environment, output):
    verify(root, receipt)
    artifacts = manifest_artifacts(root)
    if environment not in artifacts:
        raise ValueError('unknown environment')
    artifact = artifacts[environment]
    if not artifact.name.endswith('.tar.gz'):
        raise ValueError('expected candidate tar.gz archive')
    if output.exists():
        raise ValueError('candidate output must be fresh')
    with tarfile.open(artifact) as archive:
        for member in archive.getmembers():
            path = pathlib.PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('unsafe candidate archive member')
        output.mkdir(parents=True)
        for member in archive.getmembers():
            target = output / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open('xb') as destination:
                    shutil.copyfileobj(source, destination)
                target.chmod(member.mode & 0o777)
    verify(root, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seal', 'stage', 'verify'])
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--receipt', type=pathlib.Path, required=True)
    parser.add_argument('--environment')
    parser.add_argument('--output', type=pathlib.Path)
    args = parser.parse_args()
    if args.action == 'seal':
        files = inventory(args.root)
        with args.receipt.open('x') as stream:
            json.dump(files, stream, sort_keys=True, indent=2)
    elif args.action == 'stage':
        if not args.environment or args.output is None:
            parser.error('stage requires --environment and --output')
        stage(args.root, args.receipt, args.environment, args.output)
    else:
        verify(args.root, args.receipt)
    print('candidate ' + args.action + ' PASS')


if __name__ == '__main__':
    main()
