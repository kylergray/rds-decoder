from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import sys
import time
import os

from rtlsdr import RtlSdr
from rds_signal_decoder import RDSSignalDecoder


def main():

    BLK_SIZ = 16

    bits = []
    read_from_file = False

    if len(sys.argv) != 3:
        print("Invalid number of arguments!")
        print_usage()
    else:
        option = sys.argv[1]
        value = sys.argv[2]

        if option == "-r":
            freq = float(value) * 1e6
            station_freq = int(freq)  # KUOW

            offset_freq = 250000
            center_freq = station_freq - offset_freq
            sample_rate = int(57e3*20)
            N = int(1024000*8)

            sdr = RtlSdr()
            sdr.sample_rate = sample_rate
            sdr.center_freq = center_freq
            sdr.freq_correction = -52
            sdr.gain = 42.0

            samples = sdr.read_samples(N)

            decoder = RDSSignalDecoder(sample_rate)

            decoder.load_samples(samples)

            bits = decoder.read_bits()

            for i in range(2):
                samples = sdr.read_samples(N)
                decoder.load_samples(samples)
                bits = np.concatenate((bits, decoder.read_bits()))
        elif option == "-f":
            bit_file = value
            if os.path.isfile(bit_file):
                read_from_file = True
                bits = read_array_from_file(bit_file)
            else:
                ValueError()
        else:
            print("Invalid option!")
            print_usage()

    # plt.figure()
    # plt.plot(bits[:200])
    # plt.title("Bits for RDS")
    # plt.ylim(-0.2, 1.2)
    # plt.show()

    groups = []
    BLOCK_TYPES_A = ['A', 'B', 'C', 'D']

    for bit_pos in range(len(bits) - 104):
        # if block_type is not None:
        #     print(bit_pos, block_type)
        group = {}
        for block_i in range(4):
            block_type = rds_syndrome(bits, bit_pos, 26)
            if block_type == BLOCK_TYPES_A[block_i]:
                group.update({block_type: bit_pos})
            bit_pos += 26
        if len(group) > 1:
            groups.append((bit_pos, group))

    if not read_from_file:
        print(f'Saving file with {len(bits)} bits')
        write_array_to_file(bits, 'bits.txt')

    program_id = ''
    program_type = ''
    radio_name = '_' * 8
    radio_text = '_' * 64

    for bit_pos, group in groups:
        # print(group)
        # print(group)
        info = {}
        a_bits = []
        b_bits = []
        c_bits = []
        d_bits = []

        if 'A' in group:
            a_bits = bits[group['A']:group['A'] + BLK_SIZ]

            info.update(decode_block_a(a_bits))
            program_id = info['PID']

        if 'C' in group:
            c_bits = bits[group['C']:group['C'] + BLK_SIZ]

        if 'D' in group:
            d_bits = bits[group['D']:group['D'] + BLK_SIZ]

        if 'B' in group:
            b_bits = bits[group['B']:group['B'] + BLK_SIZ]

            info.update(decode_block_b(b_bits))
            program_type = info['PTY']


            # 0A is 8 byte radio name
            if (info['GROUP_TYPE'] == '0'
                and info['VERSION'] == '0'
                and 'D' in group):
                # which position
                # __ __ __ __
                # 0  1  2  3
                char_pos = bits_to_int(b_bits[14:]) * 2
                text = chr(bits_to_int(d_bits[:8])) + chr(bits_to_int(d_bits[8:]))
                radio_name = radio_name[:char_pos] + \
                    text + radio_name[char_pos+2:]

            # 2A is 64 byte radio text
            if (info['GROUP_TYPE'] == '2'
                and info['VERSION'] == '0'
                and 'D' in group):
                # clear screen
                clear = b_bits[11] == 1
                if clear:
                    radio_text = '_' * 64

                # which position
                # ____ ____ ____ ____ ... ____
                # 0    1    2    3        63
                char_pos = bits_to_int(b_bits[12:]) * 4
                if 'C' in group:
                    text = chr(bits_to_int(c_bits[:8])) + chr(bits_to_int(c_bits[8:]))
                    radio_text = radio_text[:char_pos] + \
                        text + radio_text[char_pos + 2:]

                if 'D' in group:
                    text = chr(bits_to_int(d_bits[:8])) + chr(bits_to_int(d_bits[8:]))
                    radio_text = radio_text[:char_pos + 2] + \
                        text + radio_text[char_pos + 4:]

        print(program_id, program_type, radio_name, radio_text)


def decode_block_a(bits):
    return {'PID': bits_to_hex(bits)}


def decode_block_b(bits):
    # | 4b  | 1b  | 1b      | 5b    | 5b   |
    #  Type   A/B   Traffic   PType | MISC
    return {'GROUP_TYPE': bits_to_hex(bits[:4]),
            'VERSION': str(bits[4]),
            'TRAFFIC_ANNOUNCEMENT': str(bits[5]),
            'PTY': bits_to_int(bits[6:11], string=True),
            'CHAR_SEGMENT': bits_to_hex(bits[14:])}

def decode_block_c(bits, type, version):
    text = ''
    if str(type) == '0' and str(version) == '0':
        # radio text
        text += chr(_collect_bits(bits, 0, 8)) + chr(_collect_bits(bits, 8, 8))
    return {'TEXT': text}


def write_array_to_file(array, filename):
    with open(filename, 'w') as file:
        for num in array:
            file.write(str(num) + '\n')


def read_array_from_file(filename):
    boolean_array = []
    with open(filename, 'r') as file:
        for line in file:
            value = line.strip()
            if value.lower() == 'true':
                boolean_array.append(1)
            elif value.lower() == 'false':
                boolean_array.append(0)
    return boolean_array


def bits_to_int(bits, string=False):
    binary_string = ''.join(str(int(bit)) for bit in bits)
    decimal_value = int(binary_string, 2)
    return str(decimal_value) if string else decimal_value

def bits_to_hex(bits):
    binary_string = ''.join(str(int(bit)) for bit in bits)
    decimal_value = int(binary_string, 2)
    hex_string = hex(decimal_value)[2:]  # Remove the '0x' prefix
    return hex_string.upper()


def rds_syndrome(message, m_offset, mlen):
    POLY = 0x5B9  # 10110111001, g(x)=x^10+x^8+x^7+x^5+x^4+x^3+1
    PLEN = 10
    SYNDROME = [383, 14, 303, 663, 748]
    OFFSET_NAME = ['A', 'B', 'C', 'D', 'C\'']
    reg = 0

    if ((mlen != 16) and (mlen != 26)):
        raise ValueError
    # start calculation
    for i in range(mlen):
        reg = (reg << 1) | (message[m_offset+i])
        if (reg & (1 << PLEN)):
            reg = reg ^ POLY
    for i in range(PLEN, 0, -1):
        reg = reg << 1
        if (reg & (1 << PLEN)):
            reg = reg ^ POLY
    checkword = reg & ((1 << PLEN)-1)
    # end calculation
    for i in range(0, 5):
        if (checkword == SYNDROME[i]):
            # print "checkword matches syndrome for offset", OFFSET_NAME[i]
            return OFFSET_NAME[i]

    return None

def print_usage():
    print("Usage:")
    print("python3 rds.py -r {frequency}")
    print("or")
    print("python3 rds.py -f {file path}")

if __name__ == "__main__":
    main()
