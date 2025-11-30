from dataclasses import dataclass
from typing import List, Callable

from arch.components import Bearboard
from arch.logic import num8_from_int, num32_from_int
from soflang.asm import ExecutionContext, TranslationResult
from soflang.binarify import encode_binary_asm


@dataclass
class VarDebugInfo:
    name: str
    start_sp: int
    size: int

    def format(self, value_getter: Callable[[int], int], spacing: int):
        if self.size == 1:
            v = value_getter(self.start_sp)
        else:
            v = [value_getter(self.start_sp + i * spacing) for i in range(self.size)]
        return f"{self.name} = {v}"


class AbstractFoxbugger:
    spacing = 1

    def __init__(self, compiled_code_with_debug_info: TranslationResult, source_code: List[str]):
        self.steps = 0
        self.instructions = compiled_code_with_debug_info.asm_instructions
        self.debug_info = compiled_code_with_debug_info
        self.cur_line = self.debug_info.source_code_lines[0]
        self.source_code = source_code
        self.vars: List[VarDebugInfo] = []

    def get_cur_sp(self) -> int:
        raise ValueError("not implemented")

    def make_step(self):
        raise ValueError("not implemented")

    def forward(self):
        self.steps += 1
        cur_ip = self.get_cur_ip()
        self.make_step()
        if cur_ip in self.debug_info.variable_allocations:
            var_name, var_size = self.debug_info.variable_allocations[cur_ip]
            self.vars.append(VarDebugInfo(var_name, self.get_cur_sp() - (var_size - 1) * self.spacing, var_size))
        while len(self.vars) > 0 and self.get_cur_sp() < self.vars[-1].start_sp:
            self.vars.pop()
        self.cur_line = self.debug_info.source_code_lines[self.get_cur_ip()]

    def get_cur_ip(self) -> int:
        raise ValueError("not implemented")

    def load_stack_value(self, idx) -> int:
        raise ValueError("not implemented")

    def print_state(self):
        stack_end = self.get_cur_sp() + 1
        stack_start = max(stack_end - 40 * self.spacing - 1, 0)
        print()
        shown_values = [self.load_stack_value(i) for i in range(stack_start, stack_end, self.spacing)]
        print(f"-----------------------------------------------------------{stack_end}")
        print(f"| {' '.join(map(str, shown_values[::-1]))}")
        print("--------------------------------------------------------------")
        if self.cur_line >= 0:
            code_line = self.source_code[self.cur_line].strip()
            print(code_line)
            print("-" * len(code_line))
        for v in self.vars:
            print(v.format(self.load_stack_value, self.spacing))
        print()
        cur_ip = self.get_cur_ip()
        asm_prefix = f"{cur_ip + 1}"
        shift_str = " " * (len(asm_prefix) + 3)
        if cur_ip - 1 >= 0:
            print(shift_str + str(self.instructions[cur_ip - 1]))
        print(f"{asm_prefix} > {str(self.instructions[cur_ip])}")
        if cur_ip + 1 < len(self.instructions):
            print(shift_str + str(self.instructions[cur_ip + 1]))
        print()


class FoxbuggerSimple(AbstractFoxbugger):
    def __init__(self, compiled_code_with_debug_info: TranslationResult, source_code: List[str]):
        super().__init__(compiled_code_with_debug_info, source_code)
        self.ec = ExecutionContext([0] * 1200, 20, 0, binary_source=False)

    def get_cur_sp(self):
        return self.ec.sp

    def make_step(self):
        self.instructions[self.get_cur_ip()].apply(self.ec)

    def get_cur_ip(self):
        return self.ec.ip

    def load_stack_value(self, idx):
        return self.ec.load_num(idx)


class FoxbuggerWithHPU(AbstractFoxbugger):
    spacing = 4

    def __init__(self, compiled_code_with_debug_info: TranslationResult, source_code: List[str]):
        super().__init__(compiled_code_with_debug_info, source_code)
        self.board = Bearboard()
        bs, self.instruction_mapping = encode_binary_asm(compiled_code_with_debug_info.asm_instructions)
        self.board.load_program([num8_from_int(b) for b in bs])

    def get_cur_sp(self):
        return self.board.cpu.sp.to_int() - self.spacing

    def make_step(self):
        self.board.step_program()

    def get_cur_ip(self):
        return self.instruction_mapping[self.board.cpu.ip.to_int()]

    def load_stack_value(self, idx):
        return self.board.memory.read32(num32_from_int(idx)).to_int()


def run_debugger(debugger: AbstractFoxbugger):
    debugger.print_state()
    try:
        while True:
            i = input()
            if i == "":
                debugger.forward()
            elif i == "l":
                start_line = debugger.cur_line
                while debugger.cur_line == start_line:
                    debugger.forward()
            elif i == "f":
                while True:
                    debugger.forward()
            debugger.print_state()
    except Exception as e:
        print(f"Exception: {e}")
        debugger.print_state()
