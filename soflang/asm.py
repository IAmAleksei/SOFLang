from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from soflang.analyzer import (
    Function, Variable, Type,
    AnalysisError, UndefinedVariableError, UndefinedFunctionError,
    TypeMismatchError, ArgumentCountError,
    Statement, VariableDeclaration, Assignment,
    IfExpression, WhileExpression,
    Atom, GeneralExpr, IntegerLiteral, IdentifierExpr, FunctionCall, ArrayIndex, UnaryExpr
)


@dataclass
class ExecutionContext:
    stack: List[int]
    sp: int
    ip: int

    def push(self, v):
        self.sp += 1
        self.stack[self.sp] = v

    def pop(self) -> int:
        res = self.stack[self.sp]
        self.stack[self.sp] = 0
        self.sp -= 1
        return res

    def store(self, i, v):
        self.stack[i] = v


class Instruction:
    def apply(self, ec: ExecutionContext):
        pass

    def __str__(self):
        pass


@dataclass
class AddI(Instruction):
    def apply(self, ec: ExecutionContext):
        ec.push(ec.pop() + ec.pop())
        ec.ip += 1

    def __str__(self):
        return f"ADD"


@dataclass
class SubI(Instruction):
    def apply(self, ec: ExecutionContext):
        b = ec.pop()
        ec.push(ec.pop() - b)
        ec.ip += 1

    def __str__(self):
        return f"SUB"


@dataclass
class MulI(Instruction):
    def apply(self, ec: ExecutionContext):
        ec.push(ec.pop() * ec.pop())
        ec.ip += 1

    def __str__(self):
        return f"MUL"


