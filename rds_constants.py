from typing import Dict, List, Union, Tuple, Optional


class RDS:

    BLK_SIZ = 16

    PTY_CODES = {
        '': 'None',
        '0': 'None',
        '1': 'News',
        '2': 'Current Affairs',
        '3': 'Information',
        '4': 'Sport',
        '5': 'Education',
        '6': 'Drama',
        '7': 'Culture',
        '8': 'Science',
        '9': 'Varied',
        '10': 'Pop Music',
        '11': 'Rock Music',
        '12': 'Easy Music',
        '13': 'Light Classical',
        '14': 'Seriously Classical',
        '15': 'Other Music',
        '16': 'Weather',
        '17': 'Finance',
        '18': 'Children',
        '19': 'Social Affairs',
        '20': 'Religion',
        '21': 'Phone In',
        '22': 'Travel',
        '23': 'Leisure',
        '24': 'Jazz Music',
        '25': 'Country Music',
        '26': 'National Music',
        '27': 'Oldies Music',
        '28': 'Folk Music',
        '29': 'Documentary',
        '30': 'Alarm Test',
        '31': 'Alarm'
    }

    BLOCK_TYPES = ['A', 'B', 'C', 'D']

    def find_rds_groups(bits: List[Union[bool, int]]) -> List[Dict[str, int]]:
        """
        Finds RDS groups in a given list of bits.

        Args:
            bits (List[Union[bool, int]]): List of bits representing the RDS
            data.

        Returns:
            List[Dict[str, int]]: List of tuples containing the
            starting bit position and the RDS group information.
        """
        groups = []
        for bit_pos in range(len(bits) - 104):
            group = {}
            for block_i in range(4):
                block_type = RDS._rds_syndrome(bits, bit_pos, 26)
                if block_type == RDS.BLOCK_TYPES[block_i]:
                    group.update({block_type: bit_pos})
                bit_pos += 26
            if len(group) > 1:
                groups.append(group)
        return groups

    def get_program_type(code: str) -> str:
        """
        Get the program type for an RDS PTY code

        Args:
            code (str): the code to conver, must be either '' or in [0, 31]

        Raises:
            ValueError: If the code is not a valid option

        Returns:
            str: the program type or None if the code is blank or default
        """
        if code != '' and (int(code) < 0 or int(code) > 31):
            raise ValueError('Bad Code')
        return RDS.PTY_CODES[code]

    def _decode_block_a(bits: List[int]) -> Dict[str, str]:
        """
        Decodes Block A of RDS data.

        Args:
            bits (List[int]): Array of bits representing Block A.

        Returns:
            Dict[str, str]: Decoded Block A data with 'PID' as the key and
            the hexadecimal representation as the value.
        """
        return {'PID': RDS._bits_to_hex(bits)}

    def _decode_block_b(bits: List[int]) -> Dict[str, str]:
        """
        Decodes Block B of RDS data.

        Args:
            bits (List[int]): Array of bits representing Block B.

        Returns:
            Dict[str, str]: Decoded Block B data with keys and their corresponding values.
        """
        # | 4b  | 1b  | 1b      | 5b    | 5b   |
        #  Type   A/B   Traffic   PType   MISC
        return {
            'GROUP_TYPE': RDS._bits_to_hex(bits[:4]),
            'VERSION': str(bits[4]),
            'TRAFFIC_ANNOUNCEMENT': str(bits[5]),
            'PTY': RDS._bits_to_int(bits[6:11], string=True)
        }

    def _bits_to_int(bits: List[int], string=False) -> Union[int, str]:
        """
        Converts an array of bits into a decimal representation as either
        an integer or a string conditioned on string

        Args:
            bits (List[int]): Array of bits (0 or 1)
            string (bool, optional): Indicates whether to return a string
            representation or an int. Defaults to False.

        Returns:
            Union[int, str]: If string is False, returns an integer.
                             If string is True, returns a string representation.
        """
        binary_string = ''.join(str(int(bit)) for bit in bits)
        decimal_value = int(binary_string, 2)
        return str(decimal_value) if string else decimal_value

    def _bits_to_hex(bits: List[int]) -> str:
        """
        Converts an array of bits into a hexadecimal representation as a
        string.

        Args:
            bits (List[int]): Array of bits (0 or 1)

        Returns:
            str: The string representation of the hex code.
        """
        binary_string = ''.join(str(int(bit)) for bit in bits)
        decimal_value = int(binary_string, 2)
        hex_string = hex(decimal_value)[2:]
        return hex_string.upper()

    def _rds_syndrome(message: List[int], m_offset: int, mlen: int) -> Optional[str]:
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

    def __init__(self) -> None:
        raise ValueError('This class should not be instantiated')
