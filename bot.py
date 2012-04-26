# coding: utf-8

import ircbot
import irclib

import pymongo

import datetime

import config

class SBot(ircbot.SingleServerIRCBot):
	def __init__(self):
		ircbot.SingleServerIRCBot.__init__(self,
			[(config.SERVER, config.PORT), ],
			config.BOT_NAME,
			'm',
		)
		self.connected = False

		connection = pymongo.Connection()
		self.db = connection.sirc_db
		self.db.send.remove()
		self._fetch()
	
	def on_welcome(self, c, e):
		self.connected = True

	def on_nick(self, c, e):
		before = e.source().split('!')[0]
		after = e.target()
		for target, ch in self.channels.items():
			if ch.has_user(before):
				self._log(target, '!', '<%s> is now known as <%s>.' % (before, after))
	
	def on_join(self, c, e):
		nick = e.source().split('!')[0]
		self._log(e.target(), '!', '<%s> has joined.' % nick)

	def on_part(self, c, e):
		nick = e.source().split('!')[0]
		self._log(e.target(), '!', '<%s> has left.' % nick)
	
	def on_quit(self, c, e):
		nick = e.source().split('!')[0]
		for target, ch in self.channels.items():
			if ch.has_user(nick):
				self._log(target, '!', '<%s> has quit.' % nick)
	
	def on_kick(self, c, e):
		nick_s = e.source().split('!')[0]
		nick_m = e.arguments()[0]
		because_of = e.arguments()[1]
		self._log(e.target(), '!', '<%s> was kicked by <%s> because of "%s".' % (nick_m, nick_s, because_of))
	
	def on_pubmsg(self, c, e):
		self._log(e.target(), e.source().split('!')[0], e.arguments()[0])

	def _log(self, target, source, message):
		data = {
			'datetime': datetime.datetime.now(),
			'source': source,
			'message': message,
		}
		try:
			self.db[target].insert(data)
		except:
			pass
	
	def _fetch(self):
		if self.connected:
			try:
				for data in self.db.send.find():
					channel = data['channel'].encode('utf-8')
					if channel not in self.channels:
						self.connection.join(channel)
					account = data['account'].encode('utf-8')
					message = ('<%s> %s' % (account, data['message'])).encode('utf-8')
					self.connection.privmsg(channel, message)
					self._log(channel, self._nickname, message)
					self.db.send.remove(data)
			except irclib.ServerNotConnectedError:
				self.connected = False
				self._connect()
		self.ircobj.execute_delayed(1, self._fetch)

if __name__ == '__main__':
	bot = SBot()
	bot.start()