@dataclass
class DivI(Instruction):
    def apply(self, ec: ExecutionContext):
        b = ec.pop()
        ec.push(ec.pop() // b)
        ec.ip += 1

    def __str__(self):
        return f"DIV"


@dataclass
class InvI(Instruction):
    def apply(self, ec: ExecutionContext):
        a = ec.pop()
        ec.push(0 if a != 0 else 1)
        ec.ip += 1

    def __str__(self):
        return f"INV"


@dataclass
class PushI(Instruction):
    value: int

    def apply(self, ec: ExecutionContext):
        ec.push(self.value)
        ec.ip += 1

    def __str__(self):
        return f"PUSH {self.value}"


@dataclass
class PopI(Instruction):
    count: int

    def apply(self, ec: ExecutionContext):
        for _ in range(self.count):
            ec.pop()
        ec.ip += 1

    def __str__(self):
        return f"POP {self.count}"


@dataclass
class StoreI(Instruction):
    relative_position: int

    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - self.relative_position
        v = ec.pop()
        ec.store(dest_pos, v)
        ec.ip += 1

    def __str__(self):
        return f"STORE {self.relative_position}"


@dataclass
class DStoreI(Instruction):
    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - ec.pop()
        v = ec.pop()
        ec.store(dest_pos, v)
        ec.ip += 1

    def __str__(self):
        return f"DSTORE"


@dataclass
class LoadI(Instruction):
    relative_position: int

    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - self.relative_position
        ec.push(ec.stack[dest_pos])
        ec.ip += 1

    def __str__(self):
        return f"LOAD {self.relative_position}"


@dataclass
class DLoadI(Instruction):
    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - ec.pop()
        ec.push(ec.stack[dest_pos])
        ec.ip += 1

    def __str__(self):
        return f"DLOAD"


@dataclass
class JumpI(Instruction):
    shift: int

    def apply(self, ec: ExecutionContext):
        ec.ip += self.shift

    def __str__(self):
        assert self.shift != 0
        return f"JUMP {self.shift}"


@dataclass
class Jump0I(Instruction):
    shift: int

    def apply(self, ec: ExecutionContext):
        v = ec.pop()
        if v == 0:
            ec.ip += self.shift
        else:
            ec.ip += 1

    def __str__(self):
        return f"JUMP0 {self.shift}"


@dataclass
class JumpAI(Instruction):
    new_ip: int

    def apply(self, ec: ExecutionContext):
        ec.ip = self.new_ip

    def __str__(self):
        assert self.new_ip >= 0
        return f"JUMPA {self.new_ip}"


@dataclass
class TempJumpAI(Instruction):
    f: str

    def apply(self, ec: ExecutionContext):
        raise ValueError()

    def __str__(self):
        raise ValueError()


@dataclass
class DumpI(Instruction):
    def apply(self, ec: ExecutionContext):
        ec.push(ec.ip)
        ec.ip += 1

    def __str__(self):
        return f"DUMP"


@dataclass
class ReturnI(Instruction):
    def apply(self, ec: ExecutionContext):
        ec.ip = ec.pop() + 1

    def __str__(self):
        return f"RETURN"


@dataclass
class AllocI(Instruction):
    size: int

    def apply(self, ec: ExecutionContext):
        for _ in range(self.size):
            ec.push(0)
        ec.ip += 1

    def __str__(self):
        return f"ALLOC {self.size}"


class ExitI(Instruction):
    def __str__(self):
        return f"EXIT"


def calculate_space(type: Type, array_size: Optional[int]):
    return 1 if type == Type.NUM else array_size


class TinyTranslator:
    def translate(self, functions: List[Function]) -> List[Instruction]:
        all_functions = {func.name: func for func in functions}
        function_starts = {'main': 0}
        result = self.translate_one(all_functions['main'], all_functions)
        for func in functions:
            if func.name == 'main':
                continue
            function_starts[func.name] = len(result)
            result.extend(self.translate_one(func, all_functions))
        for i in range(len(result)):
            instr = result[i]
            if isinstance(instr, TempJumpAI):
                result[i] = JumpAI(function_starts[instr.f])
        return result

    def translate_one(self, function: Function, all_functions: Dict[str, Function]) -> List[Instruction]:
        return SingleFunctionTinyTranslator(all_functions).parse_function(function)


class SingleFunctionTinyTranslator:
    def __init__(self, all_functions: Dict[str, Function]):
        self.result: List[Instruction] = []
        self.var_stack_positions: Dict[str, int] = {}
        self.var_stack_sizes: Dict[str, int] = {}
        self.stack_pos = -1
        self.all_functions = all_functions

    def calc_and_alloc(self, type, array_size):
        space = calculate_space(type, array_size)
        self.result.append(AllocI(space))
        self.stack_pos += space
        return space

    def _parse_atom(self, atom: Atom):
        if isinstance(atom.value, IntegerLiteral):
            self.result.append(PushI(atom.value.value))
            self.stack_pos += 1
        elif isinstance(atom.value, IdentifierExpr):
            self._load_var_on_stack(atom.value.name)
        elif isinstance(atom.value, ArrayIndex):
            array_start = self.stack_pos - self.var_stack_positions[atom.value.var_name]
            if isinstance(atom.value.index, int):
                self.result.append(LoadI(array_start - atom.value.index))
                self.stack_pos += 1
            elif isinstance(atom.value.index, str):
                # Points to array start + 1
                self.result.append(PushI(array_start + 1))
                # Points to array start
                self.stack_pos += 1
                self._load_var_on_stack(atom.value.index)
                # Points to array start - 1 and shift
                self.result.append(SubI())
                # Contains array start - shift
                self.stack_pos -= 1
                self.result.append(DLoadI())
        elif isinstance(atom.value, FunctionCall):
            called_func = self.all_functions[atom.value.name]
            self.calc_and_alloc(called_func.return_type, called_func.return_array_size)
            self.result.append(DumpI())
            self.stack_pos += 1
            for param in atom.value.parameters:
                self._load_var_on_stack(param)
            self.result.append(TempJumpAI(called_func.name))
        else:
            raise ValueError()

    def _clean_stack(self, vars):
        stack_cleaning_size = sum(self.var_stack_sizes[var] for var in vars)
        if stack_cleaning_size > 0:
            self.result.append(PopI(stack_cleaning_size))
            self.stack_pos -= stack_cleaning_size

    def _load_var_on_stack(self, var_name: str):
        sz = self.var_stack_sizes[var_name]
        for i in range(sz):
            self.result.append(LoadI(self.stack_pos - self.var_stack_positions[var_name] - i))
            self.stack_pos += 1

    def _parse_expr(self, expr: Union[Atom, GeneralExpr, UnaryExpr]):
        if isinstance(expr, Atom):
            self._parse_atom(expr)
        elif isinstance(expr, GeneralExpr):
            self._parse_expr(expr.left)
            self._parse_expr(expr.right)
            if expr.op == "+":
                self.result.append(AddI())
            elif expr.op == "-":
                self.result.append(SubI())
            elif expr.op == "*":
                self.result.append(MulI())
            elif expr.op == "/":
                self.result.append(DivI())
            else:
                raise ValueError()
            self.stack_pos -= 1
        elif isinstance(expr, UnaryExpr):
            self._parse_expr(expr.operand)
            if expr.op == "~":
                self.result.append(InvI())
            else:
                raise ValueError()
        else:
            raise ValueError()

    def _parse_body(self, body: List[Statement]):
        local_vars = set()
        for line in body:
            if isinstance(line, Assignment):
                self._parse_expr(line.value)
                if isinstance(line.target, str):
                    sz = self.var_stack_sizes[line.target]
                    for i in range(sz):
                        self.result.append(StoreI(self.stack_pos - self.var_stack_positions[line.target] - (sz - 1 - i)))
                        self.stack_pos -= 1
                elif isinstance(line.target, ArrayIndex):
                    array_start = self.stack_pos - self.var_stack_positions[line.target.var_name]
                    if isinstance(line.target.index, int):
                        self.result.append(StoreI(array_start - line.target.index))
                        self.stack_pos -= 1
                    elif isinstance(line.target.index, str):
                        self.result.append(PushI(array_start + 1))
                        self.stack_pos += 1
                        self._load_var_on_stack(line.target.index)
                        self.result.append(SubI())
                        self.stack_pos -= 1
                        self.result.append(DStoreI())
                        self.stack_pos -= 2
                else:
                    raise ValueError()
            elif isinstance(line, VariableDeclaration):
                var = line.variable
                space = self.calc_and_alloc(var.type, var.array_size)
                self.var_stack_positions[var.name] = self.stack_pos - space + 1
                self.var_stack_sizes[var.name] = space
                local_vars.add(var.name)
            elif isinstance(line, IfExpression):
                self._parse_expr(line.condition)
                jump_pos = len(self.result)
                self.result.append(Jump0I(-1))
                self.stack_pos -= 1
                self._parse_body(line.body)
                after_body_pos = len(self.result)
                self.result[jump_pos] = Jump0I(after_body_pos - jump_pos)
            elif isinstance(line, WhileExpression):
                calc_pos = len(self.result)
                self._parse_expr(line.condition)
                jump_pos = len(self.result)
                self.result.append(Jump0I(-1))
                self.stack_pos -= 1
                self._parse_body(line.body)
                after_body_pos = len(self.result)
                self.result.append(JumpI(calc_pos - after_body_pos))
                after_body_and_jump_pos = len(self.result)
                self.result[jump_pos] = Jump0I(after_body_and_jump_pos - jump_pos)

        self._clean_stack(local_vars)

    def parse_function(self, function: Function) -> List[Instruction]:
        if self.result:
            raise ValueError()

        result_size = calculate_space(function.return_type, function.return_array_size)
        self.var_stack_positions['result'] = -1 - result_size
        self.var_stack_sizes['result'] = result_size
        for p in function.parameters:
            space = calculate_space(p.type, p.array_size)
            self.var_stack_positions[p.name] = self.stack_pos - space + 1
            self.var_stack_sizes[p.name] = space
            self.stack_pos += space
        self._parse_body(function.body)
        self._clean_stack(p.name for p in function.parameters)
        if function.name == 'main':
            self.result.append(ExitI())
        else:
            self.result.append(ReturnI())
        return self.result


def parse_asm(lines) -> List[Instruction]:
    result = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        opcode, *args = line.split()
        opcode = opcode.upper()
        if opcode == "ADD":
            result.append(AddI())
        elif opcode == "SUB":
            result.append(SubI())
        elif opcode == "MUL":
            result.append(MulI())
        elif opcode == "DIV":
            result.append(DivI())
        elif opcode == "PUSH":
            if len(args) != 1:
                raise ValueError(f"PUSH expects 1 argument, got: {line}")
            result.append(PushI(int(args[0])))
        elif opcode == "POP":
            if len(args) != 1:
                raise ValueError(f"POP expects 1 argument, got: {line}")
            result.append(PopI(int(args[0])))
        elif opcode == "STORE":
            if len(args) != 1:
                raise ValueError(f"STORE expects 1 argument, got: {line}")
            result.append(StoreI(int(args[0])))
        elif opcode == "DSTORE":
            result.append(DStoreI())
        elif opcode == "LOAD":
            if len(args) != 1:
                raise ValueError(f"LOAD expects 1 argument, got: {line}")
            result.append(LoadI(int(args[0])))
        elif opcode == "DLOAD":
            result.append(DLoadI())
        elif opcode == "JUMP":
            if len(args) != 1:
                raise ValueError(f"JUMP expects 1 argument, got: {line}")
            result.append(JumpI(int(args[0])))
        elif opcode == "JUMP0":
            if len(args) != 1:
                raise ValueError(f"JUMP0 expects 1 argument, got: {line}")
            result.append(Jump0I(int(args[0])))
        elif opcode == "ALLOC":
            if len(args) != 1:
                raise ValueError(f"ALLOC expects 1 argument, got: {line}")
            result.append(AllocI(int(args[0])))
        elif opcode == "EXIT":
            result.append(ExitI())
        else:
            raise ValueError(f"Unsupported instruction: {line}")
    return result
