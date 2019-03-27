import sys

from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import *
import pika
from pyrabbit.api import Client
import time

class MainWindow(QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
		loadUi('chat.ui', self)
		self.username = QInputDialog.getText(self, 'Zdarova', 'User name:')

		self.history = ''

		if not self.username[1]:
			return

		self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
		self.channel = self.connection.channel()

		self.channel.exchange_declare(exchange='ex', exchange_type='topic')
		self.channel.exchange_declare(exchange='exx', exchange_type='fanout')
		self.channel.queue_declare(queue = self.username[0])
		self.channel.queue_bind(exchange='ex', queue=self.username[0], routing_key=self.username[0])
		self.channel.queue_bind(exchange='exx', queue=self.username[0])
		self.model = QStandardItemModel()
		self.textEdit = QTextEdit()
		self.textEdit.setReadOnly(True)
		self.tabWidget.addTab(self.textEdit, 'Общий чат')

		self.timer = QTimer()
		self.timer.timeout.connect(self.update)
		self.timer.start(1000)

		self.cl = Client('localhost:15672', 'guest', 'guest')

		self.btnSend.clicked.connect(self.send)
		self.listView.clicked.connect(self.lsopen)
		self.tabWidget.tabCloseRequested.connect(self.closeTab)
		self.tabWidget.currentChanged.connect(self.changeTab)

		self.listView.customContextMenuRequested.connect(self.popUp)

		self.blackList = list()

	def popUp(self, position):
		menu = QMenu("Menu", self)
		menu.addAction("Заблокировать").connect(self.block)
		menu.exec_(self.listView.mapToGlobal(position))

	def block(self):
		print(1)

	def changeTab(self, index):
		self.textEditLs = self.tabWidget.currentWidget()

	def closeTab(self, index):
		if index == 0:
			return
		self.tabWidget.removeTab(index)

	def lsopen(self, index):
		if not index.isValid():
			return
		for i in range(1, self.tabWidget.count()):
			if self.tabWidget.tabText(i) == self.listView.model().data(index):
				self.tabWidget.setCurrentIndex(i)
				self.textEditLs = self.tabWidget.currentWidget()
				return

		self.textEditLs = QTextEdit()
		self.textEditLs.setReadOnly(True)
		self.tabWidget.addTab(self.textEditLs, self.listView.model().data(index))
		self.tabWidget.setCurrentIndex(self.tabWidget.count()-1)

	def __del__(self):
		self.timer.stop()
		self.channel.queue_delete(queue = self.username[0])
		self.connection.close()

	def send(self):
		message = time.ctime() + ' ' + self.username[0] + ': ' + self.edtMes.text() + '\n'
		if self.tabWidget.currentIndex() == 0:
			self.channel.basic_publish(exchange='exx', routing_key='', body = message)
		else:
			self.channel.basic_publish(exchange='ex', routing_key=self.tabWidget.tabText(self.tabWidget.currentIndex()), body = message)
			self.channel.basic_publish(exchange='ex', routing_key=self.tabWidget.tabText(self.tabWidget.currentIndex()), body = self.username[0])
			self.textEditLs.append(message)
		self.edtMes.clear()

	def update(self):
		self.timer.stop()
		queues = [q['name'] for q in self.cl.get_queues()]
		self.model.clear()
		for i in range(len(queues)):
			item = QStandardItem(queues[i])
			if queues[i] == self.username[0]:
				font = item.font()
				font.setBold(True)
				item.setFont(font)
			self.model.setItem(i, item)
		self.listView.setModel(self.model)



		method, properties, body = self.channel.basic_get(queue = self.username[0])
		if(method == None):
			self.timer.start(1000)
			return
		elif method.routing_key == self.username[0]:
			method2, properties2, body2 = self.channel.basic_get(queue = self.username[0])
			for i in range(1, self.tabWidget.count()):
				if self.tabWidget.tabText(i) == body2.decode('utf-8'):
					self.tabWidget.setCurrentIndex(i)
					self.textEditLs = self.tabWidget.currentWidget()
					self.textEditLs.append(body.decode('utf-8'))
					self.timer.start(1000)
					return
			self.textEditLs = QTextEdit()
			self.textEditLs.setReadOnly(True)
			self.tabWidget.addTab(self.textEditLs, body2.decode('utf-8'))
			self.textEditLs.append(body.decode('utf-8'))
			self.timer.start(1000)
		else:
			self.textEdit.append(body.decode('utf-8'))
		self.timer.start(1000)



app = QApplication(sys.argv)
widget = MainWindow()
widget.show()

sys.exit(app.exec_())