from typing import List

from arch.logic import Number8, Number32, Number64, ONE32, ZERO64, ZERO32, FOUR32, FIVE32, THREE32, TWO32, ZERO8, \
    num32_from_int


class FurMemory:
    def __init__(self, board: 'Bearboard', size=512 * 4):
        self.size = size
        self.array: List[Number8] = [Number8([False] * 8) for _ in range(self.size)]
        self.board = board

    def read8(self, idx: Number32) -> Number8:
        return self.array[idx.to_int()]

    def read32(self, idx: Number32) -> Number32:
        return Number32([
            self.read8(idx),
            self.read8(idx + ONE32),
            self.read8(idx + TWO32),
            self.read8(idx + THREE32),
        ])

    def write8(self, idx: Number32, value: Number8):
        self.array[idx.to_int()] = value

    def write32(self, idx: Number32, value: Number32):
        self.write8(idx, value.array[0])
        self.write8(idx + ONE32, value.array[1])
        self.write8(idx + TWO32, value.array[2])
        self.write8(idx + THREE32, value.array[3])


# TODO: cache L1/L2/L3
class HoneyProcessingUnit:
    def __init__(self, board: 'Bearboard'):
        self.ip: Number32 = ZERO32
        self.reg0: Number32 = ZERO32
        self.reg1: Number32 = ZERO32
        self.reg2: Number32 = ZERO32
        self.reg3: Number32 = ZERO32
        self.reg4: Number32 = ZERO32
        self.reg5: Number32 = ZERO32
        self.ir: Number64 = ZERO64
        self.sp: Number32 = ZERO32
        self.board: Bearboard = board

    def cycle(self):
        self.fetch()
        self.decode()
        self.execute()

    def fetch(self):
        # Read 5 bytes
        self.reg0 = self.ip
        self.read()
        self.reg3 = self.reg2

        self.reg1 = ONE32
        self.add()
        self.reg0 = self.reg2
        self.read32()
        self.ir = Number64([
            self.reg3.array[3],
            self.reg2.array[0],
            self.reg2.array[1],
            self.reg2.array[2],
            self.reg2.array[3],
            ZERO8,
            ZERO8,
            ZERO8,
        ])

    def decode(self):
        if self.ir.array[0] == Number8([False, False, True, True, False, True, False, True]):
            # PUSH
            self.reg0 = Number32([self.ir.array[1], self.ir.array[2], self.ir.array[3], self.ir.array[4]])
        elif self.ir.array[0] == Number8([False, False, True, True, False, True, True, False]):
            # POP
            self.reg0 = Number32([ZERO8, ZERO8, ZERO8, self.ir.array[1]])
        elif self.ir.array[0] == Number8([False, False, True, True, False, True, True, True]):
            # STORE
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])
        elif self.ir.array[0] == Number8([False, False, True, True, True, False, False, True]):
            # LOAD
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])
        elif self.ir.array[0] == Number8([False, False, True, True, True, False, True, True]):
            # JUMP
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])
            self.reg0 = self.reg0.extend_from_num16()
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, False, False]):
            # JUMP0
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, False, True]):
            # JUMPA
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, True, False]):
            # DUMP
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])
        elif self.ir.array[0] == Number8([False, True, False, False, False, False, False, False]):
            # ALLOC
            self.reg0 = Number32([ZERO8, ZERO8, self.ir.array[1], self.ir.array[2]])

    def read_two_args_from_ram(self):
        self.dec_sp(FOUR32)
        self.reg0 = self.sp
        self.read32()
        self.reg3 = self.reg2

        self.dec_sp(FOUR32)
        self.reg0 = self.sp
        self.read32()
        self.reg0 = self.reg2
        self.reg1 = self.reg3

    def execute(self):
        if self.ir.array[0] == Number8([False, False, True, True, False, False, False, False]):
            # ADD
            self.read_two_args_from_ram()
            self.add()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, False, False, True]):
            # SUB
            self.read_two_args_from_ram()
            self.sub()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, False, True, False]):
            # MUL
            self.read_two_args_from_ram()
            self.mul()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, False, True, True]):
            # DIV
            self.read_two_args_from_ram()
            self.div()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, True, False, False]):
            # INV
            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()
            self.reg0 = self.reg2
            if self.is_zero():
                self.reg1 = ONE32
            else:
                self.reg1 = ZERO32
            self.reg0 = self.sp
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, True, False, True]):
            # PUSH
            self.reg1 = self.reg0
            self.reg0 = self.sp
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(FIVE32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, True, True, False]):
            # POP
            self.reg1 = FOUR32
            self.mul()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.sub()
            self.sp = self.reg2
            self.inc_ip(TWO32)
        elif self.ir.array[0] == Number8([False, False, True, True, False, True, True, True]):
            # STORE
            self.reg1 = ONE32
            self.add()

            self.reg0 = FOUR32
            self.reg1 = self.reg2
            self.mul()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.sub()
            self.reg3 = self.reg2

            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()

            self.reg0 = self.reg3
            self.reg1 = self.reg2
            self.write32()
            self.inc_ip(THREE32)
        elif self.ir.array[0] == Number8([False, False, True, True, True, False, False, False]):
            # DSTORE
            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()

            self.reg0 = FOUR32
            self.reg1 = self.reg2
            self.mul()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.sub()
            self.reg3 = self.reg2

            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()

            self.reg0 = self.reg3
            self.reg1 = self.reg2
            self.write32()
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, True, False, False, True]):
            # LOAD
            self.reg1 = ONE32
            self.add()

            self.reg0 = FOUR32
            self.reg1 = self.reg2
            self.mul()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.sub()

            self.reg0 = self.reg2
            self.read32()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)

            self.inc_ip(THREE32)
        elif self.ir.array[0] == Number8([False, False, True, True, True, False, True, False]):
            # DLOAD
            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()

            self.reg0 = FOUR32
            self.reg1 = self.reg2
            self.mul()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.sub()

            self.reg0 = self.reg2
            self.read32()
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, False, True, True, True, False, True, True]):
            # JUMP
            self.reg1 = self.ip
            self.add()
            self.ip = self.reg2
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, False, False]):
            # JUMP0
            self.reg3 = self.reg0
            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()
            self.reg0 = self.reg2
            if self.is_zero():
                self.reg0 = self.ip
                self.reg1 = self.reg3
                self.add()
                self.ip = self.reg2
            else:
                self.inc_ip(THREE32)
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, False, True]):
            # JUMPA
            self.ip = self.reg0
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, True, False]):
            # DUMP
            self.reg1 = self.ip
            self.add()
            self.reg1 = self.reg2
            self.reg0 = self.sp
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(THREE32)
        elif self.ir.array[0] == Number8([False, False, True, True, True, True, True, True]):
            # RETURN
            self.dec_sp(FOUR32)
            self.reg0 = self.sp
            self.read32()
            self.ip = self.reg2
        elif self.ir.array[0] == Number8([False, True, False, False, False, False, False, False]):
            # ALLOC
            while True:
                if self.is_zero():
                    break
                self.reg3 = self.reg0
                self.reg0 = self.sp
                self.reg1 = ZERO32
                self.write32()
                self.inc_sp(FOUR32)
                self.reg0 = self.reg3
                self.reg1 = ONE32
                self.sub()
                self.reg0 = self.reg2
            self.inc_ip(THREE32)
        elif self.ir.array[0] == Number8([False, True, False, False, False, False, False, True]):
            # CRASH
            raise ValueError("The program has crashed. Only Sofa knows why...")
        elif self.ir.array[0] == Number8([False, True, False, False, False, False, True, False]):
            # NOOP
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([False, True, False, False, False, False, True, True]):
            # LESS
            self.read_two_args_from_ram()
            if self.reg0 < self.reg1:
                self.reg2 = ONE32
            else:
                self.reg2 = ZERO32
            self.reg0 = self.sp
            self.reg1 = self.reg2
            self.write32()
            self.inc_sp(FOUR32)
            self.inc_ip(ONE32)
        elif self.ir.array[0] == Number8([True, True, True, True, True, True, True, True]):
            raise ValueError("The program has reached the end")
        else:
            raise ValueError(f"Unsupported instruction: {self.ir.array[0]}")

    def add(self):
        self.reg2 = self.reg0 + self.reg1

    def sub(self):
        self.reg2 = self.reg0 - self.reg1

    def mul(self):
        self.reg2 = self.reg0 * self.reg1

    def div(self):
        self.reg2 = self.reg0 / self.reg1

    def less(self):
        self.reg2 = self.reg0 < self.reg1

    def is_zero(self):
        return self.reg0 == ZERO32

    def inc_ip(self, value):
        self.reg0 = self.ip
        self.reg1 = value
        self.add()
        self.ip = self.reg2

    def inc_sp(self, value):
        self.reg0 = self.sp
        self.reg1 = value
        self.add()
        self.sp = self.reg2

    def dec_sp(self, value):
        self.reg0 = self.sp
        self.reg1 = value
        self.sub()
        self.sp = self.reg2

    def read(self):
        self.reg2 = Number32([ZERO8, ZERO8, ZERO8, self.board.read_ram8(self.reg0)])

    def read32(self):
        self.reg2 = self.board.read_ram32(self.reg0)

    def write(self):
        self.board.write_ram8(self.reg0, self.reg1.array[3])

    def write32(self):
        self.board.write_ram32(self.reg0, self.reg1)


class Bearboard:
    def __init__(self):
        self.memory = FurMemory(self, size=64 * 1024)
        self.cpu = HoneyProcessingUnit(self)
        self.stack_start = ZERO32

    def read_ram8(self, idx: Number32) -> Number8:
        return self.memory.read8(idx)

    def read_ram32(self, idx: Number32) -> Number32:
        return self.memory.read32(idx)

    def write_ram8(self, idx: Number32, value: Number8):
        self.memory.write8(idx, value)

    def write_ram32(self, idx: Number32, value: Number32):
        self.memory.write32(idx, value)

    def load_program(self, instructions: List[Number8]):
        total_instructions = len(instructions)
        for i in range(total_instructions):
            self.memory.write8(num32_from_int(i), instructions[i])
        self.stack_start = num32_from_int(total_instructions + (4 - total_instructions % 4) + 200 * 4)
        self.cpu.sp = self.stack_start

    def step_program(self):
        self.cpu.fetch()
        self.cpu.decode()
        self.cpu.execute()
