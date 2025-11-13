from dataclasses import dataclass


@dataclass
class ExecutionContext:
    stack: list[int]
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

    def copy(self):
        return ExecutionContext(self.stack.copy(), self.sp, self.ip)


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
    shift: int

    def apply(self, ec: ExecutionContext):
        ec.push(ec.ip + self.shift)
        ec.ip += 1

    def __str__(self):
        return f"DUMP {self.shift}"


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
    def apply(self, ec: ExecutionContext):
        raise ValueError()

    def __str__(self):
        return f"EXIT"
