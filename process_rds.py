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

    for i in range(10):
        samples = sdr.read_samples(N)
        decoder.load_samples(samples)
        np.concatenate((bits, decoder.read_bits()))

    plt.figure()
    plt.plot(bits[:200])
    plt.title("Bits for RDS")
    plt.ylim(-0.2, 1.2)
    plt.show()

    my_hits = []

    for i in range(len(bits)-26):
        h = rds_syndrome(bits, i, 26)
        if h:
            my_hits.append( (i, h) )

    print((len(my_hits), my_hits[0:10]))


    hit_parses = []
    for i in range(len(my_hits)-3):
        if my_hits[i][1] == "A":
            bogus = False
            for j,sp in enumerate("ABCD"):
                if 26*j != my_hits[i+j][0] - my_hits[i][0]:
                    bogus = True
                if my_hits[i+j][1] != sp:
                    bogus = True

            if not bogus:
                for j in range(4):
                    hit_parses.append( (my_hits[i+j][0], decode_one(bits, my_hits[i+j][0])))


    print(len(hit_parses), hit_parses[:20])

    print(accumulate_radiotext([ b for (a,b) in hit_parses]))
    print(accumulate_b0text([ b for (a,b) in hit_parses]))

    print("")


    hit_parses = []
    for i in range(len(my_hits)-3):
        if my_hits[i][1] == "A":
            bogus = False
            # for j,sp in enumerate("ABCD"):
            #     if 26*j != my_hits[i+j][0] - my_hits[i][0]:
            #         bogus = True
            #     if my_hits[i+j][1] != sp:
            #         bogus = True

            if not bogus:
                for j in range(4):
                    hit_parses.append( (my_hits[i+j][0], decode_one(bits, my_hits[i+j][0])))


    print(len(hit_parses), hit_parses[:20])

    print(accumulate_radiotext([ b for (a,b) in hit_parses]))
    print(accumulate_b0text([ b for (a,b) in hit_parses]))


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
            #print "checkword matches syndrome for offset", OFFSET_NAME[i]
            return OFFSET_NAME[i]

    return None

def _collect_bits(bitstream, offset, n):
    """Helper method to collect a string of n bits, MSB, into an int"""
    retval = 0
    for i in range(n):
        retval = retval*2 + bitstream[offset+i]
    return retval

def decode_A(bitstream, offset):
    """Trivial RDS block A decoder"""
    return _collect_bits(bitstream, offset, 16)

def decode_B(bitstream, offset):
    """Trivial RDS block B decoder"""
    retval = {}

    retval["group_type"] = _collect_bits(bitstream, offset, 4)
    retval["version_AB"] = "B" if bitstream[offset+4] else "A"
    retval["traffic_prog_code"] = bitstream[offset+5]
    retval["prog_type"] = _collect_bits(bitstream, offset+6,5)

    if retval["group_type"] == 2:
        retval["text_segment"] = _collect_bits(bitstream, offset+12, 4)
    elif retval["group_type"] == 0:
        retval["pi_segment"] = _collect_bits(bitstream, offset+14, 2)

    return retval

def decode_C(bitstream, offset):
    """Trivial RDS block C decoder"""
    c0 = _collect_bits(bitstream, offset, 8)
    c1 = _collect_bits(bitstream, offset+8, 8)

    return ( chr(c0), chr(c1))

def decode_Cp(bitstream, offset):
    """Stub RDS block C decoder"""
    return None

def decode_D(bitstream, offset):
    """Trivial RDS block D decoder"""
    return decode_C(bitstream, offset)

# A lookup table to make it easier to dispatch to subroutines in the code below
decoders = { "A": decode_A, "B": decode_B, "C": decode_C, "C'": decode_Cp, "D": decode_D }

def decode_one(bitstream, offset):
    s = rds_syndrome(bitstream, offset, 26)
    if None == s:
        return None

    return (s, decoders[s](bitstream, offset))


def accumulate_radiotext(parses):
    """A state machine that accumulates the radio text messages

    This takes in a whole list of packet-qualifying blocks (ie:
    a list of blocks, but which have been filtered down such that
    they always come in ABCD or ABC'D order, and each quad is
    adjacent in the bitstream).

    Returns a list of states of the radio text as it progresses
    through consuming the input packets.
    """
    cur_state = ["_"] * 64

    retval = [ "".join(cur_state) ]

    cursor = None
    for blkid, decode in parses:
        if blkid == "B":
            if decode['group_type'] == 2:
                cursor = decode['text_segment'] * 4
            else:
                cursor = None

        if None != cursor:
            if blkid == "C":
                cur_state[cursor] = decode[0]
                cur_state[cursor+1] = decode[1]
                retval.append("".join(cur_state))
            elif blkid == "D":
                cur_state[cursor+2] = decode[0]
                cur_state[cursor+3] = decode[1]
                retval.append("".join(cur_state))

            if blkid == "A" or blkid == "D":
                cursor = None

    return retval


def accumulate_b0text(parses):
    cur_state = ["_"] * 8

    retval = [ "".join(cur_state) ]

    cursor = None
    for blkid, decode in parses:
        if blkid == "B":
            if decode['group_type'] == 0:
                cursor = decode['pi_segment'] * 2
            else:
                cursor = None

        if None != cursor:
            if blkid == "D":
                cur_state[cursor] = decode[0]
                cur_state[cursor+1] = decode[1]
                retval.append("".join(cur_state))
            if blkid == "A" or blkid == "D":
                cursor = None

    return retval




if __name__ == "__main__":
    main()
