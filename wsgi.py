# coding: utf-8

import datetime
import gevent
import os
import re
import sys

import cgi
import Cookie
import jinja2

import pymongo

PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(PATH)

import config

con = pymongo.Connection()
db = con.sirc_db

def application(environ, start_response):
	if not config.OPEN:
		return error(start_response, '503 Service Unavailable', '점검 중')

	path = environ.get('PATH_INFO', '')
	if path.startswith('/callback/'):
		return callback(environ, start_response)

	cookie = Cookie.SimpleCookie()
	cookie.load(environ.get('HTTP_COOKIE', ''))
	authorized = False
	session = None
	if config.SESSION_ID in cookie:
		sessions = db.session.find({'session_id': cookie[config.SESSION_ID].value})
		if sessions.count() > 0:
			session = sessions[0]
	if session is None:
		return auth(environ, start_response)
	
	db.session.update({
		'session_id': session['session_id']
	}, {
		'$set': {'datetime': datetime.datetime.now()}
	})
	parameters = cgi.parse_qs(environ.get('QUERY_STRING', ''))

	if path.startswith('/update/'):
		return update(environ, start_response, session, parameters)
	elif path.startswith('/send/'):
		return send(environ, start_response, session, parameters)
	else:
		return default(environ, start_response, session, parameters)

def auth(environ, start_response):
	(url, secret) = request_request_token()
	start_response('200 OK', [
		('Refresh', '0; url=%s' % url),
		('Content-Type', 'text/html; charset=utf-8'),
		('Set-Cookie', '%s=%s; path=/sgm; expires=%s' % (config.TOKEN_SECRET, secret, (datetime.datetime.now() + datetime.timedelta(minutes = 1)).strftime('%a, %d %b %Y %H:%M:%S')))
	])
	return ['<a href="%s">SNUCSE Login Required</a>' % url]

def callback(environ, start_response):
	parameters = cgi.parse_qs(environ.get('QUERY_STRING', ''))
	if 'oauth_token' in parameters and \
		'oauth_verifier' in parameters:
		oauth_token = parameters['oauth_token'][0]
		oauth_verifier = parameters['oauth_verifier'][0]
	else:
		return error(start_response, message = 'oauth')
	cookie = Cookie.SimpleCookie()
	cookie.load(environ.get('HTTP_COOKIE', ''))
	if config.TOKEN_SECRET in cookie:
		oauth_token_secret = cookie[config.TOKEN_SECRET].value
	else:
		return error(start_response, message = 'secret')
	parameters = cgi.parse_qs(request_access_token(oauth_token, oauth_token_secret, oauth_verifier))
	if 'account' in parameters: # snucse
		account = parameters['account'][0]
	elif 'screen_name' in parameters: # twitter
		account = parameters['screen_name'][0]
	else:
		return error(start_response, message = 'account')
	session_id = create_session_id()
	data = {
		'session_id': session_id,
		'account': account,
		'datetime': datetime.datetime.now()
	}
	db.session.insert(data)
	start_response('200 OK', [
		('Refresh', '0; url=/sgm'),
		('Content-Type', 'text/html; charset=utf-8'),
		('Set-Cookie', '%s=%s; path=/sgm' % (config.SESSION_ID, session_id))
	])
	return ['<a href="/sgm">%s Go</a>' % account]

def update(environ, start_response, session, parameters):
	context = {}
	if 'channel' not in parameters:
		return error(start_response, message = 'no channel')
	last_update = datetime.datetime.now() - datetime.timedelta(1)
	if 'last_update' in parameters:
		last_update = datetime.datetime.strptime(parameters['last_update'][0].decode('utf-8'), '%Y-%m-%d %H:%M:%S.%f')
	channel = parameters['channel'][0].decode('utf-8').lower()
	logs = db[channel].find({
		'datetime': {"$gt": last_update},
	}).sort('datetime')
	logs = list(logs)
	for log in logs:
		log['source'] = remove_invalid_utf8_char(log['source'])
		log['message'] = remove_invalid_utf8_char(log['message'])
	context['logs'] = logs
	start_response('200 OK', [('Content-Type', 'text/xml; charset=utf-8')])
	return [render('result.xml', context)]

