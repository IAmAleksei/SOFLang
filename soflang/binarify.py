from typing import List, Tuple

from soflang.asm_ops import *


def encode_binary_asm(instructions: List[Instruction]) -> Tuple[bytes, dict]:
    prefix_shift = [0]
    for i in instructions:
        prefix_shift.append(prefix_shift[-1] + len(i.binarify()))
    bs = []
    starts = {}
    for i in range(len(instructions)):
        starts[len(bs)] = i
        fixed_instr = instructions[i]
        # Corrects ip jumps to align with byte positions.
        if isinstance(fixed_instr, JumpI):
            fixed_instr = JumpI(prefix_shift[i + fixed_instr.shift] - prefix_shift[i])
        elif isinstance(fixed_instr, Jump0I):
            fixed_instr = Jump0I(prefix_shift[i + fixed_instr.shift] - prefix_shift[i])
        elif isinstance(fixed_instr, JumpAI):
            fixed_instr = JumpAI(prefix_shift[fixed_instr.new_ip])
        elif isinstance(fixed_instr, DumpI):
            fixed_instr = DumpI(prefix_shift[i + fixed_instr.shift] - prefix_shift[i])
        bs.extend(fixed_instr.binarify())
    return bytes(bs), starts


def decode_binary_value(bs: bytes, idx, l) -> int:
    val = 0
    for b in range(idx, idx + l):
        val = 256 * val + bs[b]
    return unsigned_to_signed(val, l)


def decode_binary_asm(bytes: bytes, idx) -> Instruction:
    opcode = bytes[idx]
    if opcode == 48:
        return AddI()
    elif opcode == 49:
        return SubI()
    elif opcode == 50:
        return MulI()
    elif opcode == 51:
        return DivI()
    elif opcode == 52:
        return InvI()
    elif opcode == 53:
        return PushI(decode_binary_value(bytes, idx + 1, 4))
    elif opcode == 54:
        return PopI(decode_binary_value(bytes, idx + 1, 1))
    elif opcode == 55:
        return StoreI(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 56:
        return DStoreI()
    elif opcode == 57:
        return LoadI(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 58:
        return DLoadI()
    elif opcode == 59:
        return JumpI(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 60:
        return Jump0I(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 61:
        return JumpAI(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 62:
        return DumpI(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 63:
        return ReturnI()
    elif opcode == 64:
        return AllocI(decode_binary_value(bytes, idx + 1, 2))
    elif opcode == 65:
        return CrashI()
    elif opcode == 66:
        return NoOpI()
    elif opcode == 67:
        return LessI()
    elif opcode == 255:
        return ExitI()
    else:
        raise ValueError(f"Unsupported instruction: {bytes[idx]}")
