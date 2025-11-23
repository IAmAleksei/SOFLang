import copy
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
        print(f"Loading {cur_path}")
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


def resolve_templates(parsed_text: list) -> list:
    template_decls = {}
    nontemplate_decls = []
    for global_expr in parsed_text:
        if (global_expr['type'] == 'clazz_decl' or global_expr['type'] == 'func_decl') and global_expr['template_params']:
            name = global_expr['identifier']
            assert name not in template_decls, "Multiple templates with the same name is not allowed"
            template_decls[name] = global_expr
        else:
            nontemplate_decls.append(global_expr)
    resolved_template_functions = {}

    def resolve_func_call(call: dict, template_params: dict):
        if not call['template_params']:
            return
        resolved_params = []
        for p in call['template_params']:
            if p.get('type') == 'placeholder':
                resolved_params.append(template_params[p['value']])
            else:
                resolved_params.append(p)
        resolved_name = resolve_template_expr(call['identifier'], resolved_params)
        call['identifier'] = resolved_name
        call['template_params'] = []

    def resolve_inner(lines, template_params: dict):
        for line in lines:
            if line['type'] == 'placeholder':
                v = line['value']
                line.clear()
                line.update(template_params[v])
            elif line['type'] == 'var_decl':
                resolve_type(line['kind'], template_params)
            elif line['type'] == 'var_decl_with_assign':
                resolve_type(line['kind'], template_params)
                resolve_inner([line['value']], template_params)
            elif line['type'] == 'if_expr':
                resolve_inner(line['body'], template_params)
            elif line['type'] == 'while_expr':
                resolve_inner(line['body'], template_params)
            elif line['type'] == 'constructor_call':
                resolve_func_call(line, template_params)
            elif line['type'] == 'func_call':
                resolve_func_call(line, template_params)
            elif line['type'] == 'gen_expr':
                resolve_inner([line['left']], template_params)
                resolve_inner([line['right']], template_params)
            elif line['type'] == 'assignment':
                resolve_inner([line['value']], template_params)

    def resolve_type(kind: dict, template_params: dict):
        if kind == 'auto':
            return
        if kind['kind']['dim'] == 'array' and isinstance(kind['kind']['size'], dict):
            sz = template_params[kind['kind']['size']['value']]
            assert sz['type'] == 'integer'
            kind['kind']['size'] = sz['value']
        if kind['base']['type'] == 'placeholder':
            kind['base'] = template_params[kind['base']['value']]['base']
        if kind['template_params']:
            resolved_params = []
            for p in kind['template_params']:
                if p.get('type') == 'placeholder':
                    resolved_params.append(template_params[p['value']])
                else:
                    resolved_params.append(p)
            resolved_name = resolve_template_expr(kind['base']['value'], resolved_params)
            kind['base']['value'] = resolved_name
            kind['template_params'] = []

    def resolve_global_expr(decl, template_params: dict):
        resolved_decl = copy.deepcopy(decl)
        if resolved_decl['type'] == 'clazz_decl':
            for t in resolved_decl['types']:
                resolve_type(t['kind'], template_params)
        elif resolved_decl['type'] == 'func_decl':
            resolve_type(resolved_decl['kind'], template_params)
            resolve_inner(resolved_decl['parameters'], template_params)
            resolve_inner(resolved_decl['body'], template_params)
        return resolved_decl

    def resolve_template_expr(name: str, resolved_params: list):
        template_decl: dict = template_decls[name]
        template_params = {}
        for p, v in zip(template_decl['template_params'], resolved_params):
            assert p['type'] == 'placeholder'
            template_params[p['value']] = v
        resolved_params_str = []
        for rp in resolved_params:
            if rp.get('type') == 'placeholder':
                resolved_params_str.append(template_params[rp['value']])
            elif rp.get('type') == 'integer':
                resolved_params_str.append(str(rp['value']))
            else:
                assert not rp['template_params']
                base = rp['base']
                assert base['type'] == 'identifier'
                resolved_params_str.append(base['value'])
        full_name = "_".join([name] + resolved_params_str)
        if full_name in resolved_template_functions:
            return full_name
        resolved_template_functions[full_name] = {'type': 'partial_resolved_template'}
        res = resolve_global_expr(template_decl, template_params)
        res['identifier'] = full_name
        resolved_template_functions[full_name] = res
        return full_name

    result = []
    for _decl in nontemplate_decls:
        result.append(resolve_global_expr(_decl, {}))
    return result + list(resolved_template_functions.values())


def parse_with_imports_resolution(filepath: str) -> tuple[list, str]:
    parsed_text = recursive_parse(filepath)
    resolved_parsed_text = resolve_templates(parsed_text)
    formatted_text = Formatter().format(resolved_parsed_text)
    print(formatted_text)
    return Parser().parse_program(formatted_text, after_template_resolution=True), formatted_text