def send(environ, start_response, session, parameters):
	context = {}
	if 'channel' not in parameters:
		return error(start_response, message = 'no channel')
	if 'message' not in parameters:
		return error(start_response, message = 'no message')
	channel = parameters['channel'][0].decode('utf-8').lower()
	message = parameters['message'][0].decode('utf-8')
	db.send.insert({
		'account': session['account'],
		'channel': channel,
		'message': message
	})
	db[channel].remove({
		'datetime': {'$lt': datetime.datetime.now() - datetime.timedelta(1)}
	})
	context['logs'] = [{
		'flag': 'send',
		'source': config.BOT_NAME,
		'message': '<%s> %s' % (remove_invalid_utf8_char(session['account']), remove_invalid_utf8_char(message)),
		'datetime': datetime.datetime.now()
	}]
	start_response('200 OK', [('Content-Type', 'text/xml; charset=utf-8')])
	return [render('result.xml', context)]

def default(environ, start_response, session, parameters):
	context = {}
	db.session.remove({'datetime': {'$lt': datetime.datetime.now() - datetime.timedelta(1)}})
	start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
	return [render('channel.html', context)]

def render(template, context):
	return jinja2.Environment(loader=jinja2.FileSystemLoader(PATH + '/public_html')).get_template(template).render(context).encode('utf-8')

def error(start_response, code = '404 Not Found', message = 'error'):
	context = {}
	context['message'] = message.decode('utf-8')
	start_response(code, [('Content-Type', 'text/html; charset=utf-8')])
	return [render('error.html', context)]

def create_session_id(): # TODO: 중복 체크
	import string
	import random
	bag = string.ascii_uppercase + string.ascii_lowercase + string.digits
	return ''.join(random.sample(bag * 24, 24))

def request_request_token():
	import oauth2
	import httplib2
	consumer = oauth2.Consumer(config.CONSUMER_KEY, config.CONSUMER_SECRET)
	request = oauth2.Request.from_consumer_and_token(consumer, http_url=config.REQUEST_URL, parameters={'oauth_callback': config.CALLBACK_URL})
	request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, None)
	response = httplib2.Http().request(request.to_url())
	token = oauth2.Token.from_string(response[1])
	return ('%s?oauth_token=%s' % (config.AUTHORIZE_URL, token.key), token.secret)

def request_access_token(oauth_token, oauth_token_secret, oauth_verifier):
	import oauth2
	import httplib2
	token = oauth2.Token(oauth_token, oauth_token_secret)
	token.set_verifier(oauth_verifier)
	consumer = oauth2.Consumer(config.CONSUMER_KEY, config.CONSUMER_SECRET)
	request = oauth2.Request.from_consumer_and_token(consumer, token=token, http_url=config.ACCESS_URL)
	request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
	response = httplib2.Http().request(request.to_url())
	return response[1]

#pattern = re.compile("((?:[\x00-\x7F]|[\xC0-\xDF][\x80-\xBF]|[\xE0-\xEF][\x80-\xBF]{2}|[\xF0-\xF7][\x80-\xBF]{3})+)|([\x80-\xBF])|([\xC0-\xFF])", re.UNICODE)
pattern = re.compile("[\x00-\x1F]|[\x80-\x9F]", re.UNICODE)
def remove_invalid_utf8_char(s):
	#return unicode(s.encode('utf-8'), 'utf-8', 'replace')
	return pattern.sub(u'�', s)
	'''
	matches = pattern.match(s)
	if matches is None:
		return s
	if len(matches.group(1)) != 0:
		return matches.group(1)
	elif len(matches.group(2)) != 0:
		return "\xC2" + matches.group(2)
	else:
		return "\xC3" + chr(ord(matches.group(3)) - 64)
	'''

if __name__ == '__main__':
	print 'Apache와 연동하세요.'

