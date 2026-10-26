"""Finalize a staged patch manifest and ZIP from exactly the same file list."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile


def package_files(root):
    root=Path(root)
    return [p for p in sorted(root.rglob('*'))
            if p.is_file() and p.name!='manifest.json'
            and '__pycache__' not in p.relative_to(root).parts
            and p.suffix.lower() not in {'.pyc','.pyo','.partial'}
            and p.name!='.DS_Store']


def build_package(root,output,version='0.1.1-test'):
    root,output=Path(root),Path(output)
    if root.resolve() in output.resolve().parents:
        raise ValueError('ZIP output must be outside the package directory')
    manifest_path=root/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    files=package_files(root)
    manifest['version']=version
    manifest['package_sha256']={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files+[manifest_path]:z.write(p,str(Path(root.name)/p.relative_to(root)))
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('ZIP verification failed')
        for name,digest in manifest['package_sha256'].items():
            if hashlib.sha256(z.read(str(Path(root.name)/name))).hexdigest()!=digest:
                raise ValueError('Manifest/ZIP content mismatch: '+name)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--version',default='0.1.1-test');args=p.parse_args()
    result=build_package(args.directory,args.output,args.version)
    print(f'Packaged {len(result["package_sha256"])} verified files; no Python caches included')
