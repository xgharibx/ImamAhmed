"""Rebuild offline metadata against the final rebased tree before a bot push."""
import subprocess

from generate_app_content import ROOT, build_manifest, prepare_assets, write_json


def finalize(root=ROOT):
    def git(*args, check=True):
        return subprocess.run(['git', '-C', str(root), *args], check=check, capture_output=True, text=True)

    if git('diff', '--cached', '--quiet', check=False).returncode:
        raise ValueError('Unrelated staged changes must not enter the publication amend')
    prepare_assets(root)
    manifest = build_manifest(root)
    write_json(root / 'data/app-content-manifest.json', manifest)
    paths = ['data/app-content-manifest.json']
    if (root / 'assets/app-content').is_dir():
        paths.append('assets/app-content')
    git('add', '--', *paths)
    if git('diff', '--cached', '--quiet', check=False).returncode:
        git('diff', '--cached', '--check')
        git('commit', '--amend', '--no-edit')
    if manifest != build_manifest(root):
        raise ValueError('Content changed during final-tree validation')
    return manifest['revision']


if __name__ == '__main__':
    print(finalize())
