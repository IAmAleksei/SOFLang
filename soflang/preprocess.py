from pathlib import Path
from typing import List, Set

from soflang.centi_parser import Parser
from soflang.formatter import Formatter


def recursive_parse(filepath: str) -> list:
    initial_path = Path(filepath)
    if not initial_path.is_absolute():
        initial_path = Path.cwd().joinpath(initial_path)
    initial_path = initial_path.resolve()
    checked_paths: Set[Path] = set()
    load_queue: List[Path] = [initial_path]
    result = []
    while len(load_queue) > 0:
        cur_path = load_queue.pop()
        with cur_path.open() as f:
            text = f.read()
        parsed_text = Parser().parse_program(text)
        for global_expr in parsed_text:
            if global_expr['type'] == 'import_decl':
                ident: str = global_expr['identifier']
                if ident.startswith('@/'):
                    next_path_root = Path(__file__).parent / 'slib'
                    ident = ident[2:]
                else:
                    next_path_root = cur_path.parent
                next_path = next_path_root.joinpath(ident + '.sofl').resolve()
                if next_path not in checked_paths:
                    checked_paths.add(next_path)
                    load_queue.append(next_path)
            else:
                result.append(global_expr)
    return result


def parse_with_imports_resolution(filepath: str) -> tuple[list, str]:
    parsed_text = recursive_parse(filepath)
    formatted_text = Formatter().format(parsed_text)
    return Parser().parse_program(formatted_text), formatted_text
