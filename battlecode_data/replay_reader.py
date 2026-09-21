"""Read UNSWBC 0.3.5 packed Cap'n Proto replays; no third-party packages.

Wire offsets are taken from the official replay viewer shipped in unswbc 0.3.5.
This is a bounded reader for this replay schema, not a general Cap'n Proto API.
"""
from pathlib import Path
import struct

MAX_BYTES = 256 * 1024 * 1024


def unpack(data):
    out = bytearray()
    p = 0
    while p < len(data):
        tag = data[p]
        p += 1
        word = bytearray(8)
        for i in range(8):
            if tag & (1 << i):
                if p >= len(data):
                    raise ValueError("Truncated packed replay")
                word[i] = data[p]
                p += 1
        out.extend(word)
        if tag in (0, 255):
            if p >= len(data):
                raise ValueError("Missing packed run length")
            n = data[p] * 8
            p += 1
            if tag == 0:
                out.extend(bytes(n))
            else:
                if p + n > len(data):
                    raise ValueError("Truncated literal run")
                out.extend(data[p:p+n])
                p += n
        if len(out) > MAX_BYTES:
            raise ValueError("Unpacked replay exceeds 256 MiB")
    return out


class Message:
    def __init__(self, packed):
        data = unpack(packed)
        if len(data) < 8:
            raise ValueError("Replay has no segment table")
        count = struct.unpack_from('<I', data)[0] + 1
        if count > 4096 or 4 + 4*count > len(data):
            raise ValueError("Invalid segment table")
        sizes = struct.unpack_from('<' + 'I'*count, data, 4)
        p = ((count+2)//2)*8
        self.segments = []
        for words in sizes:
            end = p + 8*words
            if end > len(data):
                raise ValueError("Truncated segment")
            self.segments.append(memoryview(data)[p:end])
            p = end
        if p != len(data):
            raise ValueError("Unexpected trailing replay data")

    def read(self, seg, offset, size):
        if not 0 <= seg < len(self.segments):
            raise ValueError("Bad segment reference")
        data = self.segments[seg]
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError("Replay pointer is out of bounds")
        return data[offset:offset+size]

    def word(self, seg, offset):
        return struct.unpack('<Q', self.read(seg, offset, 8))[0]

    def pointer(self, seg, offset, depth=0):
        if depth > 8:
            raise ValueError("Pointer nesting limit")
        value = self.word(seg, offset)
        if not value:
            return None
        if value & 3 == 2:
            landing_seg = value >> 32
            landing = ((value >> 3) & ((1 << 29)-1))*8
            if value & 4:
                far = self.word(landing_seg, landing)
                tag = self.word(landing_seg, landing+8)
                if far & 7 != 2:
                    raise ValueError("Invalid double-far pointer")
                return far >> 32, ((far >> 3) & ((1 << 29)-1))*8, tag
            return self.pointer(landing_seg, landing, depth+1)
        if value & 3 not in (0, 1):
            raise ValueError("Unsupported pointer type")
        relative = (value >> 2) & ((1 << 30)-1)
        if relative & (1 << 29):
            relative -= 1 << 30
        return seg, offset+8+8*relative, value


class Record:
    def __init__(self, message, resolved):
        self.message = message
        if resolved is None:
            self.seg, self.offset, self.words, self.pointers = 0, 0, 0, 0
        else:
            self.seg, self.offset, tag = resolved
            if tag & 3:
                raise ValueError("Expected struct")
            self.words = (tag >> 32) & 65535
            self.pointers = tag >> 48
            message.read(self.seg, self.offset, (self.words+self.pointers)*8)

    def number(self, offset, fmt):
        size = struct.calcsize(fmt)
        if offset + size > self.words*8:
            return 0
        return struct.unpack(fmt, self.message.read(self.seg, self.offset+offset, size))[0]

    def ptr(self, index):
        if index >= self.pointers:
            return None
        return self.message.pointer(self.seg, self.offset+8*(self.words+index))

    def child(self, index):
        return Record(self.message, self.ptr(index))

    def list_data(self, index, expected):
        p = self.ptr(index)
        if p is None:
            return None, 0
        seg, offset, tag = p
        if tag & 3 != 1 or ((tag >> 32) & 7) != expected:
            raise ValueError("Unexpected list encoding")
        count = tag >> 35
        size = count * (8 if expected == 7 else {2: 1, 3: 2}[expected])
        self.message.read(seg, offset, size + (8 if expected == 7 else 0))
        return (seg, offset), count

    def text(self, index):
        p, size = self.list_data(index, 2)
        if p is None:
            return ''
        data = bytes(self.message.read(*p, size))
        if not data.endswith(b'\0'):
            raise ValueError("Text is not null-terminated")
        return data[:-1].decode('utf-8')

    def enums(self, index):
        p, size = self.list_data(index, 3)
        if p is None:
            return []
        return list(struct.unpack('<'+'H'*size, self.message.read(*p, size*2)))

    def records(self, index):
        p, words = self.list_data(index, 7)
        if p is None:
            return
        seg, offset = p
        tag = self.message.word(seg, offset)
        if tag & 3:
            raise ValueError("Bad struct-list tag")
        count = (tag >> 2) & ((1 << 30)-1)
        stride = ((tag >> 32) & 65535) + (tag >> 48)
        if count*stride > words or count > 2_000_000:
            raise ValueError("Bad struct-list size")
        for i in range(count):
            yield Record(self.message, (seg, offset+8+i*stride*8, tag & ~0xffffffff))


NAMES = ['roundStart', 'turnStart', 'pearlCountdown', 'tileChange',
         'dragonAction', 'engineLog', 'dragonLog', 'dragonIndicator',
         'debugDraw', 'dragonUpdate', 'dragonSplit', 'dragonDeath', 'sonarPing']
REASONS = ['hitWall', 'hitSelf', 'hitOtherBody', 'hitHeadToHead', 'noValidAction']


def enum(values, index):
    if not 0 <= index < len(values):
        raise ValueError("Unknown enum value; replay format may have changed")
    return values[index]


def point(r):
    return [r.number(0, '<i'), r.number(4, '<i')]


def action(r):
    kind = r.number(0, '<H')
    if kind == 0:
        return {'kind': 'move', 'steps': ''.join(enum('NESW', d) for d in r.enums(0))}
    if kind == 1:
        return {'kind': 'split', 'child_length': r.number(4, '<i')}
    if kind == 2:
        return {'kind': 'suicide'}
    raise ValueError('Unknown action')


def event(r):
    kind = r.number(0, '<H')
    e = {'type': enum(NAMES, kind)}
    v = r.child(0)
    if kind == 0:
        e['round'] = v.number(0, '<i')
    elif kind in (1, 4, 5, 6, 7, 8, 9, 11):
        e['id'] = v.number(0, '<i')
        if kind == 4:
            e['action'] = action(v.child(0))
        elif kind in (5, 6, 7):
            e['text'] = v.text(0)
        elif kind == 9:
            e.update(facing=enum('NESW', v.number(4, '<H')),
                     head=point(v.child(0)), tail=point(v.child(1)))
        elif kind == 11:
            e['reason'] = enum(REASONS, v.number(4, '<H'))
        # Debug drawings are intentionally omitted from learning data.
    elif kind in (2, 3):
        e['tile'] = point(v.child(0))
        if kind == 2:
            e['countdown'] = v.number(0, '<i')
        else:
            e['has_pearl'] = bool(v.number(0, '<B') & 1)
    elif kind == 10:
        e.update(parent_id=v.number(0, '<i'), child_id=v.number(4, '<i'),
                 team=enum('AB', v.number(8, '<H')),
                 facing=enum('NESW', v.number(10, '<H')),
                 parent_body=[point(p) for p in v.records(0)],
                 child_body=[point(p) for p in v.records(1)])
    elif kind == 12:
        e.update(sender_id=v.number(0, '<i'), value=v.number(8, '<I'),
                 direction=enum('NESW', v.number(4, '<H')),
                 origin=point(v.child(0)), end=point(v.child(1)),
                 hit_id=v.number(12, '<i') if v.number(6, '<H') == 1 else None)
    return e


def standing(r):
    return dict(zip(['dragon_count', 'longest_dragon', 'total_length'],
                    [r.number(i, '<i') for i in (0, 4, 8)]))


def load_replay(path):
    path = Path(path)
    if path.stat().st_size > 64*1024*1024:
        raise ValueError('Replay exceeds 64 MiB packed limit')
    msg = Message(path.read_bytes())
    root = Record(msg, msg.pointer(0, 0))
    r = root.child(4)
    result = {'terminated': bool(r.number(0, '<B') & 1),
              'winner': enum('AB', r.number(6, '<H')) if r.number(4, '<H') == 1 else None,
              'end_reason': enum(['teamEliminated', 'roundLimit'], r.number(2, '<H')),
              'A': standing(r.child(0)), 'B': standing(r.child(1))}
    map_text = root.text(0)
    if not map_text.startswith('MAP '):
        raise ValueError('Replay has no supported MAP header')
    return {'map': map_text, 'bot_A': root.text(1), 'bot_B': root.text(2),
            'result': result, 'events': (event(v) for v in root.records(3))}
