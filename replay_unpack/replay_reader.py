# coding=utf-8
import json
import os
import struct
import zlib
from io import BytesIO
from typing import NamedTuple
import logging

logging.basicConfig(level=logging.INFO)

from Cryptodome.Cipher import Blowfish

BASE_DIR = os.path.dirname(__file__)
WOWS_BLOWFISH_KEY = b''.join([b'\x29', b'\xB7', b'\xC9', b'\x09', b'\x38', b'\x3F', b'\x84', b'\x88',
                              b'\xFA', b'\x98', b'\xEC', b'\x4E', b'\x13', b'\x19', b'\x79', b'\xFB'])

WOWP_BLOWFISH_KEY = b''.join([b'\xDE', b'\x72', b'\xBE', b'\xEF', b'\xDE', b'\xAD', b'\xBE', b'\xEF',
                              b'\xDE', b'\xAD', b'\xBE', b'\xEF', b'\xDE', b'\xAD', b'\xBE', b'\xEF'])

WOT_BLOWFISH_KEY = b''.join([b'\xDE', b'\x72', b'\xBE', b'\xA0', b'\xDE', b'\x04', b'\xBE', b'\xB1',
                             b'\xDE', b'\xFE', b'\xBE', b'\xEF', b'\xDE', b'\xAD', b'\xBE', b'\xEF'])

REPLAY_SIGNATURE = b'\x12\x32\x34\x11'

WOWS_REPLAY = 'wowsreplay'
WOT_REPLAY = 'wotreplay'
WOWP_REPLAY = 'wowpreplay'
TYPE_TO_KEY = {
    'wowsreplay': WOWS_BLOWFISH_KEY,
    'wotreplay': WOT_BLOWFISH_KEY,
    'wowpreplay': WOWP_BLOWFISH_KEY
}
ALLOWED_TYPES = set(TYPE_TO_KEY.keys())

ReplayInfo = NamedTuple('ReplayInfo', [
    ('game', str),
    ('engine_data', dict),
    ('extra_data', list),
    ('decrypted_data', bytes),
])


class ReplayReader(object):
    """
    # Header
    Every replay starts off with an 8 byte header, consisting of the following values:

    magic number - An unsigned 32 bit integer (4 bytes)
    block count - An unsigned 32 bit integer (4 bytes)
    The block count is an indication of how many data blocks (excluding the real replay data) are stored inside the replay. For replays generated by a World of Tanks version before 0.8.1, the presence of 2 blocks means the replay is considered "complete", meaning it has the match start information, as well as a match result. Replays generated by 0.8.1 and later versions are guaranteed to be complete if there are 2 or more blocks present.

    # Blocks
    Every data block starts with an unsigned 32 bit integer that holds the length of the data for the given block. The first block consists of a JSON encoded structure. In versions before 0.8.1, the second block is also a JSON encoded structure.

    # Reading
    Open the replay file
    Seek to offset 4 in the replay file (skipping the magic number)
    Read 4 bytes, and interpret these as an unsigned 32 bit integer, let this be "block count"
    For every block take the following action:
    Read 4 bytes, and interpret these as an unsigned 32 bit integer, let this be "data length"
    Read "data length" bytes
    Once all blocks have been read, the remainder of the data in the file is the compressed and encrypted replay data

    See http://wiki.vbaddict.net/pages/File_Replays for more details;
    """

    def __init__(self, replay_path, dump_binary=False):
        self._dump_binary_data = dump_binary
        self._replay_path = replay_path
        self._check_replay_exists()

        self._type = self._replay_path.rsplit('.', 1)[-1]
        if self._type not in ALLOWED_TYPES:
            raise ValueError("Replay must be in following extensions: "
                             "%s" % ALLOWED_TYPES)

    def get_replay_data(self, is_compressed=True) -> ReplayInfo:
        """
        Get open info about replay 
        (stored as Json at the beginning of file) 
        and closed one
        (after decrypt & decompress);
        :rtype: tuple[dict, str]
        """
        with open(self._replay_path, 'rb') as f:
            if f.read(4) != REPLAY_SIGNATURE:
                raise ValueError("File %s is not a valid replay" % self._replay_path)

            blocks_count = struct.unpack("i", f.read(4))[0]

            block_size = struct.unpack("i", f.read(4))[0]

            # save part one block to local json file, overwritten if any
            engine_data = json.loads(f.read(block_size))
            try:
                replay_name = os.path.basename(self._replay_path)
                json_name = '{}.0.json'.format(replay_name)
                with open(json_name, 'w') as df:
                    json.dump(engine_data, df, indent=4)
            except IOError as e:
                logging.error('Cannot dump replay json to {}: {}'.format(json_name, e))

            extra_data = []
            for i in range(blocks_count - 1):
                block_size = struct.unpack("i", f.read(4))[0]
                block = f.read(block_size)

                if block:
                    try:
                        data = json.loads(block)
                        replay_name = os.path.basename(self._replay_path)
                        json_name = '{}.{}.json'.format(replay_name, i+1)
                        with open(json_name, 'w') as df:
                            json.dump(data, df, indent=4)
                    except IOError as e:
                        logging.error('Cannot dump extra replay json to {}: {}'.format(json_name, e))

                else:
                    data = None
                extra_data.append(data)

            if self._type == WOWS_REPLAY:
                game = 'wows'
            elif self._type == WOT_REPLAY:
                game = 'wot'
            elif self._type == WOWP_REPLAY:
                game = 'wowp'
            else:
                raise

            if is_compressed:
                decrypted = self.__decrypt_data(f.read())
                decrypted_data = zlib.decompress(decrypted)
            else:
                decrypted_data = f.read()

            if self._dump_binary_data:
                self._save_decrypted_data(decrypted_data)

            return ReplayInfo(
                game=game,
                engine_data=engine_data,
                extra_data=extra_data,
                decrypted_data=decrypted_data,
            )

    def _save_decrypted_data(self, decrypted_data):
        """
        Save decrypted data into file named as 
        given replay, but with '.hex' postfix;
        :type decrypted_data: bytes
        :raises ParserException
        """
        try:
            replay_name = os.path.basename(self._replay_path)
            with open('{}.hex'.format(replay_name), 'wb') as df:
                df.write(decrypted_data)
        except IOError as e:
            print('Cannot dump replay: {}'.format(e))

    def _check_replay_exists(self):
        """
        Check if replay really exists. 
        Raises ParserException otherwise. 
        """
        if not os.path.exists(self._replay_path):
            raise Exception("File does not exists: {}".format(self._replay_path))

    @staticmethod
    def __chunkify_string(string, length=8):
        """
        Split string into blocks with given max len.
        :type string: str
        :type length: int|long
        :rtype: tuple[int, str]
        """
        for i in range(0, len(string), length):
            yield i, string[0 + i:length + i]

    def __decrypt_data(self, dirty_data):
        previous_block = None  # type: str
        blowfish = Blowfish.new(TYPE_TO_KEY[self._type], Blowfish.MODE_ECB)
        decrypted_data = BytesIO()

        for index, chunk in self.__chunkify_string(dirty_data):
            # FIXME: what this chunk is used for??
            if index == 0:
                continue

            decrypted_block, = struct.unpack('q', blowfish.decrypt(chunk))
            if previous_block:
                # get two blocks, each 8 bytes long and xor them
                # then pack them back to bytes
                decrypted_block ^= previous_block
            previous_block = decrypted_block

            decrypted_data.write(struct.pack('q', decrypted_block))

        return decrypted_data.getvalue()
