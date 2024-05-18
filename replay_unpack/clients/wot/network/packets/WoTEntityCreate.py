# coding=utf-8
import struct
import logging

from replay_unpack.core.entity_def.data_types import FixedDict

from replay_unpack.core import PrettyPrintObjectMixin
from replay_unpack.core.network.types import BinaryStream
from replay_unpack.core.network.types import Vector3
from replay_unpack.clients.wot.helper import get_definitions, get_controller
from replay_unpack.core import (
    Entity
)

class WoTEntityCreate(PrettyPrintObjectMixin):
    def __init__(self, stream, player=None, rawdata=None):
        nowpos = stream.tell()
        if rawdata is None:
            self.rawdata = stream.read()
            stream.seek(nowpos)
        else:
            self.rawdata = rawdata

        self.entityID, = struct.unpack('i', stream.read(4))
        self.type, = struct.unpack('h', stream.read(2))
        if self.type == 6:
            self.vehicleId, = struct.unpack('i', stream.read(4))
            self.spaceId, = struct.unpack('i', stream.read(4))
            self.unknown0, = struct.unpack('i', stream.read(4))
            self.position = Vector3(stream)
            self.direction = Vector3(stream)

            # TODO: what is it?
            self.unknown1, = struct.unpack('i', stream.read(4))
        elif player is not None:
            entity = Entity(
                id_=self.entityID,
                spec=player._definitions.get_entity_def_by_index(self.type))


