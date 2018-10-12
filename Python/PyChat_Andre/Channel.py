
class Channel:
    def __init__(self, name):
        self.clients = {} # Client Name -> Socket
        self.channel_name = name

    def welcome_client(self, clientName):
        for name, socket in self.clients.items():
            if name is clientName:
                chatMessage = '\n\n> {0} have joined the channel {1}!\n'.format("You", self.channel_name)
                socket.sendall(chatMessage.encode('utf8'))
            else:
                chatMessage = '\n\n> {0} has joined the channel {1}!\n'.format(clientName, self.channel_name)
                socket.sendall(chatMessage.encode('utf8'))

    def broadcast_message(self, chatMessage, clientName=''):
        for name, socket in self.clients.items():
            if name is clientName:
                socket.sendall(("You: " + chatMessage).encode('utf8'))
            else:
                socket.sendall((clientName + chatMessage).encode('utf8'))

    def remove_client_from_channel(self, clientName):
        del self.clients[clientName]
        leave_message = "\n" + clientName + " has left the channel " + self.channel_name + "\n"
        self.broadcast_message(leave_message)
