from typing import List, Tuple


class Number8:
    def __init__(self, value: List[bool]):
        assert len(value) == 8
        self.array = value

    def copy(self):
        return Number8([b for b in self.array])

    def clear(self):
        for i in range(8):
            self.array[i] = False

    def __eq__(self, other):
        return self.comp(other) == 0

    def add(self, other, tmp=False) -> Tuple['Number8', bool]:
        res = ZERO8()
        for i in range(7, -1, -1):
            res.array[i] = (self.array[i] and not other.array[i] and not tmp) or (
                        not self.array[i] and other.array[i] and not tmp) or (
                                       not self.array[i] and not other.array[i] and tmp) or (
                                       self.array[i] and other.array[i] and tmp)
            tmp = (self.array[i] and other.array[i]) or (self.array[i] and tmp) or (other.array[i] and tmp)
        return res, tmp

    def inv(self):
        res = ZERO8()
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

    def __getitem__(self, item):
        return self.array[item]

    def __setitem__(self, key, value):
        self.array[key] = value


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

    def copy(self):
        return type(self)([b.copy() for b in self.array])

    def clear(self):
        for i in range(self.length):
            self.array[i] = ZERO8()

    def __eq__(self, other):
        for i in range(self.length):
            if self.array[i] != other.array[i]:
                return False
        return True

    def __add__(self, other):
        res = ZERO32()
        tmp = False
        for i in range(self.length - 1, -1, -1):
            res.array[i], tmp = self.array[i].add(other.array[i], tmp)
        assert num32_from_int(self.to_int() + other.to_int()) == res
        return res

    def __neg__(self):
        res = ZERO32()
        for i in range(self.length - 1, -1, -1):
            res.array[i] = self.array[i].inv()
        res = res + ONE32()
        assert num32_from_int(-self.to_int()) == res
        return res

    def __sub__(self, other):
        res = self + (-other)
        assert num32_from_int(self.to_int() - other.to_int()) == res
        return res

    def __mul__(self, other):
        res = ZERO32()
        for i in range(0, 8 * self.length):
            res = res << 1
            if other[i]:
                res = res + self
        assert num32_from_int(self.to_int() * other.to_int()) == res
        return res

    def __truediv__(self, other):
        a = self
        b = other
        neg_result = a[0] ^ b[0]
        if a[0]:
            a = -a
            assert not a[0]
        if b[0]:
            b = -b
            assert not b[0]
        highest_bit = -1
        for i in range(self.length * 8):
            if b[i]:
                highest_bit = i
                break
        if highest_bit == -1:
            raise RuntimeError("Division by zero")
        res = ZERO32()
        for shift in range(highest_bit - 1, -1, -1):
            res = res << 1
            shifted = other << shift
            if not (a < shifted):
                a = a - shifted
                res = res + ONE32()
        if neg_result:
            return -res
        else:
            return res

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
        block_idx = item // 8
        inner_idx = item % 8
        return self.array[block_idx][inner_idx]

    def __setitem__(self, key, value):
        block_idx = key // 8
        inner_idx = key % 8
        self.array[block_idx][inner_idx] = value

    def __lshift__(self, sz):
        res = ZERO32()
        for i in range(self.length * 8 - sz):
            res[i] = self[i + sz]
        return res

    def extend_from_num16(self):
        if self[self.length * 8 - 16]:
            self.array[0] = MAX8()
            self.array[1] = MAX8()

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


def ZERO8():
    return Number8([False, False, False, False, False, False, False, False])


def ONE8():
    return Number8([False, False, False, False, False, False, False, True])


def TWO8():
    return Number8([False, False, False, False, False, False, True, False])


def THREE8():
    return Number8([False, False, False, False, False, False, True, True])


def FOUR8():
    return Number8([False, False, False, False, False, True, False, False])


def FIVE8():
    return Number8([False, False, False, False, False, True, False, True])


def MAX8():
    return Number8([True, True, True, True, True, True, True, True])


def ZERO32():
    return Number32([ZERO8(), ZERO8(), ZERO8(), ZERO8()])


def ONE32():
    return Number32([ZERO8(), ZERO8(), ZERO8(), ONE8()])


def TWO32():
    return Number32([ZERO8(), ZERO8(), ZERO8(), TWO8()])


def THREE32():
    return Number32([ZERO8(), ZERO8(), ZERO8(), THREE8()])


def FOUR32():
    return Number32([ZERO8(), ZERO8(), ZERO8(), FOUR8()])


def FIVE32():
    return Number32([ZERO8(), ZERO8(), ZERO8(), FIVE8()])


def ZERO64():
    return Number64([ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8()])


def ONE64():
    return Number64([ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8(), ZERO8(), ONE8()])
