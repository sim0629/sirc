# coding: utf-8

import datetime
import os
import sys

import cgi
import Cookie
import jinja2

import pymongo

PATH = os.path.dirname(os.path.realpath(__file__))
TARGET = '#snucse12'
SESSION_ID = 'SIRC_SESSION_ID'
TOKEN_SECRET = 'OAUTH_TOKEN_SECRET'
sys.path.append(PATH)

from config import *

def application(environ, start_response):
	if not OPEN:
		return test(start_response, '점검 중')

	path = environ.get('PATH_INFO', '')
	context = {}

	con = pymongo.Connection()
	db = con.sirc_db
	
	# callback
	if path.startswith('/callback/'):
		parameters = cgi.parse_qs(environ.get('QUERY_STRING', ''))
		if 'oauth_token' in parameters and \
			'oauth_verifier' in parameters:
			oauth_token = parameters['oauth_token'][0]
			oauth_verifier = parameters['oauth_verifier'][0]
		else:
			return error(start_response)
		cookie = Cookie.SimpleCookie()
		cookie.load(environ.get('HTTP_COOKIE', ''))
		if TOKEN_SECRET in cookie:
			oauth_token_secret = cookie[TOKEN_SECRET].value
		else:
			return error(start_response)
		parameters = cgi.parse_qs(callback(oauth_token, oauth_token_secret, oauth_verifier))
		if 'account' in parameters:
			account = parameters['account'][0]
		else:
			return error(start_response)
		session_id = create_session_id()
		data = {
			'session_id': session_id,
			'account': account,
			'datetime': datetime.datetime.now()
		}
		db.session.insert(data)
		start_response('200 OK', [('Refresh', '0; url=/sgm'), ('Content-Type', 'text/html; charset=utf-8'), ('Set-Cookie', '%s=%s; path=/sgm' % (SESSION_ID, session_id))])
		return ['<a href="/sgm">Go</a>']

	# auth
	cookie = Cookie.SimpleCookie()
	cookie.load(environ.get('HTTP_COOKIE', ''))
	authorized = False
	if SESSION_ID in cookie:
		sessions = db.session.find({'session_id': cookie[SESSION_ID].value})
		authorized = not not sessions
	if authorized:
		session = sessions[0]
	else:
		(url, secret) = request()
		start_response('200 OK', [('Refresh', '0; url=%s' % url), ('Content-Type', 'text/html; charset=utf-8'), ('Set-Cookie', '%s=%s' % (TOKEN_SECRET, secret))])
		return ['<a href="%s">SNUCSE Login Required</a>' % url]
	
	# update
	if path.startswith('/update/'):
		logs = db[TARGET].find({'datetime': {"$gt": session['datetime']}}).sort('datetime')
		db.session.update({'session_id': session['session_id']}, {'$set': {'datetime': datetime.datetime.now()}})
		context['logs'] = logs
		start_response('200 OK', [('Content-Type', 'text/xml; charset=utf-8')])
		return [render('result.xml', context)]

	# send
	elif path.startswith('/send/'):
		parameters = cgi.parse_qs(environ.get('QUERY_STRING', ''))
		message = parameters['message'][0].decode('utf-8')
		db.send.insert({'account': session['account'], 'message': message})
		start_response('200 OK', [])
		return []
		'''
		d = datetime.datetime.now()
		db.session.update({'session_id': session['session_id']}, {'$set': {'datetime': d}})
		start_response('200 OK', [('Content-Type', 'text/xml; charset=utf-8')])
		return [render('result.xml', {'logs': [{'datetime': d, 'source': 's><%s' % session['account'], 'message': message}]})]
		'''

	# default
	db[TARGET].remove({'datetime': {'$lt': datetime.datetime.now() - datetime.timedelta(1)}})
	logs = db[TARGET].find().sort('datetime')
	db.session.update({'session_id': session['session_id']}, {'$set': {'datetime': datetime.datetime.now()}})
	logs = list(logs)
	for log in logs:
		log['message'] = cgi.escape(log['message'])
	context['logs'] = logs

	start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
	return [render('chat.html', context)]

def render(template, context):
	return jinja2.Environment(loader=jinja2.FileSystemLoader(PATH + '/public_html')).get_template(template).render(context).encode('utf8')

def error(start_response):
	start_response('404 NOT FOUND', [])
	return []

def test(start_response, message):
	start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
	return [message]

def create_session_id():
	import string
	import random

	bag = string.ascii_uppercase + string.ascii_lowercase + string.digits
	return ''.join(random.sample(bag * 24, 24))

def request():
	import oauth2
	import httplib2
	
	REQUEST_URL = 'https://www.snucse.org/app/RequestToken'
	CALLBACK_URL = 'http://sirc.neria.kr:8000/sgm/callback/'
	AUTHORIZE_URL = 'https://www.snucse.org/app/Authorize'

	consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
	request = oauth2.Request.from_consumer_and_token(consumer, http_url=REQUEST_URL, parameters={'oauth_callback': CALLBACK_URL})
	request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, None)
	response = httplib2.Http().request(request.to_url())
	token = oauth2.Token.from_string(response[1])
	return ('%s?oauth_token=%s' % (AUTHORIZE_URL, token.key), token.secret)

def callback(oauth_token, oauth_token_secret, oauth_verifier):
	import oauth2
	import httplib2

	ACCESS_URL = 'https://www.snucse.org/app/AccessToken'

	token = oauth2.Token(oauth_token, oauth_token_secret)
	token.set_verifier(oauth_verifier)

	consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
	request = oauth2.Request.from_consumer_and_token(consumer, token=token, http_url=ACCESS_URL)
	#return str(request)
	request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
	#return request.to_url()
	response = httplib2.Http().request(request.to_url())
	return response[1]

