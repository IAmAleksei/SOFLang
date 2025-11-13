from typing import List

from soflang.asm import ExecutionContext, Instruction, ExitI


class LionVM:
    def __init__(self):
        self.stack_size = 300
        self.max_result = 20
        assert self.stack_size > self.max_result

    def run(self, instructions: List[Instruction]):
        ec = ExecutionContext([0] * self.stack_size, self.max_result, 0)
        steps = 0
        while True:
            steps += 1
            i = instructions[ec.ip]
            if isinstance(i, ExitI):
                break
            else:
                i.apply(ec)
        final_stack = [chr(s) for s in ec.stack]
        print(*final_stack, sep="")
        print(f"Steps: {steps}")
