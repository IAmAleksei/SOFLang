from typing import List, Callable

from arch.components import Lionboard
from arch.logic import num8_from_int, num32_from_int
from soflang.asm import ExecutionContext, Instruction, ExitI
from soflang.binarify import decode_binary_asm


class LionVM:
    def __init__(self):
        self.stack_size = 300 * 8
        self.max_result = 20
        assert self.stack_size > self.max_result

    def run_abstract(self, instruction_getter: Callable[[int], Instruction], binary_source: bool):
        ec = ExecutionContext([0] * self.stack_size, self.max_result, 0, binary_source)
        steps = 0
        while True:
            steps += 1
            i = instruction_getter(ec.ip)
            if isinstance(i, ExitI):
                break
            else:
                i.apply(ec)
        final_stack = [chr(s) for s in ec.stack]
        print(*final_stack, sep="")
        print(f"Steps: {steps}")

    def run(self, instructions: List[Instruction]):
        self.run_abstract(lambda x: instructions[x], binary_source=False)

    def run_binary(self, bs: bytes):
        self.run_abstract(lambda x: decode_binary_asm(bs, x), binary_source=True)

    def run_with_cpu_simulation(self, bs: bytes):
        board = Lionboard()
        board.load_program([num8_from_int(b) for b in bs])
        steps = 0
        try:
            while True:
                steps += 1
                board.step_program()
        except Exception as e:
            print("Exception", e)
        program_memory = [board.memory.read32(num32_from_int(i)) for i in range(0, board.stack_start.to_int(), 4)]
        final_stack = [board.memory.read32(num32_from_int(i)) for i in range(board.stack_start.to_int() - 16, board.memory.size, 4)]
        print("Program:", *program_memory, sep=" ")
        print("Stack:", *final_stack, sep=" ")
        print(f"Steps: {steps}")
