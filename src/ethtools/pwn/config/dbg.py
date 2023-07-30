

from typing import Union


class DebugConfig:
    @property
    def show_opcodes_desc(self) -> bool:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG['dbg'].get('show_opcodes_desc', True)

    @show_opcodes_desc.setter
    def show_opcodes_desc(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['show_opcodes_desc'] = value

    @property
    def stop_on_returns(self) -> bool:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG.get('stop_on_returns', False)

    @stop_on_returns.setter
    def stop_on_returns(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['stop_on_returns'] = value

    @property
    def stop_on_reverts(self) -> bool:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG['dbg'].get('stop_on_reverts', False)

    @stop_on_reverts.setter
    def stop_on_reverts(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['stop_on_reverts'] = value

    @property
    def source_view_cutoff(self) -> Union[int, None]:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG['dbg'].get('source_view_cutoff', None)

    @source_view_cutoff.setter
    def source_view_cutoff(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['source_view_cutoff'] = value

    @property
    def hide_source_view(self) -> bool:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG['dbg'].get('hide_source_view', False)

    @hide_source_view.setter
    def hide_source_view(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['hide_source_view'] = value

    @property
    def hide_sstores(self) -> bool:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG['dbg'].get('hide_sstores', False)

    @hide_sstores.setter
    def hide_sstores(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['hide_sstores'] = value

    @property
    def hide_sloads(self) -> bool:
        from . import GLOBAL_CONFIG
        return GLOBAL_CONFIG['dbg'].get('hide_sloads', False)

    @hide_sloads.setter
    def hide_sloads(self, value: bool):
        from . import GLOBAL_CONFIG
        GLOBAL_CONFIG['dbg']['hide_sloads'] = value

DebugConfig = DebugConfig()