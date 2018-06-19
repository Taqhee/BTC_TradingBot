#!/usr/bin/python3

from __future__ import print_function, division, unicode_literals
from config import twilio_conf
from twilio.rest import Client

client = None
if twilio_conf['account_sid'] and twilio_conf['auth_token']:
	client = Client(twilio_conf['account_sid'], twilio_conf['auth_token'])

def send_sms(message):
	if client:
		client.api.account.messages.create(
				to=twilio_conf['tonumber'],
				from_=twilio_conf['fromnumber'],
				body=twilio_conf['msgprefix']+message)


