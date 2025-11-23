from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ExecutionContext:
    stack: list[int]
    sp: int
    ip: int
    binary_source: bool

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

    def copy(self):
        return ExecutionContext(self.stack.copy(), self.sp, self.ip, self.binary_source)


def binarify_instruction(code, args: Optional[list[tuple[int, int]]] = None) -> list:
    args = args or []
    result = [code]
    for l, val in args:
        # The 1st bit is the sign. Other bits are used to encode the number.
        max_val = 1 << (8 * l - 1)
        assert abs(val) < max_val
        if val < 0:
            val = -val
            val |= max_val
        arg = []
        for _ in range(l):
            arg.append(val % 256)
            val //= 256
        result.extend(arg[::-1])
    return result


@dataclass
class Instruction:
    def __post_init__(self):
        self.bin_size = len(self.binarify() or [])

    def apply(self, ec: ExecutionContext):
        raise ValueError()

    def __str__(self):
        raise ValueError()

    def inc_ip(self, ec: ExecutionContext):
        ec.ip += self.bin_size if ec.binary_source else 1

    def binarify(self) -> List[int]:
        return None


@dataclass
class AddI(Instruction):
    def apply(self, ec: ExecutionContext):
        ec.push(ec.pop() + ec.pop())
        self.inc_ip(ec)

    def __str__(self):
        return f"ADD"

    def binarify(self):
        return binarify_instruction(48)

@dataclass
class SubI(Instruction):
    def apply(self, ec: ExecutionContext):
        b = ec.pop()
        ec.push(ec.pop() - b)
        self.inc_ip(ec)

    def __str__(self):
        return f"SUB"

    def binarify(self):
        return binarify_instruction(49)


@dataclass
class MulI(Instruction):
    def apply(self, ec: ExecutionContext):
        ec.push(ec.pop() * ec.pop())
        self.inc_ip(ec)

    def __str__(self):
        return f"MUL"

    def binarify(self):
        return binarify_instruction(50)


