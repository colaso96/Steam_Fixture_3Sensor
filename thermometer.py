import glob
import time
import os

TEMP_PROBE_SURR = ''
TEMP_PROBE_STEAM = ''
TEMP_PROBE_STATE = True

def update_temp_id():
    global TEMP_PROBE_SURR, TEMP_PROBE_STEAM
    try:
        mypath = '/sys/bus/w1/devices/'
        onlylinks = [f for f in os.listdir(mypath) if os.path.islink(os.path.join(mypath, f))]
        onlylinks.remove('w1_bus_master1')
        TEMP_PROBE_SURR = str(onlylinks[0])
        TEMP_PROBE_STEAM = str(onlylinks[1])
    except IndexError:
        TEMP_PROBE_STATE = False

def read_temp_raw(id):
    base_dir = '/sys/bus/w1/devices/'
    thermo_file = glob.glob(base_dir + id)[0] + '/w1_slave'
    f = open(thermo_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp(id):
    lines = read_temp_raw(id)
    while lines[0].strip()[-3:] != 'YES':
        lines = read_temp_raw(id)
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

update_temp_id()
print(TEMP_PROBE_STEAM)
print(TEMP_PROBE_SURR)
while 1:
    print(read_temp(TEMP_PROBE_SURR))
    print(read_temp(TEMP_PROBE_STEAM))
