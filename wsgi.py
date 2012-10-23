# coding: utf-8

import datetime
import gevent.monkey; gevent.monkey.patch_all()
import gevent.pywsgi
import os
import re
import sys

import cgi
import Cookie
import jinja2

import urllib2
import pymongo

PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(PATH)

import config
import bot

con = pymongo.Connection()
db = con[config.SIRC_DB]
db.authenticate(config.SIRC_DB_USER, config.SIRC_DB_PASS)

def application(environ, start_response):
	cookie = Cookie.SimpleCookie()
	cookie.load(environ.get('HTTP_COOKIE', ''))
	
	oauth_config = None
	if config.OAUTH_PROVIDER in cookie:
		oauth_provider = cookie[config.OAUTH_PROVIDER].value
		if oauth_provider in config.OAUTH:
			oauth_config = config.OAUTH[oauth_provider]

	path = environ.get('PATH_INFO', '')
	if path.startswith('/callback/'):
		if oauth_config is None:
			return error(start_response, message = 'callback')
		return callback(environ, start_response, oauth_config, oauth_provider)

	authorized = False
	session = None
	if config.SESSION_ID in cookie:
		sessions = db.session.find({'session_id': cookie[config.SESSION_ID].value})
		if sessions.count() > 0:
			session = sessions[0]
	if session is None:
		if oauth_config is None:
			return preauth(environ, start_response)
		else:
			return auth(environ, start_response, oauth_config)
	
	db.session.update({
		'session_id': session['session_id']
	}, {
		'$set': {'datetime': datetime.datetime.now()}
	})
	parameters = cgi.parse_qs(environ.get('QUERY_STRING', ''))

	if path.startswith('/update/'):
		return update(environ, start_response, session, parameters)
	elif path.startswith('/downdate/'):
		return downdate(environ, start_response, session, parameters)
	elif path.startswith('/send/'):
		return send(environ, start_response, session, parameters)
	elif path.startswith('/delete/'):
		return delete(environ, start_response, session, parameters)
	elif path == '/':
		return default(environ, start_response, session, parameters)
	else:
		return static(environ, start_response)

def preauth(environ, start_response):
	context = {}
	start_response('200 OK', [
		('Content-Type', 'text/html; charset=utf-8')
	])
	context['OAUTH_PROVIDER'] = config.OAUTH_PROVIDER
	context['oauth'] = config.OAUTH.keys()
	return [render('preauth.html', context)]

def auth(environ, start_response, oauth_config):
	(url, secret) = request_request_token(oauth_config)
	start_response('200 OK', [
		('Refresh', '0; url=%s' % url),
		('Content-Type', 'text/html; charset=utf-8'),
		('Set-Cookie', '%s=%s; path=/' % (config.TOKEN_SECRET, secret))
	])
	return ['<a href="%s">Login Required</a>' % url]

def callback(environ, start_response, oauth_config, oauth_provider):
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
	parameters = cgi.parse_qs(request_access_token(oauth_token, oauth_token_secret, oauth_verifier, oauth_config))
	if oauth_provider == 'snucse' and 'account' in parameters:
		account = parameters['account'][0]
	elif oauth_provider == 'twitter' and 'screen_name' in parameters:
		account = parameters['screen_name'][0]
	else:
		return error(start_response, message = 'account')
	session_id = create_session_id()
	shown_account = '%s%s' % (config.OAUTH[oauth_provider]['PREFIX'], account)
	data = {
		'session_id': session_id,
		'account': shown_account,
		'datetime': datetime.datetime.now()
	}
	db.session.insert(data)
	start_response('200 OK', [
		('Refresh', '0; url=/'),
		('Content-Type', 'text/html; charset=utf-8'),
		('Set-Cookie', '%s=%s; path=/' % (config.SESSION_ID, session_id))
	])
	return ['<a href="/">%s Go</a>' % account]

def update(environ, start_response, session, parameters):
	context = {}
	if 'channel' not in parameters:
		return error(start_response, message = 'no channel')
	last_update = datetime.datetime.now()
	if 'last_update' in parameters:
		last_update = parse_datetime(parameters['last_update'][0].decode('utf-8'))
	if 'transition_id' not in parameters:
		return error(start_response, message = 'no transition_id')
	channel = parameters['channel'][0].lower()#.decode('utf-8').lower()
	#channel is percent-encoded now
	channel_encoded = urllib2.quote(channel)

	transition_id = parameters['transition_id'][0].decode('utf-8')
	if db[session['account']].find({'channel': channel}).count() == 0:
		db[session['account']].insert({'channel': channel})
	context['channel'] = channel
	context['transition_id'] = transition_id
	logs = []
	for i in xrange(30):
		logs = list(db[channel_encoded].find({
			'datetime': {"$gt": last_update},
		}, sort = [
			('datetime', pymongo.ASCENDING)
		]))
		if len(logs) == 0:
			gevent.sleep(1)
		else:
			break
	for log in logs:
		log['source'] = remove_invalid_utf8_char(log['source'])
		log['message'] = remove_invalid_utf8_char(log['message'])
	context['logs'] = logs
	start_response('200 OK', [('Content-Type', 'text/xml; charset=utf-8')])
	return [render('result.xml', context)]

