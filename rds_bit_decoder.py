from typing import Dict, List, Union, Optional
import numpy as np

from rds_constants import RDS


class RDSBitDecoder:

    """
    RDS Coding Structure
    http://www.interactive-radio-system.com/docs/EN50067_RDS_Standard.pdf

    Group
    <--- 104 bits                    --->
    +--------+--------+--------+--------+
    | B1     | B2     | B3     | B4     |
    +--------+--------+--------+--------+
      26b      26b      26b      26b

    Block
    <--- 26 bits            --->
    +----------------+----------+
    | Word           | Check    |
    +----------------+----------+
      16b              10b
    """

    def __init__(self, save_to_file: bool, file_name=None) -> None:
        self.program_id = ''
        self.program_type = ''
        self.radio_name = '_' * 8
        self.radio_text = '_' * 64
        self.bits = []
        self.save_to_file = save_to_file
        self.file_name = file_name
        self.first_write = True

        if not self.save_to_file:
            self.bits = RDSBitDecoder._read_array_from_file(self.file_name)
            self.decode(self.bits)

    def decode(self, bits: np.ndarray) -> None:
        my_hits = []
        self.bits = bits
        if self.save_to_file:
            if self.first_write:
                RDSBitDecoder._write_array_to_file(bits, self.file_name)
                self.first_write = False
            else:
                RDSBitDecoder._append_array_to_file(bits, self.file_name)

        for i in range(len(bits)-26):
            h = self._rds_syndrome(bits, i, 26)
            if h:
                my_hits.append((i, h))

        groups = RDS.find_rds_groups(bits)
        for group in groups:
            self._decode_rds_group(group)
            print(self.program_id, self.program_type,
                  self.radio_name, self.radio_text)

    def _decode_rds_group(self, group: Dict[str, int]):
        info = {}
        a_bits = []
        b_bits = []
        c_bits = []
        d_bits = []

        if 'A' in group:
            a_bits = self.bits[group['A']:group['A'] + RDS.BLK_SIZ]

            info.update(RDS._decode_block_a(a_bits))
            self.program_id = info['PID']

        if 'C' in group:
            c_bits = self.bits[group['C']:group['C'] + RDS.BLK_SIZ]

        if 'D' in group:
            d_bits = self.bits[group['D']:group['D'] + RDS.BLK_SIZ]

        if 'B' in group:
            b_bits = self.bits[group['B']:group['B'] + RDS.BLK_SIZ]

            info.update(RDS._decode_block_b(b_bits))
            self.program_type = RDS.get_program_type(info['PTY'])

            # 0A is 8 byte radio name
            if (info['GROUP_TYPE'] == '0'
                and info['VERSION'] == '0'
                    and 'D' in group):
                # which position
                # __ __ __ __
                # 0  1  2  3
                char_pos = RDS._bits_to_int(b_bits[14:]) * 2
                text = chr(RDS._bits_to_int(
                    d_bits[:8])) + chr(RDS._bits_to_int(d_bits[8:]))
                self.radio_name = self.radio_name[:char_pos] + \
                    text + self.radio_name[char_pos+2:]

            # 2A is 64 byte radio text
            if (info['GROUP_TYPE'] == '2'
                and info['VERSION'] == '0'
                    and 'D' in group):
                # clear screen
                clear = b_bits[11] == 1
                if clear:
                    self.radio_text = '_' * 64

                # which position
                # ____ ____ ____ ____ ... ____
                # 0    1    2    3        63
                char_pos = RDS._bits_to_int(b_bits[12:]) * 4
                if 'C' in group:
                    text = chr(RDS._bits_to_int(
                        c_bits[:8])) + chr(RDS._bits_to_int(c_bits[8:]))
                    self.radio_text = self.radio_text[:char_pos] + \
                        text + self.radio_text[char_pos + 2:]

                if 'D' in group:
                    text = chr(RDS._bits_to_int(
                        d_bits[:8])) + chr(RDS._bits_to_int(d_bits[8:]))
                    self.radio_text = self.radio_text[:char_pos + 2] + \
                        text + self.radio_text[char_pos + 4:]

    def _rds_syndrome(self, message: List[int], m_offset: int, mlen: int) -> Optional[str]:
        """
        Calculates the syndrome of a given message and returns the corresponding
        offset name if it matches any syndrome.

        Args:
            message (List[int]): The message to calculate the syndrome for.
            m_offset (int): The offset of the message.
            mlen (int): The length of the message.

        Returns:
            Optional[str]: The offset name if the checkword matches any
            syndrome, otherwise None.

        Raises:
            ValueError: If the mlen is not equal to 16 or 26.
        """
        POLY = 0x5B9  # 10110111001, g(x)=x^10+x^8+x^7+x^5+x^4+x^3+1
        PLEN = 10
        SYNDROME = [383, 14, 303, 663, 748]
        OFFSET_NAME = ['A', 'B', 'C', 'D', 'C\'']
        reg = 0

        if mlen != 16 and mlen != 26:
            raise ValueError("mlen must be 16 or 26")

        # Start calculation
        for i in range(mlen):
            reg = (reg << 1) | message[m_offset + i]
            if reg & (1 << PLEN):
                reg = reg ^ POLY

        for i in range(PLEN, 0, -1):
            reg = reg << 1
            if reg & (1 << PLEN):
                reg = reg ^ POLY

        checkword = reg & ((1 << PLEN) - 1)

        # End calculation
        for i in range(5):
            if checkword == SYNDROME[i]:
                return OFFSET_NAME[i]

        return None

    def _write_array_to_file(array: List[int], filename: str) -> None:
        """
        Writes the elements of an array to a file. Each element is written on a
        new line.

        Args:
            array (List[int]): The array of integers to write to the file.
            filename (str): The name of the file to write the array to.

        Returns:
            None
        """
        with open(filename, 'w') as file:
            for num in array:
                file.write(str(num) + '\n')

    def _append_array_to_file(array: List[int], filename: str) -> None:
        """
        Appends the elements of an array to a file. Each element is appended on
        a new line.

        Args:
            array (List[int]): The array of integers to append to the file.
            filename (str): The name of the file to append the array to.

        Returns:
            None
        """
        with open(filename, 'a') as file:
            for num in array:
                file.write(str(num) + '\n')

    def _read_array_from_file(filename: str) -> List[int]:
        """
        Reads an array of integers from a file and returns it.

        Args:
            filename (str): The name of the file to read.

        Returns:
            List[int]: The array of integers read from the file.
        """
        bits = []
        with open(filename, 'r') as file:
            for line in file:
                bits.append(int(line.strip()))
        return bits
