# coding=utf-8
import struct
from io import BytesIO


class NetPacket(object):
    __slots__ = ('size', 'type', 'time', 'raw_data', 'index')
    _counter = 0

    def __init__(self, stream):
        type(self)._counter += 1
        self.index = type(self)._counter

        self.size, = struct.unpack('I', stream.read(4))
        self.type, = struct.unpack('I', stream.read(4))
        self.time, = struct.unpack('f', stream.read(4))

        self.raw_data = BytesIO(stream.read(self.size))

    def __repr__(self):
        return "TIME: {} TYPE: {} SIZE: {} DATA: {}".format(
            self.time, hex(self.type), self.size, self.raw_data)