def downdate(environ, start_response, session, parameters):
	context = {}
	if 'channel' not in parameters:
		return error(start_response, message = 'no channel')
	last_downdate = datetime.datetime.now()
	if 'last_downdate' in parameters:
		last_downdate = parse_datetime(parameters['last_downdate'][0].decode('utf-8'))
	if 'transition_id' not in parameters:
		return error(start_response, message = 'no transition_id')
	channel = parameters['channel'][0].lower()#.decode('utf-8').lower()
	channel_encoded = urllib2.quote(channel) #channel name is percent-encoded

	transition_id = parameters['transition_id'][0].decode('utf-8')
	context['channel'] = channel
	context['transition_id'] = transition_id
	logs = db[channel_encoded].find({
		'datetime': {"$lt": last_downdate},
	}, limit = config.N_LINES, sort = [
		('datetime', pymongo.DESCENDING)
	])
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
	#send db에 넣을 때는 percent-encode할 필요가 없다
	channel = parameters['channel'][0].decode('utf-8').lower()
	message = parameters['message'][0].decode('utf-8')
	db.send.insert({
		'account': session['account'],
		'channel': channel,
		'message': message
	})
	context['logs'] = [{
		'source': config.BOT_NAME,
		'message': '<%s> %s' % (remove_invalid_utf8_char(session['account']), remove_invalid_utf8_char(message)),
		'datetime': datetime.datetime.now()
	}]
	start_response('200 OK', [('Content-Type', 'text/xml; charset=utf-8')])
	return [render('result.xml', context)]

def delete(environ, start_response, session, parameters):
	if 'channel' not in parameters:
		return error(start_response, message = 'no channel')
	channel = parameters['channel'][0].decode('utf-8').lower()
	db[session['account']].remove({'channel': channel})
	start_response('200 OK', [])
	return []

def default(environ, start_response, session, parameters):
	context = {}
	context['account'] = session['account']
	context['channels'] = db[session['account']].find(fields = ['channel'])
	db.session.remove({'datetime': {'$lt': datetime.datetime.now() - datetime.timedelta(1)}})
	start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
	return [render('channel.html', context)]

def static(environ, start_response):
	import mimetypes
	path = environ.get('PATH_INFO', '')
	assert '..' not in path
	assert path.startswith('/')
	file_path = os.path.join(PATH + '/static', os.path.normpath(path[1:]))
	content_type, content_encoding = mimetypes.guess_type(file_path)
	header = []
	if content_type:
		header.append(('Content-Type', content_type))
	if content_encoding:
		header.append(('Content-Encoding', content_encoding))
	start_response('200 OK', header)
	return open(file_path, 'rb')

def render(template, context):
	return jinja2.Environment(loader=jinja2.FileSystemLoader(PATH + '/render')).get_template(template).render(context).encode('utf-8')

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

def parse_datetime(s):
	if '.' in s:
		return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f')
	else:
		return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')

def request_request_token(oauth_config):
	import oauth2
	import httplib2
	consumer = oauth2.Consumer(oauth_config['CONSUMER_KEY'], oauth_config['CONSUMER_SECRET'])
	request = oauth2.Request.from_consumer_and_token(consumer, http_url=oauth_config['REQUEST_URL'], parameters={'oauth_callback': config.CALLBACK_URL})
	request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, None)
	response = httplib2.Http().request(request.to_url())
	if response[0]['status'] != '200':
		raise Exception(response)
	token = oauth2.Token.from_string(response[1])
	return ('%s?oauth_token=%s' % (oauth_config['AUTHORIZE_URL'], token.key), token.secret)

def request_access_token(oauth_token, oauth_token_secret, oauth_verifier, oauth_config):
	import oauth2
	import httplib2
	token = oauth2.Token(oauth_token, oauth_token_secret)
	token.set_verifier(oauth_verifier)
	consumer = oauth2.Consumer(oauth_config['CONSUMER_KEY'], oauth_config['CONSUMER_SECRET'])
	request = oauth2.Request.from_consumer_and_token(consumer, token=token, http_url=oauth_config['ACCESS_URL'], is_form_encoded=True)
	request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
	response = httplib2.Http().request(request.to_url())
	if response[0]['status'] != '200':
		raise Exception(response)
	return response[1]

pattern = re.compile("[\x00-\x1F]|[\x80-\x9F]", re.UNICODE)
def remove_invalid_utf8_char(s):
	return pattern.sub(u'�', s)

if __name__ == '__main__':
	bot = bot.SBot()
	gevent.spawn(bot.start)
	server = gevent.pywsgi.WSGIServer(('0.0.0.0', config.SIRC_PORT), application)
	server.serve_forever()

