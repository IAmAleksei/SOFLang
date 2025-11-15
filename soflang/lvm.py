from typing import List, Callable

from soflang.asm import ExecutionContext, Instruction, ExitI
from soflang.binarify import decode_binary_asm


class LionVM:
    def __init__(self):
        self.stack_size = 300
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
