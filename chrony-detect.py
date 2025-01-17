#!/usr/bin/python3

import os
import re
import datetime
import pytz
import tzlocal
import ntplib
import subprocess
from ctypes import *
from ctypes.util import find_library

STA_NANO = 0x2000
STA_UNSYNC = 0x0040

class TimevalStruct(Structure):
    _fields_ = [
        ("tv_sec", c_long),
        ("tv_usec", c_long),
    ]


class TimexStruct(Structure):
    _fields_ = [
        ("modes", c_int),
        ("offset", c_long),
        ("freq", c_long),
        ("maxerror", c_long),
        ("esterror", c_long),
        ("status", c_int),
        ("constant", c_long),
        ("precision", c_long),
        ("tolerance", c_long),
        ("time", TimevalStruct),
        ("tick", c_long),
        ("ppsfreq", c_long),
        ("jitter", c_long),
        ("shift", c_int),
        ("stabil", c_long),
        ("jitcnt", c_long),
        ("calcnt", c_long),
        ("errcnt", c_long),
        ("stbcnt", c_long),
        ("tai", c_int),
    ]

    @property
    def synchronized(self):
        return (self.status & STA_UNSYNC) == 0


def ntp_adjtime():

    libc = cdll.LoadLibrary(find_library("c"))
    timex = TimexStruct()
    p_timex = pointer(timex)

    libc.ntp_adjtime(p_timex)

    return p_timex.contents

unsync = False
output = subprocess.Popen("chronyc tracking", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
if "not found" in output.stderr.read().decode():
    print("chrony not installed")
else:
    if "506 Cannot talk to daemon" in output.stdout.read().decode():
        unsync = True
    output = output.stdout.read()
    print("chrony installed")
    adjtime = ntp_adjtime()
    system_synchronized = adjtime.synchronized
    utc = datetime.datetime.utcnow()
    local_tz = tzlocal.get_localzone()
    time_here = pytz.utc.localize(utc).astimezone(local_tz)

    raw_offset = time_here.strftime("%z")
    if len(raw_offset):
        offset = raw_offset[:3] + ":" + raw_offset[-2:]
    else:
        offset = ""

    result = {
        "time": time_here.strftime("%Y-%m-%dT%H:%M:%S.%f") + offset,
        "synchronized": system_synchronized,
    }
    if system_synchronized:
        
        # chrony implementation
        
        parameters = output.decode().split("\n")
        
        reference_str = ""
        offset_str = ""
        for parameter in parameters:
            if "Reference" in parameter:
                reference_str = parameter
            if "Last offset" in parameter:
                offset_str = parameter
        
        try:
            if unsync == False:
                result["source"] = "chrony"
            else:
                raise Exception("Chrony not running")        
            reference = reference_str[reference_str.find('('):reference_str.find(')')]
            if reference != "":
                result["reference"] = reference[1:]
            else:
                raise Exception("Reference server not found")
        
            offset = offset_str[offset_str.find(':'):]
            if offset != "":
                result["offset"] = offset[2:]
            else:
                raise Exception("Offset not found")
 
        except Exception as ex:
            result["synchronized"] = False
            result["error"] = str(ex)
    print(result)

