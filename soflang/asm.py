from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from soflang.analyzer import (
    Function,
    Statement, VariableDeclaration, Assignment,
    IfExpression, WhileExpression,
    Atom, GeneralExpr, IntegerLiteral, IdentifierExpr, FunctionCall, ArrayIndex, UnaryExpr, Class, FieldAccess,
    ConstructorCall, Throwable, VarDeclWithAssign
)
from soflang.asm_ops import *


@dataclass
class TranslationResult:
    asm_instructions: List[Instruction]
    source_code_lines: List[int]
    variable_allocations: Dict[int, tuple[str, int]]


def translate(functions: List[Function], classes: Dict[str, Class], with_debug: bool = False) -> TranslationResult:
    all_functions = {func.name: func for func in functions}
    function_starts = {'main': 0}
    result = TranslationResult(asm_instructions=[], source_code_lines=[], variable_allocations={})

    def run_translation(func_name, instr_shift):
        subtranslator = SingleFunctionTinyTranslator(all_functions, classes)
        subtranslator.parse_function(all_functions[func_name])
        result.asm_instructions.extend(subtranslator.result)
        if with_debug:
            result.source_code_lines.extend(subtranslator.source_code_lines)
            for idx, info in subtranslator.variable_allocations.items():
                result.variable_allocations[idx + instr_shift] = info

    run_translation('main', 0)
    for func in functions:
        if func.name == 'main':
            continue
        instr_shift = len(result.asm_instructions)
        function_starts[func.name] = instr_shift
        run_translation(func.name, instr_shift)
    for i in range(len(result.asm_instructions)):
        instr = result.asm_instructions[i]
        if isinstance(instr, TempJumpAI):
            result.asm_instructions[i] = JumpAI(function_starts[instr.f])
    return result


