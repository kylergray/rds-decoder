import numpy as np


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

    def __init__(self) -> None:
        pass

    def decode(self, bits: np.ndarray) -> None:
        my_hits = []

        for i in range(len(bits)-26):
            h = self.rds_syndrome(bits, i, 26)
            if h:
                my_hits.append( (i, h) )

        print(len(bits))
        print((len(my_hits), my_hits))

    def rds_syndrome(self, message, m_offset, mlen):
        POLY = 0x5B9  # 10110111001, g(x)=x^10+x^8+x^7+x^5+x^4+x^3+1
        PLEN = 10
        SYNDROME = [383, 14, 303, 663, 748]
        OFFSET_NAME = ['A', 'B', 'C', 'D', 'C\'']
        reg = 0

        if (mlen != 16 and mlen != 26):
            raise ValueError
        # start calculation
        for i in range(mlen):
            reg = (reg << 1) | (message[m_offset + i])
            if reg & (1 << PLEN):
                reg = reg ^ POLY
        for i in range(PLEN, 0, -1):
            reg = reg << 1
            if reg & (1 << PLEN):
                reg = reg ^ POLY
        checkword = reg & ((1 << PLEN) - 1)
        # end calculation
        for i in range(0, 5):
            if checkword == SYNDROME[i]:
                # print "checkword matches syndrome for offset", OFFSET_NAME[i]
                return OFFSET_NAME[i]
        return None


bit_decorder = RDSBitDecoder()
rds_bits = "110010010011101011001000101010100101001100010011011100110001011100111100110100100101111010011010100111100110011001101010011001100010011010001100010"
bit_decorder.decode([int(bit) for bit in rds_bits])