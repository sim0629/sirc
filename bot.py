# coding: utf-8

import ircbot
import irclib

import pymongo
import datetime

import config

import urllib2 # only for quote

class SBot(ircbot.SingleServerIRCBot):
	def __init__(self):
		ircbot.SingleServerIRCBot.__init__(self,
			[(config.SERVER, config.PORT), ],
			config.BOT_NAME,
			'm',
		)
		self.connected = False

		connection = pymongo.Connection()
		self.db = connection[config.SIRC_DB]
		self.db.send.remove()
		self._fetch()
	
	def on_welcome(self,c, e):
		self.connected = True
		for target in self.db.collection_names(): #extract last channels the user used
			target = urllib2.unquote(target.encode("utf-8"))
			if target.startswith('#'): # TODO: is_channel?
				c.join(target) #==self.connect.join(target)
	
	def on_mode(self, c, e):
		nick = irclib.nm_to_n(e.source())
		target = e.target()
		if irclib.is_channel(target):
			self._log(target, config.NOTIFY_NAME, '[%s] by <%s>.' % (' '.join(e.arguments()), nick))
		else:
			pass

	def on_nick(self, c, e):
		before = irclib.nm_to_n(e.source())
		after = e.target()
		for target, ch in self.channels.items():
			if ch.has_user(before):
				self._log(target, config.NOTIFY_NAME, '<%s> is now known as <%s>.' % (before, after))
	
	def on_join(self, c, e):
		nick = irclib.nm_to_n(e.source())
		self._log(e.target(), config.NOTIFY_NAME, '<%s> has joined.' % nick)

	def on_part(self, c, e):
		nick = irclib.nm_to_n(e.source())
		self._log(e.target(), config.NOTIFY_NAME, '<%s> has left.' % nick)
	
	def on_quit(self, c, e):
		nick = irclib.nm_to_n(e.source())
		for target, ch in self.channels.items():
			if ch.has_user(nick):
				self._log(target, config.NOTIFY_NAME, '<%s> has quit.' % nick)
	
	def on_kick(self, c, e):
		nick_s = irclib.nm_to_n(e.source())
		nick_m = e.arguments()[0]
		because_of = e.arguments()[1]
		self._log(e.target(), config.NOTIFY_NAME, '<%s> was kicked by <%s> because of "%s".' % (nick_m, nick_s, because_of))
	#딴사람이 메시지를 썼을때
	def on_pubmsg(self, c, e): #c는 커넥트된 서버, 허나 이미 connection이라는 멤버 변수가 있으므로 그렇게 필요가 있을까?=>
		nick = irclib.nm_to_n(e.source())# e: Event객체(source와 target이 있음)
		target = e.target()
		message = e.arguments()[0]
		self._log(target, nick, message)
		if self.channels[target].is_oper(c.get_nickname()) and \
			nick == config.OPERATOR_NAME and \
			message.startswith(config.OPERATOR_COMMAND):
			self.connection.mode(target, '+o %s' % nick)
	def _log(self, target, source, message):
		data = {
			'datetime': datetime.datetime.now(),
			'source': source,
			'message': message,
		}
		try:
			channel = target.lower()
			channel = urllib2.quote(channel) # percent encoding to deal with hangul channel
			self.db[channel].insert(data)
		except:
			pass
	#send에 들어있는 것=>irc 서버로 전송
	#자동으로 불림
	def _fetch(self):
		if self.connected:
			try:
				for data in self.db.send.find():
					channel = data['channel'].lower().encode('utf-8').lower()
					
					if channel not in self.channels:
						self.connection.join(channel)
					account = data['account'].encode('utf-8')
					message = ('<%s> %s' % (account, data['message'])).encode('utf-8')
					self.connection.privmsg(channel, message) #중요: 메시지 보냄
					self._log(channel, self._nickname, message)
					self.db.send.remove(data)
			except irclib.ServerNotConnectedError:
				self.connected = False
				self._connect()
		self.ircobj.execute_delayed(1, self._fetch) # 1초마다 fetch하는 함수

if __name__ == '__main__':
	bot = SBot()
	bot.start()

