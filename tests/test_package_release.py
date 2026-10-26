import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
spec=importlib.util.spec_from_file_location('release',Path(__file__).resolve().parents[1]/'packaging/package_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)


class PackageTests(unittest.TestCase):
    def test_cache_and_python_versions_never_enter_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'patch';root.mkdir();(root/'tools/__pycache__').mkdir(parents=True)
            (root/'__pycache__').mkdir()
            (root/'manifest.json').write_text('{}');(root/'patcher.py').write_text('pass')
            (root/'tools/helper.py').write_text('pass')
            for relative in ['__pycache__/patcher.cpython-312.pyc','tools/__pycache__/helper.cpython-313.pyc','stray.pyo']:
                (root/relative).write_bytes(b'temporary')
            out=Path(tmp)/'fixed.zip';m=release.build_package(root,out)
            self.assertEqual(set(m['package_sha256']),{'patcher.py','tools/helper.py'})
            with zipfile.ZipFile(out) as z:
                self.assertFalse(any('__pycache__' in n or n.endswith(('.pyc','.pyo')) for n in z.namelist()))
                # A fresh extraction, with no interpreter-generated files, has
                # every file the installer's integrity check requires.
                clean=Path(tmp)/'clean';z.extractall(clean)
                for name,checksum in m['package_sha256'].items():
                    self.assertEqual(hashlib.sha256((clean/'patch'/name).read_bytes()).hexdigest(),checksum)

    def test_reject_zip_inside_source_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):release.build_package(root,root/'patch.zip')


if __name__=='__main__':unittest.main()