@dataclass
class DivI(Instruction):
    def apply(self, ec: ExecutionContext):
        b = ec.pop()
        ec.push(ec.pop() // b)
        self.inc_ip(ec)

    def __str__(self):
        return f"DIV"

    def binarify(self):
        return binarify_instruction(51)


@dataclass
class InvI(Instruction):
    def apply(self, ec: ExecutionContext):
        a = ec.pop()
        ec.push(0 if a != 0 else 1)
        self.inc_ip(ec)

    def __str__(self):
        return f"INV"

    def binarify(self):
        return binarify_instruction(52)


@dataclass
class PushI(Instruction):
    value: int

    def apply(self, ec: ExecutionContext):
        ec.push(self.value)
        self.inc_ip(ec)

    def __str__(self):
        return f"PUSH {self.value}"

    def binarify(self):
        return binarify_instruction(53, [(4, self.value)])


@dataclass
class PopI(Instruction):
    count: int

    def apply(self, ec: ExecutionContext):
        for _ in range(self.count):
            ec.pop()
        self.inc_ip(ec)

    def __str__(self):
        return f"POP {self.count}"

    def binarify(self):
        return binarify_instruction(54, [(1, self.count)])


@dataclass
class StoreI(Instruction):
    relative_position: int

    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - self.relative_position
        v = ec.pop()
        ec.store(dest_pos, v)
        self.inc_ip(ec)

    def __str__(self):
        return f"STORE {self.relative_position}"

    def binarify(self):
        return binarify_instruction(55, [(2, self.relative_position)])


@dataclass
class DStoreI(Instruction):
    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - ec.pop()
        v = ec.pop()
        ec.store(dest_pos, v)
        self.inc_ip(ec)

    def __str__(self):
        return f"DSTORE"

    def binarify(self):
        return binarify_instruction(56)


@dataclass
class LoadI(Instruction):
    relative_position: int

    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - self.relative_position
        ec.push(ec.stack[dest_pos])
        self.inc_ip(ec)

    def __str__(self):
        return f"LOAD {self.relative_position}"

    def binarify(self):
        return binarify_instruction(57, [(2, self.relative_position)])


@dataclass
class DLoadI(Instruction):
    def apply(self, ec: ExecutionContext):
        dest_pos = ec.sp - ec.pop()
        ec.push(ec.stack[dest_pos])
        self.inc_ip(ec)

    def __str__(self):
        return f"DLOAD"

    def binarify(self):
        return binarify_instruction(58)


@dataclass
class JumpI(Instruction):
    shift: int

    def apply(self, ec: ExecutionContext):
        ec.ip += self.shift

    def __str__(self):
        assert self.shift != 0
        return f"JUMP {self.shift}"

    def binarify(self):
        return binarify_instruction(59, [(2, self.shift)])


@dataclass
class Jump0I(Instruction):
    shift: int

    def apply(self, ec: ExecutionContext):
        v = ec.pop()
        if v == 0:
            ec.ip += self.shift
        else:
            self.inc_ip(ec)

    def __str__(self):
        return f"JUMP0 {self.shift}"

    def binarify(self):
        return binarify_instruction(60, [(2, self.shift)])


@dataclass
class JumpAI(Instruction):
    new_ip: int

    def apply(self, ec: ExecutionContext):
        ec.ip = self.new_ip

    def __str__(self):
        assert self.new_ip >= 0
        return f"JUMPA {self.new_ip}"

    def binarify(self):
        return binarify_instruction(61, [(2, self.new_ip)])


@dataclass
class TempJumpAI(Instruction):
    f: str

    def apply(self, ec: ExecutionContext):
        raise ValueError()

    def __str__(self):
        raise ValueError()


@dataclass
class DumpI(Instruction):
    shift: int

    def apply(self, ec: ExecutionContext):
        ec.push(ec.ip + self.shift)
        self.inc_ip(ec)

    def __str__(self):
        return f"DUMP {self.shift}"

    def binarify(self):
        return binarify_instruction(62, [(2, self.shift)])


@dataclass
class Error(Instruction):
    def apply(self, ec: ExecutionContext):
        raise ValueError()

    def __str__(self):
        raise ValueError()


@dataclass
class ReturnI(Instruction):
    def apply(self, ec: ExecutionContext):
        a = ec.pop()
        ec.ip = a

    def __str__(self):
        return f"RETURN"

    def binarify(self):
        return binarify_instruction(63)


@dataclass
class AllocI(Instruction):
    size: int

    def apply(self, ec: ExecutionContext):
        for _ in range(self.size):
            ec.push(0)
        self.inc_ip(ec)

    def __str__(self):
        return f"ALLOC {self.size}"

    def binarify(self):
        return binarify_instruction(64, [(2, self.size)])


@dataclass
class CrashI(Instruction):
    def apply(self, ec: ExecutionContext):
        raise ValueError("Crash")

    def __str__(self):
        return f"CRASH"

    def binarify(self):
        return binarify_instruction(65)


@dataclass
class NoOpI(Instruction):
    def apply(self, ec: ExecutionContext):
        self.inc_ip(ec)

    def __str__(self):
        return f"NOOP"

    def binarify(self):
        return binarify_instruction(66)


@dataclass
class LessI(Instruction):
    def apply(self, ec: ExecutionContext):
        b = ec.pop()
        ec.push(1 if ec.pop() < b else 0)
        self.inc_ip(ec)

    def __str__(self):
        return f"LESS"

    def binarify(self):
        return binarify_instruction(67)


class ExitI(Instruction):
    def apply(self, ec: ExecutionContext):
        raise ValueError()

    def __str__(self):
        return f"EXIT"

    def binarify(self):
        return binarify_instruction(255)


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
        elif opcode == "INV":
            result.append(InvI())
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
        elif opcode == "JUMPA":
            if len(args) != 1:
                raise ValueError(f"JUMPA expects 1 argument, got: {line}")
            result.append(JumpAI(int(args[0])))
        elif opcode == "ALLOC":
            if len(args) != 1:
                raise ValueError(f"ALLOC expects 1 argument, got: {line}")
            result.append(AllocI(int(args[0])))
        elif opcode == "DUMP":
            if len(args) != 1:
                raise ValueError(f"DUMP expects 1 argument, got: {line}")
            result.append(DumpI(int(args[0])))
        elif opcode == "RETURN":
            result.append(ReturnI())
        elif opcode == "CRASH":
            result.append(CrashI())
        elif opcode == "NOOP":
            result.append(NoOpI())
        elif opcode == "EXIT":
            result.append(ExitI())
        else:
            raise ValueError(f"Unsupported instruction: {line}")
    return result

