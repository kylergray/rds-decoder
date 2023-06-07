# RDS Decoder Project

Decode RDS information from FM radio stations using an RTL-SDR.

## Usage
rds_display.py [-h] (-f FILE | -r FREQUENCY) [-s SAVE]

Display the decoded RDS information from an FM radio station using an RTL-SDR!

options:
 * -h, --help            show this help message and exit
 * -f FILE, --file FILE  Read from the given bit file
 * -r FREQUENCY, --radio FREQUENCY Tune to the specified radio frequency
 * -s SAVE, --save SAVE  Save the recording to the given file path

## Links
* https://wiki.gnuradio.org/index.php?title=Tutorials
* https://github.com/alexmrqt/fm-rds/blob/master/radio/rds_demod.py
* https://picodes.nrscstandards.org/fs_pi_codes_allocated.html?
* https://en.wikipedia.org/wiki/Radio_Data_System#Baseband_coding_(Data-link_layer)
