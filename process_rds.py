from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

from rtlsdr import RtlSdr
from rds_signal_decoder import RDSSignalDecoder


def main():

    bits = []
    read_from_file = False

    if len(sys.argv) > 1:
        bit_file = sys.argv[1]
        if os.path.isfile(bit_file):
            read_from_file = True
            bits = read_array_from_file(bit_file)
        else:
            ValueError()
    else:
        station_freq = int(94.9e6)  # KUOW

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

    # for i in range(10):
    #     samples = sdr.read_samples(N)
    #     decoder.load_samples(samples)
    #     np.concatenate((bits, decoder.read_bits()))

    plt.figure()
    plt.plot(bits[:200])
    plt.title("Bits for RDS")
    plt.ylim(-0.2, 1.2)
    plt.show()

    my_hits = []

    for i in range(len(bits)-26):
        h = rds_syndrome(bits, i, 26)
        if h:
            my_hits.append((i, h))

    print((len(my_hits), my_hits[0:10]))

    if not read_from_file:
        write_array_to_file(bits, 'bits.txt')


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


if __name__ == "__main__":
    main()
