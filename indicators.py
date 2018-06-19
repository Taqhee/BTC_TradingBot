#!/usr/bin/env python2

from __future__ import print_function, division, unicode_literals
import math
from utilities import ts2label
import numpy as np
import tulipy as ti
from time import localtime, mktime
from utilities import *

def alma( data, window, offset, sigma ):
	m = math.floor((float(offset) * (window - 1)))
	s = float(window)/float(sigma)
	almaseries = []
	for idata in range(0, len(data)-window):
		wtdsum = 0
		cumwt = 0
		for k in range(0,window-1):
			wtd = math.exp(-((k-m)*(k-m))/(2*s*s))
			wtdsum = wtdsum + wtd * data[idata+window-1-k]
			cumwt = cumwt + wtd
			almaseries.append(wtdsum / cumwt)
	return almaseries

def alma_ox_cross( ohlcv, window, offset, sigma ):
	diff = None
	opens = []
	closes = []

	# time, open, high, low, close, volume
	for candle in ohlcv:
		opens.append(candle[1])
		closes.append(candle[4])
	
	openalma = alma( opens, window, offset, sigma )
	closealma = alma( closes, window, offset, sigma )
	diff = closealma[-1] - openalma[-1]
	return diff

def kama(data):
	erp = 10
	fastMA = 2.
	slowMA = 30.
	fastAlpha = 2./(fastMA+1.)
	slowAlpha = 2./(slowMA+1.)
	
	kamadata = []
	kamadata.append(0.0)

	# looks back #erp
	for idata in range(erp, len(data)):
		change = abs(data[idata]-data[idata-erp])

		vsum = 0
		for ivol in range(0, erp):
			vsum = vsum + abs(data[idata-ivol]-data[idata-ivol-1])
		er = change/vsum
		sc = math.pow( er*(fastAlpha - slowAlpha)+slowAlpha, 2)
		kamadata.append(kamadata[-1]+sc*(data[idata]-kamadata[-1]))
	return kamadata[5:]


def klinger_kama(h, l, c, v):
	cslow = 55
	cfast = 34
	h2 = [float(i) for i in h]
	l2 = [float(i) for i in l]
	c2 = [float(i) for i in c]
	v2 = [float(i) for i in v]
	kvo = ti.kvo(np.array(h2), np.array(l2), np.array(c2), np.array(v2), 34.0, 55.0)
	signal = kama(kvo)
	return (kvo, signal)
