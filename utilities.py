#!/usr/bin/env python3

from __future__ import print_function, division, unicode_literals
from time import localtime
from time import strftime
from time import mktime
from time import sleep

import json
import requests
#from StringIO import StringIO

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def ts2label(timestamp):
	return strftime("%d %H:%M", localtime(timestamp/1000))

def ochlv2ohlcv(ochlv):
	for io in range(0, len(ochlv)):
		cv = ochlv[io][2]
		hv = ochlv[io][3]
		lv = ochlv[io][4]
		ochlv[io][2] = hv
		ochlv[io][3] = lv
		ochlv[io][4] = cv
	return ochlv

def ochlv_split(ochlv):
	t = []
	o = []
	c = []
	h = []
	l = []
	v = []

	for ii in range(0, len(ochlv)):
		t.append(ochlv[ii][0])
		o.append(ochlv[ii][1])
		c.append(ochlv[ii][2])
		h.append(ochlv[ii][3])
		l.append(ochlv[ii][4])
		v.append(ochlv[ii][5])

	return (t, o, c, h, l, v)
