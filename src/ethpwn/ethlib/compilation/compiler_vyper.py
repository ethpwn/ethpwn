"""
This module contains the `VyperCompiler` class, which is a wrapper around `ethcx`.
`VyperCompiler` provides a convenient interface to compile smart contracts implemented in Vyper.
"""

from pathlib import Path
from typing import Dict, List, Union
import ethcx

def configure_vyper_from_version_line(version_line: str):
    if version_line is None:
        return

    ethcx.install_vyper_pragma(version_line)
    ethcx.set_vyper_version_pragma(version_line)


def find_version_line(content: str):
    for line in content.splitlines():
        if line.strip().startswith("# @version"):
            return line


def get_version_lines(files: List[str]):
    version_lines = set()
    for file in files:
        with open(file, "r") as f:
            vyper_version_line = find_version_line(f.read())
            if vyper_version_line is not None:
                version_lines.add(vyper_version_line)
    return list(version_lines)


def merge_version_lines(pragma_lines: List[str]):
    if len(pragma_lines) == 0:
        return None
    if len(pragma_lines) == 1:
        return pragma_lines[0]
    pragma_lines = sorted(
        pragma_lines,
        key=lambda x: tuple(
            int(y) for y in x.split()[2].rstrip(";").strip().lstrip("><^=").split(".")
        ),
    )
    return pragma_lines[-1]  # take the highest requested one


class VyperCompiler:
    def __init__(self) -> None:
        # self.import_remappings: Dict[str, str] = {}
        # self.allowed_directories: List[str] = []
        pass

    # def add_import_remappings(self, remappings: Dict[str, str]):
    #     self.import_remappings.update(remappings)
    #     self.add_allowed_directories(remappings.values())

    # def add_allowed_directories(self, directories: List[str]):
    #     self.allowed_directories.extend(directories)

    # def get_output_values(self):
    #     output_values = ['abi','bin','bin-runtime','asm','hashes','metadata','srcmap','srcmap-runtime']
    #     if ethcx.get_solc_version().minor >= 6:
    #         output_values.append('storage-layout')
    #     return output_values

    # def get_import_remappings(self, no_default_import_remappings=False, import_remappings=None, **kwargs):
    #     result = {} if no_default_import_remappings else self.import_remappings.copy()
    #     if import_remappings is not None:
    #         result.update(import_remappings)
    #     return result

    # def get_allow_paths(self):
    #     return self.allowed_directories

    def get_default_optimizer_settings(self, optimizer_runs=1000):
        return {"enabled": True, "runs": optimizer_runs}

    def get_vyper_input_json(self, sources_entry):

        sources_dict = {}
        for fname in sources_entry:
            sources_dict[fname] = {}
            if 'content' not in sources_entry[fname]:
                with open(fname, 'r') as f:
                    sources_dict[fname]['content'] = f.read()
            else:
                sources_dict[fname]['content'] = sources_entry[fname]['content']

        return {
            "language": "Vyper",
            # use dictionary comprehension to build the dict
            "sources": sources_entry,
            "settings": {
                # 'remappings': [f'{key}={value}' for key, value in sorted(remappings.items())],
                "outputSelection": {"*": {"*": ["*"], "": ["*"]}},
                # 'optimizer': optimizer_settings if optimizer_settings is not None else {'enabled': False},
            },
        }

    def compile_source(
        self,
        input_json: str,
        file_name: Union[Path, str],
        libraries=None,
        optimizer_settings=None,
        #    no_default_import_remappings=False, extra_import_remappings=None,
        **kwargs,
    ):
        assert libraries is None, "libraries not supported for vyper"
        configure_vyper_from_version_line(find_version_line(input_json))

        # if optimizer_settings is None:
        #     optimizer_settings = self.get_default_optimizer_settings()

        input_json = self.get_vyper_input_json(
            {str(file_name): {"content": input_json}},
            # remappings=self.get_import_remappings(no_default_import_remappings, extra_import_remappings),
            # optimizer_settings=optimizer_settings,
        )

        kwargs = _add_cached_vyper_binary_to_kwargs(kwargs)

        output_json = ethcx.compile_vyper_standard(
            input_json,
            # allow_paths=self.get_allow_paths(),
            **kwargs,
        )

        return input_json, output_json

    def compile_sources(
        self,
        sources: Dict[str, str],
        libraries=None,
        optimizer_settings=None,
        # no_default_import_remappings=False, extra_import_remappings=None,
        **kwargs,
    ):
        assert libraries is None, "libraries not supported for vyper"
        pragma_lines = [find_version_line(s["content"]) for file, s in sources.items()]

        configure_vyper_from_version_line(merge_version_lines(pragma_lines))

        # if optimizer_settings is None:
        #     optimizer_settings = self.get_default_optimizer_settings()

        # sources should already be in the right format
        input_json = self.get_vyper_input_json(
            sources,
            # remappings=self.get_import_remappings(
            #     no_default_import_remappings, extra_import_remappings
            # ),
            # optimizer_settings=optimizer_settings,
        )

        kwargs = _add_cached_vyper_binary_to_kwargs(kwargs)

        output_json = ethcx.compile_vyper_standard(
            input_json,
            # allow_paths=self.get_allow_paths(),
            **kwargs,
        )
        return input_json, output_json

    def compile_files(
        self,
        files: List[Union[str, Path]],
        libraries=None,
        optimizer_settings=None,
        #   no_default_import_remappings=False, extra_import_remappings=None,
        **kwargs,
    ):
        assert libraries is None, "libraries not supported for vyper"
        version_lines = get_version_lines(files)
        assert len(version_lines) <= 1, "Multiple solidity versions in files"
        configure_vyper_from_version_line(
            version_lines[0] if len(version_lines) == 1 else None
        )

        # if optimizer_settings is None:
        #     optimizer_settings = self.get_default_optimizer_settings()

        input_json = self.get_vyper_input_json(
            files
            # remappings=self.get_import_remappings(
            #     no_default_import_remappings, extra_import_remappings
            # ),
            # optimizer_settings=optimizer_settings,
        )

        kwargs = _add_cached_vyper_binary_to_kwargs(kwargs)

        output_json = ethcx.compile_vyper_standard(
            input_json,
            # allow_paths=self.get_allow_paths() + [os.path.dirname(file) for file in files],
            **kwargs,
        )
        return input_json, output_json


vyper_binary_cache = {}


def _add_cached_vyper_binary_to_kwargs(kwargs):
    vyper_binary_version = kwargs.get("vyper_version", None)
    if vyper_binary_version is None:
        return kwargs
    if kwargs.get("vyper_binary", None) is None:
        if vyper_binary_version in vyper_binary_cache:
            vyper_binary = vyper_binary_cache[vyper_binary_version]
        else:
            ethcx.install_vyper(vyper_binary_version)
            vyper_binary = ethcx.compilers.vyper.install.get_executable(
                vyper_binary_version
            )
            vyper_binary_cache[vyper_binary_version] = vyper_binary
        kwargs["vyper_binary"] = vyper_binary
    return kwargs