class SingleFunctionTinyTranslator:
    def __init__(self, all_functions: Dict[str, Function], classes: Dict[str, Class]):
        self.result: List[Instruction] = []
        self.var_stack_positions: Dict[str, int] = {}
        self.var_stack_sizes: Dict[str, int] = {}
        self.var_classes: Dict[str, str] = {}
        self.stack_pos = -1
        self.all_functions = all_functions
        self.all_classes = classes
        self.cached_class_sizes: Dict[str, int] = {'Num': 1}
        self.cur_line = -1
        self.source_code_lines: List[int] = []
        self.variable_allocations: Dict[int, tuple[str, int]] = {}

    def calculate_space(self, str_type, array_size: Optional[int] = None):
        """Calculate space needed for a type. Returns 1 for simple types, array_size for arrays."""
        cnt = 1 if array_size is None else array_size
        if str_type not in self.cached_class_sizes:
            sz = 0
            for field in self.all_classes[str_type].fields:
                sz += self.calculate_space(field.class_type, field.array_size)
            self.cached_class_sizes[str_type] = sz
        return cnt * self.cached_class_sizes[str_type]

    def save_instr(self, instr: Instruction):
        self.result.append(instr)
        self.source_code_lines.append(self.cur_line)

    def calc_and_alloc(self, name, str_type, array_size):
        space = self.calculate_space(str_type, array_size)
        self.variable_allocations[len(self.result)] = (name, space)
        self.save_instr(AllocI(space))
        self.stack_pos += space
        return space

    # TODO: fix places where only single num are accepted
    def _parse_atom(self, atom: Atom):
        if isinstance(atom.value, IntegerLiteral):
            self.save_instr(PushI(atom.value.value))
            self.stack_pos += 1
        elif isinstance(atom.value, IdentifierExpr):
            self._load_var_on_stack(atom.value.name)
        elif isinstance(atom.value, ArrayIndex):
            element_sz = self.calculate_space(self.var_classes[atom.value.var_name])
            if isinstance(atom.value.index, int):
                for i in range(element_sz):
                    array_start = self.stack_pos - self.var_stack_positions[atom.value.var_name]
                    self.save_instr(LoadI(array_start - atom.value.index * element_sz - i))
                    self.stack_pos += 1
            elif isinstance(atom.value.index, str):
                for i in range(element_sz):
                    array_start = self.stack_pos - self.var_stack_positions[atom.value.var_name]
                    # Points to array start + 1
                    self.save_instr(PushI(array_start + 1 - i))
                    # Points to array start
                    self.stack_pos += 1
                    self._load_var_on_stack(atom.value.index)
                    self.save_instr(PushI(element_sz))
                    self.stack_pos += 1
                    self.save_instr(MulI())
                    self.stack_pos -= 1
                    # Points to array start - 1 and shift
                    self.save_instr(SubI())
                    # Contains array start - shift
                    self.stack_pos -= 1
                    self.save_instr(DLoadI())
        elif isinstance(atom.value, FunctionCall):
            called_func = self.all_functions[atom.value.name]
            self.calc_and_alloc(f"{called_func.name}_res", called_func.return_class_type, called_func.return_array_size)
            dump_pos = len(self.result)
            self.save_instr(Error())
            self.stack_pos += 1
            allocated_stack = 0
            for param, var_name in zip(called_func.parameters, atom.value.parameters):
                sz = self._load_var_on_stack(var_name)
                allocated_stack += sz
                self.variable_allocations[len(self.result) - 1] = (param.name, sz)
            self.save_instr(TempJumpAI(called_func.name))
            after_jump_pos = len(self.result)
            self.result[dump_pos] = DumpI(after_jump_pos - dump_pos)
            self.stack_pos -= 1 + allocated_stack  # The memory will be clean by callee.
        elif isinstance(atom.value, FieldAccess):
            shift = 0
            var_start_pos = self.var_stack_positions[atom.value.var_name]
            for field in self.all_classes[self.var_classes[atom.value.var_name]].fields:
                if field.name == atom.value.field:
                    sz = self.calculate_space(field.class_type, field.array_size)
                    for i in range(sz):
                        self.save_instr(LoadI(self.stack_pos - var_start_pos - shift - i))
                        self.stack_pos += 1
                    break
                else:
                    shift += self.calculate_space(field.class_type, field.array_size)
        elif isinstance(atom.value, ConstructorCall):
            for param in atom.value.parameters:
                self._load_var_on_stack(param)
        else:
            raise ValueError()

    def _clean_stack(self, vars):
        for var in vars:
            size = self.var_stack_sizes.pop(var)
            self.var_classes.pop(var)
            self.var_stack_positions.pop(var)
            self.save_instr(PopI(size))
            self.stack_pos -= size

    def _load_var_on_stack(self, var_name: str):
        sz = self.var_stack_sizes[var_name]
        for i in range(sz):
            self.save_instr(LoadI(self.stack_pos - self.var_stack_positions[var_name] - i))
            self.stack_pos += 1
        return sz

    def _parse_expr(self, expr: Union[Atom, GeneralExpr, UnaryExpr]):
        if isinstance(expr, Atom):
            self._parse_atom(expr)
        elif isinstance(expr, GeneralExpr):
            self._parse_expr(expr.left)
            self._parse_expr(expr.right)
            if expr.op == "+":
                self.save_instr(AddI())
            elif expr.op == "-":
                self.save_instr(SubI())
            elif expr.op == "*":
                self.save_instr(MulI())
            elif expr.op == "/":
                self.save_instr(DivI())
            else:
                raise ValueError()
            self.stack_pos -= 1
        elif isinstance(expr, UnaryExpr):
            self._parse_expr(expr.operand)
            if expr.op == "~":
                self.save_instr(InvI())
            else:
                raise ValueError()
        else:
            raise ValueError()

    def _parse_body(self, body: List[Statement]):
        local_vars = []
        for line in body:
            if line.line is not None:
                self.cur_line = line.line
            if isinstance(line, Assignment):
                self._parse_expr(line.value)
                if isinstance(line.target, str):
                    sz = self.var_stack_sizes[line.target]
                    for i in range(sz):
                        self.save_instr(StoreI(self.stack_pos - self.var_stack_positions[line.target] - (sz - 1 - i)))
                        self.stack_pos -= 1
                elif isinstance(line.target, ArrayIndex):
                    element_sz = self.calculate_space(self.var_classes[line.target.var_name])
                    if isinstance(line.target.index, int):
                        for i in range(element_sz):
                            array_start = self.stack_pos - self.var_stack_positions[line.target.var_name]
                            self.save_instr(StoreI(array_start - line.target.index * element_sz - (element_sz - 1 - i)))
                            self.stack_pos -= 1
                    elif isinstance(line.target.index, str):
                        for i in range(element_sz):
                            array_start = self.stack_pos - self.var_stack_positions[line.target.var_name]
                            self.save_instr(PushI(array_start + 1 - (element_sz - 1 - i)))
                            self.stack_pos += 1
                            self._load_var_on_stack(line.target.index)
                            self.save_instr(PushI(element_sz))
                            self.stack_pos += 1
                            self.save_instr(MulI())
                            self.stack_pos -= 1
                            self.save_instr(SubI())
                            self.stack_pos -= 1
                            self.save_instr(DStoreI())
                            self.stack_pos -= 2
                else:
                    raise ValueError()
            elif isinstance(line, VariableDeclaration):
                var = line.variable
                space = self.calc_and_alloc(var.name, var.class_type, var.array_size)
                self.var_stack_positions[var.name] = self.stack_pos - space + 1
                self.var_stack_sizes[var.name] = space
                self.var_classes[var.name] = var.class_type
                local_vars.append(var.name)
            elif isinstance(line, IfExpression):
                self._parse_expr(line.condition)
                jump_pos = len(self.result)
                self.save_instr(Jump0I(-1))
                self.stack_pos -= 1
                self._parse_body(line.body)
                after_body_pos = len(self.result)
                self.result[jump_pos] = Jump0I(after_body_pos - jump_pos)
            elif isinstance(line, WhileExpression):
                calc_pos = len(self.result)
                self._parse_expr(line.condition)
                jump_pos = len(self.result)
                self.save_instr(Jump0I(-1))
                self.stack_pos -= 1
                self._parse_body(line.body)
                after_body_pos = len(self.result)
                self.save_instr(JumpI(calc_pos - after_body_pos))
                after_body_and_jump_pos = len(self.result)
                self.result[jump_pos] = Jump0I(after_body_and_jump_pos - jump_pos)
            elif isinstance(line, Throwable):
                self.save_instr(CrashI())
            elif isinstance(line, VarDeclWithAssign):
                assert line.class_type is not None
                self._parse_expr(line.value)
                var = line
                space = self.calculate_space(var.class_type, var.array_size)
                self.var_stack_positions[var.name] = self.stack_pos - space + 1
                self.var_stack_sizes[var.name] = space
                self.var_classes[var.name] = var.class_type
                self.variable_allocations[len(self.result) - 1] = (var.name, space)
                local_vars.append(var.name)
            else:
                raise ValueError()

        self._clean_stack(local_vars[::-1]) # Clean in a reverse order

    def parse_function(self, function: Function):
        if self.result:
            raise ValueError()

        result_size = self.calculate_space(function.return_class_type, function.return_array_size)
        self.var_stack_positions['result'] = -1 - result_size
        self.var_stack_sizes['result'] = result_size
        self.var_classes['result'] = function.return_class_type
        for p in function.parameters:
            space = self.calculate_space(p.class_type, p.array_size)
            self.var_stack_positions[p.name] = self.stack_pos + 1
            self.var_stack_sizes[p.name] = space
            self.var_classes[p.name] = p.class_type
            self.stack_pos += space
        self._parse_body(function.body)
        self._clean_stack(p.name for p in function.parameters)
        if function.name == 'main':
            self.save_instr(ExitI())
        else:
            self.save_instr(ReturnI())
