from rtlsdr import RtlSdr
import numpy as np
from scipy.signal import resample_poly, firwin, bilinear, lfilter, welch, hilbert, resample, butter, filtfilt
import matplotlib.pyplot as plt
import time
import sounddevice as sd
from copy import copy
from rds_bit_reader import RDSBitReader
import math

from tools import bandpassmask, lowpass_fir_filter
np.set_printoptions(precision=2)

# Close previous instances of the sdr object
try:
    sdr.close()
    print("Closed old SDR")
except NameError:
    print("No SDR instance found")

sdr = RtlSdr()  # Create a new sdr object (by keeping this in


sample_rate = 2*256*256*2  # =  ... about 2Msps...works

fc = 94.9e6  # Seattle
dt = 1.0/sample_rate  # time step size between samples
nyquist = sample_rate / 2.0

Tmax = 4        # 2.5 s

N = round(sample_rate*Tmax)  # N must be a multiple of 256

sdr.sample_rate = sample_rate
sdr.center_freq = fc
sdr.gain = 42.0  # This is max, according to sdr.valid_gains_db

faudiosps = 48000
faudionyquist = faudiosps/2.0

# Collect N samples...N must be multiple of 256
samples = sdr.read_samples(N)

bit_reader = RDSBitReader(sample_rate)

bit_reader.run(samples=samples)

bits = bit_reader.bits()
print(len(bits))

# for i in range(100):
#   print(bits[i])

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

bitdec = bits[1:] != bits[:-1]

my_hits = []

for i in range(len(bitdec)-26):
    h = rds_syndrome(bitdec, i, 26)
    if h:
        my_hits.append( (i, h) )

print((len(my_hits), my_hits[0:10]))

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
                hit_parses.append( (my_hits[i+j][0], decode_one(bitdec, my_hits[i+j][0])))


print(len(hit_parses), hit_parses)