from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import sys
import time
import os

from rtlsdr import RtlSdr
from rds_signal_decoder import RDSSignalDecoder
from rds_constants import RDS
from rds_bit_decoder import RDSBitDecoder


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
            N = int(1024000*0.5)

            sdr = RtlSdr()
            sdr.sample_rate = sample_rate
            sdr.center_freq = center_freq
            sdr.freq_correction = -52
            sdr.gain = 42.0

            decoder = RDSSignalDecoder(sample_rate)
            bit_decoder = RDSBitDecoder()

            while True:

                samples = sdr.read_samples(N)
                decoder.load_samples(samples)
                bits = decoder.read_bits()

                bit_decoder.decode(bits)

        elif option == "-f":
            bit_file = value
            if os.path.isfile(bit_file):
                read_from_file = True
                bits = read_array_from_file(bit_file)
            else:
                raise ValueError()
        else:
            print("Invalid option!")
            print_usage()

    # plt.figure()
    # plt.plot(bits[:200])
    # plt.title("Bits for RDS")
    # plt.ylim(-0.2, 1.2)
    # plt.show()



def write_array_to_file(array, filename):
    with open(filename, 'w') as file:
        for num in array:
            file.write(str(num) + '\n')


def read_array_from_file(filename):
    bits = []
    with open(filename, 'r') as file:
        for line in file:
            bits.append(int(line.strip()))
    return bits


def print_usage():
    print("Usage:")
    print("python3 rds.py -r {frequency}")
    print("or")
    print("python3 rds.py -f {file path}")


if __name__ == "__main__":
    main()
