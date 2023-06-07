from scipy import signal
import matplotlib.pyplot as plt
import numpy as np

from rtlsdr import RtlSdr
from rds_signal_decoder import RDSSignalDecoder


def main():

    station_freq = int(106.1e6)  # KUOW

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

    for i in range(0):
        samples = sdr.read_samples(N)
        decoder.load_samples(samples)
        np.concatenate((bits, decoder.read_bits()))


    # Find a valid 104-bit group

    my_hits = []

    for i in range(len(bits)-26):
        h = rds_syndrome(bits, i, 26)
        if h:
            my_hits.append( (i, h) )

    plt.plot([r[0] % 26 for r in my_hits])
    plt.ylim(-1, 27)
    plt.title("26 bit block alignment of each candidate block")
    plt.show()


def rds_syndrome(message, m_offset, mlen):
    POLY = 0x5B9 # 10110111001, g(x)=x^10+x^8+x^7+x^5+x^4+x^3+1
    PLEN = 10
    SYNDROME=[383, 14, 303, 663, 748]
    OFFSET_NAME=['A', 'B', 'C', 'D', 'C\'']
    reg = 0

    if((mlen!=16)and(mlen!=26)):
        raise ValueError
    # start calculation
    for i in range(mlen):
        reg=(reg<<1)|(message[m_offset+i])
        if(reg&(1<<PLEN)):
            reg=reg^POLY
    for i in range(PLEN,0,-1):
        reg=reg<<1
        if(reg&(1<<PLEN)):
            reg=reg^POLY
    checkword=reg&((1<<PLEN)-1)
    # end calculation
    for i in range(0,5):
        if(checkword==SYNDROME[i]):
            return OFFSET_NAME[i]

    return None

def decode_rds_station_name(bits):
    # Check if the RDS bits are valid
    if len(bits) != 104:
        raise ValueError("Invalid RDS bit length")

    # Extract relevant bits for station name decoding
    station_name_bits = bits[16:48]

    # Initialize the station name as an empty string
    station_name = ""

    # Iterate over each group of 2 bits
    for i in range(0, len(station_name_bits), 2):
        # Decode the ASCII character from the 2-bit group
        char_bits = station_name_bits[i:i+2]
        ascii_val = char_bits[0] * 2 + char_bits[1]
        char = chr(ascii_val)

        # Append the character to the station name
        station_name += char

    return station_name


if __name__ == "__main__":
    main()
