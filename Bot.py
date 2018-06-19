#!/usr/bin/env python3
# coding=utf-8
from __future__ import print_function
import time
import logging
#logging.basicConfig(level=logging.INFO)
import mexorders
from indicators import *
from notifications import send_sms
from utilities import *
import ExchgData

import config

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
dh = logging.FileHandler('full.log')
dh.setLevel(logging.DEBUG)
ih = logging.FileHandler('tradebot.log')
ih.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
ffm = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
cfm = logging.Formatter('[%(asctime)s] %(message)s')
sh.setFormatter(cfm)
dh.setFormatter(ffm)
ih.setFormatter(ffm)

log.addHandler(sh)
log.addHandler(dh)
log.addHandler(ih)
log.info("Logger initialized")

tl = logging.getLogger('trades')
tl.setLevel(logging.DEBUG)
tfh = logging.FileHandler('trades.log')
tsh = logging.StreamHandler()
tfh.setLevel(logging.DEBUG)
tsh.setLevel(logging.INFO)
tff = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
tsf = logging.Formatter('[%(asctime)s] %(message)s')
tfh.setFormatter(tff)
tsh.setFormatter(tsf)
tl.addHandler(tfh)
tl.addHandler(tsh)
tl.info("Trade Logger Initialized")

def report_trade(action, ordersize, stacked, price):
    report_string="action: %s\tordersize: %d\tstacked: %d\tprice: %.2f" % (action, ordersize, stacked, price)
    tl.info(report_string)
    log.debug(report_string)
    send_sms(report_string)


def hist_positive(exchgdata, tf):
    #  for the div detection
    (t, o, h, l, c, v) = exchgdata.get_split_tohlcv(tf, 34)
    exchgdata.dprint_last_candles(tf, 5)
    (kvo, signal) = klinger_kama(h, l, c, v)
    hist = kvo[-1] - signal[-1]
    log.info("hist is %.2f" % hist)	
    positive = True
    if hist <= 0:
        positive = False
    return positive

sleeptime = 30
#send_sms('\nBot Active!')
hist_tf = '1d'

bfxdata = ExchgData.ExchgData('bitmex')

last_hist_positive = hist_positive(bfxdata, hist_tf)
curr_hist_positive = last_hist_positive

