#!/usr/bin/env python2

from __future__ import print_function, division, unicode_literals
import time
import utilities
import logging
import ccxt
import math

class ExchgData:

	known_exchanges = ['bitmex', 'bitmex-testnet', 'bfx']
	apitrylimit = 20
	apitrysleep = 5
	tf_seconds = { 
			'1m' : 60,
			'5m' : 300,
			'10m' : 600,
			'15m' : 900,
			'1h' : 60*60,
			'3h' : 60*60*3,
			'6h' : 60*60*6,
			'12h' : 60*60*12,
			'1d' : 60*60*24,
			'3d' : 60*60*24*3
			}
	candles = {}
	cindexes  = {
			'time' : 0,
			'open' : 1,
			'high' : 2,
			'low' : 3,
			'close' : 4,
			'volume' : 5
			}

	book = { 
			'bids': {},
			'asks': {},
			'ts': 0
			}

	def __init__(self, exchange, symbol = u'BTC/USD', logfile='full.log'):
		if exchange in self.known_exchanges:
			if exchange == 'bfx':
				self.exchange = ccxt.bitfinex2({
					'rateLimit': 10000,
					'enableRateLimit': True
					})
			if exchange == 'bitmex':
				self.exchange = ccxt.bitmex({
					'rateLimit': 10000,
					'enableRateLimit': True
					})
			self.symbol = symbol
		self.logger = logging.getLogger(__name__+'.ExchgData')
		self.logger.setLevel(logging.DEBUG)
		sh = logging.StreamHandler()
		dh = logging.FileHandler(logfile)
		sh.setLevel(logging.INFO)
		dh.setLevel(logging.DEBUG)
		fm = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
		dh.setFormatter(fm)
		sh.setFormatter(fm)
		self.logger.addHandler(sh)
		self.logger.addHandler(dh)
		self.logger.info("Logger initialized")


	def debug(self, message):
		self.logger.debug(message)

	# timeframe tf should be in tf_seconds
	# lookback should be number of candles
	# start and end should be in milliseconds
	def fetch_candles(self, tf, start = None, end = None):
		rawdata = None
		apitry = 0

		if not start:
			start = (time.time() - self.tf_seconds[tf]*100)*1000
		
		if not end:
			end = time.time()*1000

		start = start - (start % self.tf_seconds[tf])
		limit = math.ceil((end-start)/1000./self.tf_seconds[tf])
		self.debug("Limit %d candles from start %d to end %d" % (limit, start, end))
		while not rawdata and apitry < self.apitrylimit:
			try:
				self.debug("Fetching %s candles with start ts %d, limit %d" % (tf, start, limit))
				rawdata = self.exchange.fetch_ohlcv(self.symbol, tf, start, limit)
			except (ccxt.ExchangeError, ccxt.DDoSProtection, ccxt.AuthenticationError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as error:
				self.debug( "failed to connect to api to fetch candles, sleeping for %d seconds, try %d of %d" % (self.apitrysleep+apitry*2, apitry, self.apitrylimit))
				self.debug(error)
				time.sleep(self.apitrysleep+apitry*2)
				apitry = apitry+1
		self.debug("Last candle ts: %s" % utilities.ts2label(rawdata[-1][0]))
	# 	if time.time()*1000 - rawdata[-1][0] < self.tf_seconds[tf]:
	# 		self.debug("Last candle is not complete with ts %s, dropping" % utilities.ts2label(rawdata[-1][0]))

		self.debug("Fetched %d candles" % len(rawdata))
		if(len(rawdata) < limit-1):
			self.logger.debug("Asked for %d candles but received %d" % (limit, len(rawdata)))
		return rawdata

	def preload_candles(self, tf, lookback = 100):
		self.candles[tf] = []

		lookback_s = self.tf_seconds[tf]*lookback
		self.debug("Preloading candles with lookback %d, lookback_s %d" % (lookback, lookback_s))	
		self.candles[tf] = self.fetch_candles(tf, start = (time.time() - lookback_s)*1000)
		self.debug("Current candles: %d" % len(self.candles[tf]))
	
	def get_last_ts(self, tf):
		if not tf in self.candles.keys():
			self.preload_candles(tf)

		last_ts = self.candles[tf][-1][0]

		self.debug("Last TS: %d" % last_ts)
		return last_ts

	def update_candles(self, tf, lookback = 100):
		self.debug("Update candles for %s, lookback %d" % (tf, lookback))
		if (not tf in self.candles.keys()):
			self.debug("tf %s not in candles keys" % tf)
		elif len(self.candles[tf]) < lookback:
			self.debug("current candles length %d less than lookback %d" % (len(self.candles[tf]), lookback))
		if (not tf in self.candles.keys()) or len(self.candles[tf]) < lookback:
			self.preload_candles(tf, lookback)
			self.debug("Preloading candles for tf %s, lookback %d" % (tf, lookback))
		else:
			self.debug("updating candles for %s, lookback %d" % (tf, lookback))
			last_ts = self.get_last_ts(tf)
			self.debug("Last ts is %d" % last_ts)
			lag = time.time() - last_ts/1000.
			self.debug("Lag is %d" % lag)
			currlen = len(self.candles[tf])
			self.debug("current length for tf %s is %d" % (tf, currlen))
			
			candles = self.fetch_candles(tf, start=((time.time() - (lag+self.tf_seconds[tf]))*1000))
			self.debug("Candles length is %d" % len(candles))
			if lag > self.tf_seconds[tf]:
				self.debug("Fetching fresh data for lag %d greater than %d" % (lag, self.tf_seconds[tf]))
				it = 0
				while it < len(candles) and candles[it][0] < last_ts:
					self.debug("it %d, ts %d" % (it, candles[it][0]))
					it = it + 1

				if it < len(candles):
					self.debug("Old candles last ts now %s" % utilities.ts2label(self.get_last_ts(tf)))
					self.candles[tf] = self.candles[tf][-currlen:-1]
					self.debug("Old candles last ts now %s" % utilities.ts2label(self.get_last_ts(tf)))
					self.candles[tf].extend(candles[it:])
					self.debug("Old candles last tses now %s, %s" % (utilities.ts2label(self.candles[tf][-2][0]), utilities.ts2label(self.get_last_ts(tf))))
					trimlength = currlen
					if(lookback > trimlength):
						trimlength = lookback
					self.debug("Resizing candles to %d" % trimlength)
					self.candles[tf] = self.candles[tf][-trimlength:] # prevent indefinite expansion
				self.debug("New last timestamp is %d" % self.get_last_ts(tf))
			else:
				self.candles[tf] = self.candles[tf][-currlen:-1]
				self.debug("Old candles last ts now %s" % utilities.ts2label(self.get_last_ts(tf)))
				self.debug("Refreshing last candle for lag %d less than %d" % (lag, self.tf_seconds[tf]))
				self.candles[tf].append(candles[-1])
				self.debug("Update candles last ts now %s" % utilities.ts2label(self.get_last_ts(tf)))

	def get_candles(self, tf, lookback):
		# if not tf in self.candles.keys() or len(self.candles[tf]) < lookback:
		# 	log.debug("Preloading in get_candles for tf, len self.candles[tf], lookback" % (tf, len(self.candles[tf]), lookback))
		# 	self.preload_candles(tf, lookback)
		self.update_candles(tf, lookback)
		return self.candles[tf][-lookback:]
	
	def get_candle_components(self, tf, lookback, component):
		candles = self.get_candles(tf, lookback)
		components = []
		if component in self.cindexes.keys():
			for candle in candles:
				components.append(candle[self.cindexes[component]])

		return components

	def get_closes(self, tf, lookback):
		return self.get_candle_components(tf, lookback, 'close')

	def get_times(self, tf, lookback):
		return self.get_candle_components(tf, lookback, 'time')

	# use this to be sure the times and candles are aligned and no refresh between
	def get_times_closes(self, tf, lookback):
		self.debug("get_times_closes tf %s, lookback %d" % (tf, lookback))
		candles = self.get_candles(tf, lookback)
		times = []
		closes = []
		for candle in candles:
			times.append(candle[self.cindexes['time']])
			closes.append(candle[self.cindexes['close']])
		return (times, closes)

	def get_split_tohlcv(self, tf, lookback):
		candles = []
		while not candles:
			candles = self.get_candles(tf, lookback)
		splits = []
		for i in range(0,6):
			splits.append([])
		for candle in candles:
			splits[0].append(candle[self.cindexes['time']])
			splits[1].append(candle[self.cindexes['open']])
			splits[2].append(candle[self.cindexes['high']])
			splits[3].append(candle[self.cindexes['low']])
			splits[4].append(candle[self.cindexes['close']])
			splits[5].append(candle[self.cindexes['volume']])
		return splits

	def last_close(self, tf):
		closes = self.get_closes(tf, 1)
		return closes[-1]

	def purge_book(self):
		minqty = 0.1
		for side in ('bids', 'asks'):
			for key in self.book[side].keys():
				if self.book[side][key] < minqty:
					del self.book[side][key]

	def decay_book(self):
		decay=0.1 #10 percent per time period
		tau=10 #10 seconds per period
		tcurr = time.time()
		lag = tcurr - self.book['ts']/1000.
		periods = int(round(lag / tau))
		factor = 1
		for period in range(0, periods):
			factor *= decay
		for side in ('bids', 'asks'):
			for key in self.book[side].keys():
				self.book[side][key] *= factor
		self.purge_book()
		

	def update_book(self):
		apitry = 0
		bookdata = None
		while not bookdata and apitry < self.apitrylimit:
			try:
				self.debug("Fetching book...")
				bookdata = self.exchange.fetch_order_book(self.symbol,  params= { 'len' : 100 } )
			except (ccxt.ExchangeError, ccxt.DDoSProtection, ccxt.AuthenticationError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as error:
				self.debug( "failed to connect to api to fetch book, sleeping for %d seconds, try %d of %d" % (self.apitrysleep+apitry*2, apitry, self.apitrylimit))
				self.debug(error)
				time.sleep(self.apitrysleep+apitry*2)
				apitry = apitry+1

		newbook = { 'bids' : {}, 'asks' : {}, 'ts' : bookdata['timestamp'] }
		
		if round(newbook['ts']) > round(self.book['ts']):
			# first bin this update's data
			for side in ('bids', 'asks'):
				for entry in bookdata[side]:
					price = int(round(entry[0]))
					if not price in newbook[side].keys():
						newbook[side][price] = entry[1]
					else:
						newbook[side][price] += entry[1]
			
			self.decay_book()
			for side in ('bids', 'asks'):
				for price in newbook[side].keys():
					if not price in self.book[side].keys():
						self.book[side][price] = newbook[side][price]
					else:
						self.book[side][price] += newbook[side][price]
						self.book[side][price] /= 2.
			self.book['ts'] = newbook['ts']
			

	def print_book(self):
		bidkeys = self.book['bids'].keys()
		bidkeys = sorted(bidkeys, reverse=True)
		askkeys = self.book['asks'].keys()
		askkeys = sorted(askkeys, reverse=True)

		for key in askkeys:
			print("%d\t%.2f" %  (key, self.book['asks'][key]*-1))
		print('============================================')
		for key in bidkeys:
			print("%d\t%.2f" % (key, self.book['bids'][key]))

	def get_book(self):
		return self.book

	def dprint_last_candles(self, tf, lookback):
		if lookback > len(self.candles[tf]):
			lookback = len(self.candles[tf])
		for ts in range(-lookback, 0):
			candle = self.candles[tf][ts]
			self.debug("CANDLES(%s), T: %s, O: %.2f, H: %2.f, L: %.2f, C: %.2f, V: %.2f" % (tf, utilities.ts2label(candle[0]), candle[1], candle[2], candle[3], candle[4], candle[5]))
