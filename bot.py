# coding: utf-8

import ircbot
import irclib

import pymongo

import datetime

#.strftime('%Y-%m-%d %H:%M:%S')
#pymongo.Connection().sirc_db['#sgm'].remove() #ereate_index([('datetime', 1)])
#exit()
TARGET = '#snucse12'

class SBot(ircbot.SingleServerIRCBot):
	def __init__(self):
		ircbot.SingleServerIRCBot.__init__(self,
			[('115.92.130.250', 16667), ],
			's',
			'm',
		)
		self.connected = False

		connection = pymongo.Connection()
		self.db = connection.sirc_db
		self.db.send.remove()
		self._fetch()
	
	def on_welcome(self, c, e):
		c.join(TARGET)
		self.connected = True
	
	def on_pubmsg(self, c, e):
		self._log(e.target(), e.source().split('!')[0], e.arguments()[0])

	def _log(self, target, source, message):
		data = {'datetime': datetime.datetime.now(),
				'source': source,
				'message': message
		}
		try:
			self.db[target].insert(data)
			#print '_log_%s' % message
		except:
			pass
	
	def _fetch(self):
		if self.connected:
			try:
				for data in self.db.send.find():
					account = data['account'].encode('utf-8')
					message = ('<%s> %s' % (account, data['message'])).encode('utf-8')
					self.connection.privmsg(TARGET, message)
					self.db.send.remove(data)
					self._log(TARGET, self._nickname, message)
			except irclib.ServerNotConnectedError:
				self._connect()
		self.ircobj.execute_delayed(1, self._fetch)

if __name__ == '__main__':
	bot = SBot()
	bot.start()

