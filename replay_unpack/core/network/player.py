#!/usr/bin/python
# coding=utf-8
import logging
from abc import ABC
from io import BytesIO
import os
from .net_packet import NetPacket


class PlayerBase:
    def __init__(self, version: str):
        self._definitions = self._get_definitions(version)

        self._mapping = self._get_packets_mapping(version)

    def _get_definitions(self, version):
        raise NotImplementedError

    def _get_packets_mapping(self, version):
        raise NotImplementedError

    def _deserialize_packet(self, packet: NetPacket):
        if packet.type in self._mapping:
            return self._mapping[packet.type](packet.raw_data)
        logging.debug('[U] {:4.3f} type: 0x{:02X} size:{:4d}\t|{}'.format(packet.time, packet.type, packet.size, packet.raw_data.read().hex(' ')))
        return None

    def _process_packet(self, time, packet):
        raise NotImplementedError

    def play(self, replay_data, strict_mode=False, dumpfname=None):
        io = BytesIO(replay_data)
        dumpsplit = None
        if dumpfname is not None:
            dumpsplit = open(dumpfname, 'w')

        while io.tell() != len(replay_data):
            packet = NetPacket(io)

            state = "E"
            try:
                state = self._process_packet(packet.time, self._deserialize_packet(packet))
                if dumpfname is not None:
                    packet.raw_data.seek(0)
                    dumpsplit.write("{:6d}[{}] {:4.3f} type: 0x{:02X} size:{:4d}\t|{}\n".format(
                        packet.index, state, packet.time, packet.type, packet.size,
                        packet.raw_data.read().hex(" ")))
            except Exception:
                packet.raw_data.seek(0)
                logging.exception("{:6d}[{}] {:4.3f} type: 0x{:02X} size:{:4d}\t|{}\npacketClass: {}".format(
                    packet.index, state, packet.time, packet.type, packet.size, packet.raw_data.read().hex(" "),
                    self._mapping.get(packet.type)))
                packet.raw_data.seek(0)
                dumpsplit.write("{:6d}[{}] {:4.3f} type: 0x{:02X} size:{:4d}\t|{}\n".format(
                    packet.index, state, packet.time, packet.type, packet.size,
                    packet.raw_data.read().hex(" ")))
                if strict_mode and dumpfname is None:
                    raise


class ControlledPlayerBase(PlayerBase, ABC):
    def __init__(self, version: str):
        self._battle_controller = self._get_controller(version)

        super(ControlledPlayerBase, self).__init__(version)

    def _get_controller(self, version):
        raise NotImplementedError

    def get_info(self):
        return self._battle_controller.get_info()
