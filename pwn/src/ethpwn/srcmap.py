
from typing import Any, Dict, List, Tuple, TypedDict
from enum import Enum
import math

from ansi.color.fx import faint as dim, reset, bold

# define a python enum jumptype (i = into-function, o=out-of-function, -=none)
class JumpType(Enum):
    INTO_FUNCTION = 'i'
    OUT_OF_FUNCTION = 'o'
    NONE = '-'

class SrcMapEntry(TypedDict):
    src_start_character_index: int
    num_chars: int
    source_file_index: int
    jumpType: JumpType
    modifierDepth: int


def parse_srcmap(srcmap: str) -> List[Tuple[int, int]]:
    entries = srcmap.split(';')
    result = []

    # src_start_character_index, num_chars, source_file_index, jumpType, modifierDepth
    # modifierDepth didn't used to exist so we initialize it to 0
    last_entry = [None, None, None, None, '0'] * 5
    results = []
    for entry in entries:
        cur_entry = last_entry.copy()
        vals = list(entry.split(':'))
        for i in range(len(vals)):
            if vals[i] == '':
                continue
            cur_entry[i] = vals[i]

        results.append(SrcMapEntry(
            src_start_character_index=int(cur_entry[0]),
            num_chars=int(cur_entry[1]),
            source_file_index=int(cur_entry[2]),
            jumpType=JumpType(cur_entry[3]),
            modifierDepth=int(cur_entry[4]),
        ))
        last_entry = cur_entry

    return results

class InstructionSourceInfo:
    def __init__(self,
                 source_content,
                 source_byte_offset_start,
                 source_bytes_len,
                 line_no_start,
                 col_no_start,
                 line_no_end,
                 col_no_end,
                 jump_type=None,
                 modifier_depth=None
                ):
        self.source_content = source_content
        self.source_byte_offset_start = source_byte_offset_start
        self.source_bytes_len = source_bytes_len
        self.line_no_start = line_no_start
        self.col_no_start = col_no_start
        self.line_no_end = line_no_end
        self.col_no_end = col_no_end
        self.jump_type = jump_type
        self.modifier_depth = modifier_depth

    def get_source(self):
        return self.source_content[
            self.source_byte_offset_start:self.source_byte_offset_start+self.source_bytes_len
        ]

    def pretty_print_source(self, context_lines=5):
        byte_start = self.source_byte_offset_start
        byte_end = self.source_byte_offset_start + self.source_bytes_len

        # import ipdb; ipdb.set_trace()
        highlighted = ''
        if byte_start > 0:
            highlighted += self.source_content[:byte_start] + str(reset)
        highlighted += self.source_content[byte_start:byte_end]
        if byte_end < len(self.source_content):
            highlighted += str(dim) + self.source_content[byte_end:]

        lines = highlighted.split('\n')
        start_line = max(0, self.line_no_start - context_lines)
        end_line = min(len(lines), self.line_no_end + context_lines)
        return str(dim) + '\n'.join(lines[start_line:end_line]) + str(reset)

    def from_srcmap_entry(entry: SrcMapEntry, source_content: str=None) -> 'InstructionSourceInfo':

        if source_content is None:
            line_no_start, col_no_start = None, None
            line_no_end, col_no_end = None, None
        else:
            line_no_start, col_no_start = get_line_col_from_byte_offset(source_content, entry['src_start_character_index'])
            line_no_end, col_no_end = get_line_col_from_byte_offset(source_content, entry['src_start_character_index'] + entry['num_chars'])

        return InstructionSourceInfo(
            source_content=source_content,
            source_byte_offset_start=entry['src_start_character_index'],
            source_bytes_len=entry['num_chars'],
            line_no_start=line_no_start,
            col_no_start=col_no_start,
            line_no_end=line_no_end,
            col_no_end=col_no_end,
            jump_type=entry['jumpType'],
            modifier_depth=entry['modifierDepth'],
        )


def get_line_col_from_byte_offset(source: str, byte_offset: int) -> Tuple[int, int]:
    line_no = source.count('\n', 0, byte_offset) + 1
    col_no = byte_offset - source.rfind('\n', 0, byte_offset)
    return line_no, col_no

def symbolize_source_map(src_map_entries: List[SrcMapEntry], sources_by_id: Dict[int, str]) -> List[InstructionSourceInfo]:
    result = []
    # import ipdb; ipdb.set_trace()
    for entry in src_map_entries:
        if entry['source_file_index'] == -1:
            result.append(InstructionSourceInfo.from_srcmap_entry(entry))
            continue
        source_file = sources_by_id[entry['source_file_index']]
        assert source_file is not None
        assert source_file['id'] == entry['source_file_index']
        path = source_file['path']
        content = source_file['content']
        result.append(InstructionSourceInfo.from_srcmap_entry(entry, source_content=content))
    return result

class SymbolizedSourceMap:
    def __init__(self, entries: List[InstructionSourceInfo]) -> None:
        self.entries = entries

    def from_src_map(src_map: str, sources_by_id: Dict[int, Any]) -> 'SymbolizedSourceMap':
        return SymbolizedSourceMap(symbolize_source_map(parse_srcmap(src_map), sources_by_id))

    def get_source_info_for_instruction(self, index: int) -> InstructionSourceInfo:
        return self.entries[index]
