import os
from pathlib import Path
from typing import Dict, List, Union
import solcx

def configure_solcx_for_pragma(pragma_line: str):
    if pragma_line is None:
        return

    solcx.install_solc_pragma(pragma_line)
    solcx.set_solc_version_pragma(pragma_line)

def find_pragma_line(content: str):
    for line in content.splitlines():
        if line.strip().startswith('pragma solidity'):
            return line

def get_pragma_lines(files: List[str]):
    pragma_lines = set()
    for file in files:
        with open(file, 'r') as f:
            solidity_pragma_line = find_pragma_line(f.read())
            if solidity_pragma_line is not None:
                pragma_lines.add(solidity_pragma_line)
    return list(pragma_lines)

class SolidityCompiler:
    def __init__(self) -> None:
        self.import_remappings: Dict[str, str] = {}
        self.allowed_directories: List[str] = []

    def add_import_remappings(self, remappings: Dict[str, str]):
        self.import_remappings.update(remappings)
        self.add_allowed_directories(remappings.values())

    def add_allowed_directories(self, directories: List[str]):
        self.allowed_directories.extend(directories)

    def get_output_values(self):
        output_values = ['abi','bin','bin-runtime','asm','hashes','metadata','srcmap','srcmap-runtime']
        if solcx.get_solc_version().minor >= 6:
            output_values.append('storage-layout')
        return output_values

    def get_import_remappings(self, **kwargs):
        import_remappings = {} if kwargs.get('no_default_import_remappings', False) else self.import_remappings.copy()
        if 'import_remappings' in kwargs:
            import_remappings.update(kwargs.pop('import_remappings'))
        return import_remappings

    def get_allow_paths(self):
        return self.allowed_directories

    def get_solc_input_json(self, sources_entry, **kwargs):
        return {
            "language": "Solidity",
            'sources': sources_entry,
            'settings': {
                'remappings': [f'{key}={value}' for key, value in sorted(self.get_import_remappings(**kwargs).items())],
                'outputSelection': { "*": { "*": [ "*" ], "": [ "*" ] } },
            }
        }

    def compile_source(self, source: str, file_name: Union[Path, str], **kwargs):

        configure_solcx_for_pragma(find_pragma_line(source))

        source = self.get_solc_input_json({str(file_name): {'content': source}}, **kwargs)

        return solcx.compile_standard(
            source,
            allow_paths=self.get_allow_paths(),
            **kwargs
            )

    def compile_files(self, files: List[Union[str, Path]], **kwargs):
        pragma_lines = get_pragma_lines(files)
        assert len(pragma_lines) <= 1, "Multiple solidity versions in files"
        configure_solcx_for_pragma(pragma_lines[0] if len(pragma_lines) == 1 else None)

        source = self.get_solc_input_json({
            str(path): {"urls": [str(path)]} for path in files
        }, **kwargs)

        return solcx.compile_standard(
            source,
            allow_paths=self.get_allow_paths() + [os.path.dirname(file) for file in files],
            **kwargs
            )