import socket
import sys

class Client:
    def __init__(self, name='client user'):
        self.socket = None
        self.isClientConnected = False

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.connect((host, port))
            self.isClientConnected = True
        except socket.error as errorMessage:
            if errorMessage.errno == socket.errno.ECONNREFUSED:
                sys.stderr.write('Connection refused to ' + str(host) + ' on port ' + str(port))
            else:
                sys.stderr.write('Error, unable to connect: ' + str(errorMessage))

    def disconnect(self):
        if self.isClientConnected:
            self.socket.close()
            self.isClientConnected = False

    def send(self, data):
        if self.isClientConnected:
            self.socket.send(data.encode('utf8'))

    def receive(self, size=4096):
        if not self.isClientConnected:
            return ""

        return self.socket.recv(size).decode('utf8')
