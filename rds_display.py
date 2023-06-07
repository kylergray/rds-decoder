from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import sys
import time
import os
import argparse

from rtlsdr import RtlSdr
from rds_signal_decoder import RDSSignalDecoder
from rds_constants import RDS
from rds_bit_decoder import RDSBitDecoder


def main():
    parser = argparse.ArgumentParser(
        description='Display the decoded RDS information from an FM radio station using an RTL-SDR!')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='Read from the given bit file')
    group.add_argument('-r', '--radio', type=float, metavar='FREQUENCY',
                      help='Tune to the specified radio frequency')
    parser.add_argument(
        '-s', '--save', help='Save the recording to the given file path')
    args = parser.parse_args()

    if args.file:
        bit_file = args.file
        if os.path.isfile(bit_file):
            RDSBitDecoder((False, None), (True, bit_file))
        else:
            raise ValueError('Invalid file')

    if args.radio:
        frequency = args.radio

        freq = float(frequency) * 1e6
        station_freq = int(freq)

        offset_freq = 250000
        center_freq = station_freq - offset_freq
        sample_rate = int(57e3*20)
        N = int(1024000*1)

        sdr = RtlSdr()
        sdr.sample_rate = sample_rate
        sdr.center_freq = center_freq
        sdr.gain = 42.0

        decoder = RDSSignalDecoder(sample_rate)
        bit_decoder = RDSBitDecoder((True if args.save else False, args.save),
                                    (False, None))

        while True:
            samples = sdr.read_samples(N)
            decoder.load_samples(samples)
            bits = decoder.read_bits()

            bit_decoder.decode(bits)

            sdr.close()


if __name__ == "__main__":
    main()