while [ 1 ]:
    log.debug("Main loop")
    mexorders.update_bracket_pct(config.sl, config.tp)

    curr_hist_positive = hist_positive(bfxdata, hist_tf)

    shorts = mexorders.get_position_size('short')
    longs = mexorders.get_position_size('long')
    (last, vwap) = mexorders.get_last_and_vwap();
    #buybelow   =  10000
    buybelow  = vwap
    #sellabove  =  1000          
    sellabove = vwap
    
    # if 1d kvo has flipped, flip positions
    if curr_hist_positive and not last_hist_positive:
        if last < buybelow:
            if shorts>longs:
                entryprice = mexorders.get_positions()[0]['avgCostPrice']
                breakEvenPrice = mexorders.get_positions()[0]['breakEvenPrice']
                if breakEvenPrice - last> 15:            
                    mexorders.cancel_open_orders()
                    time.sleep(1)
                    #mexorders.smart_order('Buy', shorts+config.ordersize)
                    send_sms("%s %s %s %s %s" % (                                                    \
                                ("\nBuy signal!! KVO flipped positive and price is: " + str(last)),    \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nCurrently net short with Average entry: "+ str(entryprice)),    \
                                (" and Breakeven at " + str(breakEvenPrice)),                        \
                                (".\nClosing short in profit and Going Long")))                            
                    #report_trade("Closing short and Going Long", shorts+config.ordersize, longs+config.ordersize, last)
                else:
                    send_sms("%s %s %s %s %s" % (                                                    \
                                ("\nBuy signal!! KVO flipped positive and price is: " + str(last)),    \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nUnderwater short with Average entry: "+ str(entryprice)),       \
                                (" and Breakeven at " + str(breakEvenPrice)),                        \
                                (".\nSo not going long yet.")))                      
            else:
                mexorders.cancel_open_orders()
                time.sleep(1)
                #mexorders.smart_order('Buy', shorts+config.ordersize)
                if longs==0:
                    send_sms("%s %s %s" % (                                                          \
                                ("\nBuy signal!! KVO flipped positive and price is: " + str(last)),    \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nGoing Long")))                      
                    #report_trade("GOING LONG", shorts+config.ordersize, longs+config.ordersize, last)
                else:
                    send_sms("%s %s %s" % (                                                          \
                                ("\nBuy signal!! KVO flipped positive and price is: " + str(last)),    \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nAdding to Long")))                      
                    #report_trade("Adding to LONG", shorts+config.ordersize, longs+config.ordersize, last)
        
        else:
            send_sms("%s %s %s" % (                                                                  \
                                ("\nKVO flipped positive and price is: " + str(last)),                 \
                                (". But VWAP is: " + str(vwap)),                                     \
                                (".\nSo not going Long"))) 
            
    elif not curr_hist_positive and last_hist_positive:
        if last > sellabove:
            if longs>shorts:
                entryprice = mexorders.get_positions()[0]['avgCostPrice']
                breakEvenPrice = mexorders.get_positions()[0]['breakEvenPrice']
                if last - breakEvenPrice > 15:            
                    mexorders.cancel_open_orders()
                    time.sleep(1)
                    #mexorders.smart_order('Sell', longs+config.ordersize)
                    send_sms("%s %s %s %s %s" % (                                                    \
                                ("\nSell signal!! KVO flipped negative and price is: " + str(last)),   \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nCurrently net long with Average entry: "+ str(entryprice)),     \
                                (" and Breakeven at " + str(breakEvenPrice)),                        \
                                (".\nClosing long in profit and Going short")))                                                
                    #report_trade("Closing long and Going short", longs+config.ordersize, shorts+config.ordersize, last)                    
                else:
                    send_sms("%s %s %s %s %s" % (                                                    \
                                ("Sell signal!! KVO flipped negative and price is: " + str(last)),   \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nUnderwater long with Average entry: "+ str(entryprice)),        \
                                (" and Breakeven at " + str(breakEvenPrice)),                        \
                                (".\nSo not going short yet.")))                      
            else:
                mexorders.cancel_open_orders()
                time.sleep(1)
                #mexorders.smart_order('Buy', longs+config.ordersize)
                if longs==0:
                    send_sms("%s %s %s" % (                                                          \
                                ("\nSell signal!! KVO flipped negative and price is: " + str(last)),   \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\Going short")))                      
                    #report_trade("GOING short", longs+config.ordersize, shorts+config.ordersize, last)
                else:
                    send_sms("%s %s %s" % (                                                          \
                                ("\nSell signal!! KVO flipped negative and price is: " + str(last)),   \
                                (". VWAP is: " + str(vwap)),                                         \
                                (".\nAdding to short")))                      
                    #report_trade("Adding to short", longs+config.ordersize, shorts+config.ordersize, last)
    
                
        else:
            send_sms("%s %s %s" % (                                                                  \
                                ("\nKVO flipped negative and price is: " + str(last)),                 \
                                (". But VWAP is: " + str(vwap)),                                     \
                                (".\nSo not going short")))         

    last_hist_positive = curr_hist_positive

    # now print some status info
    mexorders.print_positions()
    mexorders.print_open_orders()
    totalbal = mexorders.get_balance_total()
    freebal = mexorders.get_balance_free()
    log.info(" Last price is: %.4f, VWAP is %.4f" %(last, vwap))
    log.info("Total Balance: %.4f, Free Balance: %.4f" % (totalbal, freebal))
    log.info( "Loop completed, sleeping for %d seconds" % sleeptime)
    time.sleep(sleeptime)