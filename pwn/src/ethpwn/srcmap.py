
from typing import Any, Dict, List, Tuple, TypedDict
from enum import Enum

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

    def pretty_print_source(self, whole_file=False):
        byte_start = self.source_byte_offset_start
        byte_end = self.source_byte_offset_start + self.source_bytes_len

        source = self.source_content

        start_of_first_line = source.rfind('\n', 0, byte_start) + 1
        offset_in_first_line = byte_start - start_of_first_line
        end_of_last_line = source.find('\n', byte_end) + 1
        len_of_remainder_in_last_line = end_of_last_line - byte_end
        if not whole_file:
            source = source[start_of_first_line:end_of_last_line]
            source_formatted = str(dim) + source[:offset_in_first_line] + str(reset)
            source_formatted += source[offset_in_first_line:len(source)-len_of_remainder_in_last_line]
            source_formatted += str(dim) + source[len(source)-len_of_remainder_in_last_line:] + str(reset)
            return source_formatted
        else:
            source = str(dim) + source[:byte_start] + str(reset) + source[byte_start:byte_end] + str(dim) + source[byte_end:] + str(reset)
            return source

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

def symbolize_source_map(src_map_entries: List[SrcMapEntry], source_ids: Dict[int, str]) -> List[Tuple[int, int, str]]:
    result = []
    for entry in src_map_entries:
        source_file = source_ids.get(entry['source_file_index'], None)
        if source_file is None:
            continue
        with open(source_file, 'r') as f:
            source_content = f.read()
        result.append(InstructionSourceInfo.from_srcmap_entry(entry, source_content=source_content))
    return result

class SymbolizedSourceMap:
    def __init__(self, entries: List[InstructionSourceInfo]) -> None:
        self.entries = entries

    def from_src_map(src_map: str, sources: Dict[str, Any]) -> 'SymbolizedSourceMap':
        source_ids = {}
        for source_file, data in sources.items():
            source_ids[data['id']] = source_file
        return SymbolizedSourceMap(symbolize_source_map(parse_srcmap(src_map), source_ids))

    def get_source_info_for_instruction(self, index: int) -> InstructionSourceInfo:
        return self.entries[index]
