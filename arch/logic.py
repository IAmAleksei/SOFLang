from typing import List, Tuple


class Number8:
    def __init__(self, value: List[bool]):
        assert len(value) == 8
        self.array = value

    def __eq__(self, other):
        return self.comp(other) == 0

    def add(self, other, tmp=False) -> Tuple['Number8', bool]:
        res = ZERO8M()
        for i in range(7, -1, -1):
            res.array[i] = (self.array[i] and not other.array[i] and not tmp) or (
                        not self.array[i] and other.array[i] and not tmp) or (
                                       not self.array[i] and not other.array[i] and tmp) or (
                                       self.array[i] and other.array[i] and tmp)
            tmp = (self.array[i] and other.array[i]) or (self.array[i] and tmp) or (other.array[i] and tmp)
        return res, tmp

    def inv(self):
        res = ZERO8M()
        for i in range(8):
            res.array[i] = not self.array[i]
        return res

    def comp(self, other):
        for i in range(8):
            if self.array[i] < other.array[i]:
                return -1
            elif self.array[i] > other.array[i]:
                return 1
        return 0

    def to_int(self):
        res = 0
        for b in self.array:
            res = res << 1
            if b:
                res += 1
        return res

    def __str__(self):
        return str(self.to_int())


def num8_from_int(v):
    res = []
    for i in range(8):
        res.append(v % 2 == 1)
        v //= 2
    return Number8(res[::-1])


class AbstractNumber:
    length = 0

    def __init__(self, value: List[Number8]):
        assert len(value) == self.length
        self.array = value

    def get_zero(self):
        return type(self)([ZERO8M() for _ in range(self.length)])

    def __eq__(self, other):
        for i in range(self.length):
            if self.array[i] != other.array[i]:
                return False
        return True

    def __add__(self, other):
        res = self.get_zero()
        tmp = False
        for i in range(self.length - 1, -1, -1):
            res.array[i], tmp = self.array[i].add(other.array[i], tmp)
        return res

    def __neg__(self):
        res = self.get_zero()
        for i in range(self.length - 1, -1, -1):
            res.array[i] = self.array[i].inv()
        return res + ONE32

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        res = self.get_zero()
        for i in range(8 * self.length):
            res = res << 1
            if other[i]:
                res = res + self
        return res

    def __truediv__(self, other):
        a = self
        b = other
        if a[0]:
            a = -a
            assert not a[0]
        if b[0]:
            b = -b
            assert not b[0]
        highest_bit = next((i for i in range(self.length * 8) if b[i]), -1)
        if highest_bit == -1:
            raise RuntimeError("Division by zero")
        res = self.get_zero()
        for shift in range(highest_bit - 1, -1, -1):
            res = res << 1
            shifted = b << shift
            if not (a < shifted):
                a = a - shifted
                res = res + ONE32
        if self[0] == other[0]:
            return res
        else:
            return -res

    def __lt__(self, other):
        if self == other:
            return False
        if self[0] != other[0]:
            return self[0]
        if self[0]:
            return (-other) < (-self)
        for i in range(self.length):
            cmp = self.array[i].comp(other.array[i])
            if cmp != 0:
                return cmp < 0
        return False

    def __getitem__(self, item):
        return self.array[item // 8].array[item % 8]

    def __lshift__(self, sz):
        res = self.get_zero()
        for i in range(self.length * 8 - sz):
            res.array[i // 8].array[i % 8] = self[i + sz]
        return res

    def extend_from_num16(self):
        res = self.get_zero()
        for i in range(self.length - 2, self.length):
            res.array[i] = self.array[i]
        if res[self.length * 8 - 16]:
            for i in range(self.length - 2):
                res.array[i] = MAX8
        return res

    def to_int(self):
        res = 0
        for b in self.array:
            res = (res << 8) + b.to_int()
        max_val = 1 << (8 * self.length - 1)
        if res >= max_val:
            res = res - 2 * max_val
        return res

    def __str__(self):
        return str(self.to_int())


class Number64(AbstractNumber):
    length = 8


class Number32(AbstractNumber):
    length = 4


def num32_from_int(v):
    res = []
    for i in range(4):
        res.append(num8_from_int(v % 256))
        v //= 256
    return Number32(res[::-1])


def ZERO8M():
    return Number8([False, False, False, False, False, False, False, False])


ZERO8 = Number8([False, False, False, False, False, False, False, False])
ONE8 = Number8([False, False, False, False, False, False, False, True])
TWO8 = Number8([False, False, False, False, False, False, True, False])
THREE8 = Number8([False, False, False, False, False, False, True, True])
FOUR8 = Number8([False, False, False, False, False, True, False, False])
FIVE8 = Number8([False, False, False, False, False, True, False, True])
MAX8 = Number8([True, True, True, True, True, True, True, True])


ZERO32 = Number32([ZERO8, ZERO8, ZERO8, ZERO8])
ONE32 = Number32([ZERO8, ZERO8, ZERO8, ONE8])
TWO32 = Number32([ZERO8, ZERO8, ZERO8, TWO8])
THREE32 = Number32([ZERO8, ZERO8, ZERO8, THREE8])
FOUR32 = Number32([ZERO8, ZERO8, ZERO8, FOUR8])
FIVE32 = Number32([ZERO8, ZERO8, ZERO8, FIVE8])
ZERO64 = Number64([ZERO8, ZERO8, ZERO8, ZERO8, ZERO8, ZERO8, ZERO8, ZERO8])

