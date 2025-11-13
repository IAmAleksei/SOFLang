from dataclasses import dataclass
from typing import List

from soflang.asm import ExecutionContext, ExitI, TranslationResult
from soflang.asm_ops import AllocI, PopI


@dataclass
class VarDebugInfo:
    name: str
    start_sp: int
    size: int

    def format(self, ec: ExecutionContext):
        if self.size == 1:
            v = ec.stack[self.start_sp]
        else:
            v = ec.stack[self.start_sp:self.start_sp + self.size]
        return f"{self.name} = {v}"


class Debugger:
    def __init__(self, compiled_code_with_debug_info: TranslationResult, source_code: List[str]):
        self.history: List[ExecutionContext] = []
        self.ec = ExecutionContext([0] * 300, 20, 0)
        self.steps = 0
        self.instructions = compiled_code_with_debug_info.asm_instructions
        self.debug_info = compiled_code_with_debug_info
        self.cur_line = self.debug_info.source_code_lines[0]
        self.source_code = source_code
        self.vars: List[VarDebugInfo] = []

    # def back(self):
    #     self.steps += 1
    #     if len(self.history) > 0:
    #         self.ec = self.history.pop()

    def forward(self):
        self.steps += 1
        cur_ip = self.ec.ip
        i = self.instructions[cur_ip]
        if not isinstance(i, ExitI):
            self.history.append(self.ec.copy())
            i.apply(self.ec)
            if isinstance(i, AllocI):
                assert cur_ip in self.debug_info.variable_allocations
                self.vars.append(
                    VarDebugInfo(self.debug_info.variable_allocations[cur_ip], self.ec.sp - i.size + 1, i.size)
                )
            elif isinstance(i, PopI):
                self.vars.pop()
            self.cur_line = self.debug_info.source_code_lines[self.ec.ip]

    def print_state(self):
        stack_end = self.ec.sp + 1
        stack_start = stack_end - 20
        print()
        print(f"-----------------------------------------------------------{stack_end}")
        print(f"| {' '.join(map(str, self.ec.stack[stack_start:stack_end:][::-1]))}")
        print("--------------------------------------------------------------")
        if self.cur_line >= 0:
            code_line = self.source_code[self.cur_line].strip()
            print(code_line)
            print("-" * len(code_line))
        for v in self.vars:
            print(v.format(self.ec))
        print()
        asm_prefix = f"{self.ec.ip + 1}"
        shift_str = " " * (len(asm_prefix) + 3)
        if self.ec.ip - 1 >= 0:
            print(shift_str + str(self.instructions[self.ec.ip - 1]))
        print(f"{asm_prefix} > {str(self.instructions[self.ec.ip])}")
        if self.ec.ip + 1 < len(self.instructions):
            print(shift_str + str(self.instructions[self.ec.ip + 1]))
        print()


def move_forward(debugger):
    debugger.forward()
    debugger.print_state()


def run_debugger(compiled_code_with_debug_info: TranslationResult, source_code: list[str]):
    debugger = Debugger(compiled_code_with_debug_info, source_code)
    debugger.print_state()
    while True:
        input()
        move_forward(debugger)
