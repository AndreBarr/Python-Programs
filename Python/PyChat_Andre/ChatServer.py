import socket
import sys
import threading
import Channel
import Users
from time import gmtime, strftime

class Server:
    SERVER_CONFIG = {"MAX_CONNECTIONS": 15}

    HELP_MESSAGE = """\n> The list of commands available are:

/help                           - Show the instructions
/join <channel_name>            - To create or switch to a channel.
/quit                           - Exits the program.
/away <awayMessage>             - Sets an away message. Note: Type /away again to return from away.
/time                           - Returns the time of the current server
/setname <newName>              - Changes your name
/privmsg <msgtarget> <message>  - Sends a message only to the target
/list                           - Lists all available channels.\n\n""".encode('utf8')

    def __init__(self, host=socket.gethostbyname(socket.gethostname()), port=50000, allowReuseAddress=True):
        self.address = (host, port)
        self.channels = {} # Channel Name -> Channel
        self.channels_client_map = {} # Client Name -> Channel Name
        self.server_users = {} # Nick Name -> User (object)

        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("Server IP Address: " + host)
        except socket.error as errorMessage:
            sys.stderr.write("Failed to initialize the server. Error - %s\n", str(errorMessage))
            raise

        if allowReuseAddress:
            self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.serverSocket.bind(self.address)
        except socket.error as errorMessage:
            sys.stderr.write('Failed to bind to ' + self.address + '. Error - %s\n', str(errorMessage))
            raise

    def start_listening(self):
        self.serverSocket.listen(Server.SERVER_CONFIG["MAX_CONNECTIONS"])
        listenerThread = threading.Thread(target=self.listen_thread)
        listenerThread.start()
        listenerThread.join()

    def welcome_client(self, clientSocket):
        clientSocket.sendall("\n> Welcome to our chat app!!! What is your name?\n".encode('utf8'))

    def client_thread(self, clientSocket, size=4096):
        clientName = clientSocket.recv(size).decode('utf8')
        welcomeMessage = '> Welcome %s, type /help for a list of helpful commands.\n\n' % clientName
        clientSocket.send(welcomeMessage.encode('utf8'))
        self.server_users[clientName] = Users.Users(clientName, '', 'User', clientName, clientSocket, False, '')

        while True:
            chatMessage = clientSocket.recv(size).decode('utf8')
            chatCommand = chatMessage.split(' ')[0].lower()

            if not chatMessage:
                break

            if '/quit' in chatCommand:
                self.quit(clientSocket, clientName)
                break
            elif '/list' in chatCommand:
                self.list_all_channels(clientSocket)
            elif '/help' in chatCommand:
                self.help(clientSocket)
            elif '/join' in chatCommand:
                self.join(clientSocket, chatMessage, clientName)
            elif '/away'in chatCommand:
                self.away(clientSocket, chatMessage, clientName)
            elif '/time' in chatCommand:
                self.getTime(clientSocket)
            elif '/setname' in chatCommand:
                clientName = self.setName(clientSocket, chatMessage, clientName)
            elif '/privmsg' in chatCommand:
                self.privateMessage(clientSocket, chatMessage, clientName)
            elif '/ping' in chatCommand:
                self.ping(clientSocket)
            elif '/pong' in chatCommand:
                self.pong(clientSocket)
            elif '/version' in chatCommand:
                self.version(clientSocket)
            elif '/invite' in chatMessage:
                self.invite(clientSocket, chatMessage, clientName)
            elif '/ison' in chatCommand:
                self.ison(clientSocket, chatMessage)
            elif '/knock' in chatCommand:
                self.knock(clientSocket, chatMessage, clientName)
            elif '/nick' in  chatCommand:
                self.setNick(clientSocket, chatMessage, clientName)
            elif '/die' in  chatCommand:
                self.die()
            else:
                self.send_message(clientSocket, chatMessage + '\n' , clientName)

        clientSocket.close()

    def quit(self, clientSocket, clientName):
        clientSocket.sendall('/quit'.encode('utf8'))
        self.remove_client(clientName)

    def list_all_channels(self, clientSocket):
        if len(self.channels) == 0:
            chatMessage = "\n> No rooms available. Create your own by typing /join [channel_name]\n"
            clientSocket.sendall(chatMessage.encode('utf8'))
        else:
            chatMessage = '\n\n> Current channels available are: \n'
            for channel in self.channels:
                chatMessage += "    \n" + channel + ": " + str(len(self.channels[channel].clients)) + " user(s)"
            chatMessage += "\n"
            clientSocket.sendall(chatMessage.encode('utf8'))

    def help(self, clientSocket):
        clientSocket.sendall(Server.HELP_MESSAGE)

    def join(self, clientSocket, chatMessage, clientName):
        isInSameRoom = False

        if len(chatMessage.split()) >= 2:
            channelName = chatMessage.split()[1]

            if clientName in self.channels_client_map: # Here we are switching to a new channel.
                if self.channels_client_map[clientName] == channelName:
                    clientSocket.sendall(("\n> You are already in channel: " + channelName + "\n").encode('utf8'))
                    isInSameRoom = True
                else: # switch to a new channel
                    oldChannelName = self.channels_client_map[clientName]
                    self.channels[oldChannelName].remove_client_from_channel(clientName) # remove them from the previous channel

            if not isInSameRoom:
                if not channelName in self.channels:
                    newChannel = Channel.Channel(channelName)
                    self.channels[channelName] = newChannel

                self.channels[channelName].clients[clientName] = clientSocket
                self.channels[channelName].welcome_client(clientName)
                self.channels_client_map[clientName] = channelName
        else:
            self.help(clientSocket)

    def away(self, clientSocket, chatMessage, clientName):
        if len(chatMessage.split()) < 2:
           if self.server_users[clientName].awayStatus:
               clientSocket.sendall('\n> You are back to the chat.\n'.encode('utf8'))
               self.server_users[clientName].awayStatus = False
        else:
           theAwayMessage = chatMessage.replace("/away", "")
           clientSocket.sendall('\n> You are away from the chat.\n'.encode('utf8'))
           self.server_users[clientName].awayStatus = True
           self.server_users[clientName].awayMessage = theAwayMessage

    def setName(self, clientSocket, chatMessage, clientName):
        if len(chatMessage.split()) < 2:
                clientSocket.sendall('\n> Must provide a name to change to.\n'.encode('utf8'))
                return clientName
        else:
                newName = chatMessage.split()[1]
                self.server_users[clientName].name = newName
                self.server_users[newName] = self.server_users[clientName]
                if clientName in self.channels_client_map:
                    self.channels_client_map[newName] = self.channels_client_map[clientName]
                    self.channels[self.channels_client_map[newName]].clients[newName] = self.channels[self.channels_client_map[clientName]].clients[clientName]
                    del self.channels[self.channels_client_map[clientName]].clients[clientName]
                    del self.channels_client_map[clientName]
                del self.server_users[clientName]
                return newName

    def setNick(self, clientSocket, chatMessage, clientName):
        if len(chatMessage.split()) < 2:
                clientSocket.sendall('\n> Must provide a nickname to change to.\n'.encode('utf8'))
        else:
                newNick = chatMessage.split()[1]
                self.server_users[clientName].nickName = newNick

    def getTime(self, clientSocket):
        time = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        clientSocket.sendall(time.encode('utf8'))

    def privateMessage(self, clientSocket, chatMessage, clientName):
        if len(chatMessage.split()) < 3:
                clientSocket.sendall('\n> Must provide a target name and a message to send.\n'.encode('utf8'))
        else:
                targetName = chatMessage.split()[1]
                privMessage = chatMessage.split()[2]
                if self.server_users[targetName].awayStatus:
                    clientSocket.sendall(('> ' + targetName + ': ' + self.server_users[targetName].awayMessage + '\n').encode('utf8'))
                else:
                    if targetName in self.channels_client_map:
                        targetClient = self.channels[self.channels_client_map[targetName]].clients[targetName]
                        targetClient.send(("PrivMsg> " + clientName + ": "+ privMessage + "\n").encode('utf8'))
                        clientSocket.send(("PrivMsg> " + clientName + ": " + privMessage + "\n").encode('utf8'))
                    else:
                        clientSocket.sendall(('> ' + targetName + ' is not in any channels.\n').encode('utf8'))

    def notice(self, clientSocket, chatMessage, clientName):
        if not len(chatMessage.split()) < 3:
            targetName = chatMessage.split()[1]
            privMessage = chatMessage.split()[2]
            if targetName in self.channels_client_map:
                  targetClient = self.channels[self.channels_client_map[targetName]].clients[targetName]
                  targetClient.send(("Notice> " + clientName + ": "+ privMessage + "\n").encode('utf8'))
            else:
                  clientSocket.sendall(('> ' + targetName + ' is not in any channels.\n').encode('utf8'))

    def ping(self, clientSocket):
        clientSocket.sendall('\nPong\n'.encode('utf8'))

    def pong(self, clientSocket):
        clientSocket.sendall('\nPing\n'.encode('utf8'))

    def version(self, clientSocket):
        clientSocket.sendall('\nVersion: 1.0\n'.encode('utf8'))

    def knock(self, clientSocket, chatMessage, clientName):
        if len(chatMessage.split()) < 2:
            clientSocket.sendall('\n> Must provide a target channel and message to the channel.\n'.encode('utf8'))
        else:
            smallChatMessage = chatMessage.replace('/knock', '')
            targetChannel = chatMessage.split(' ')[1]
            requestMessage = smallChatMessage.replace(targetChannel, '')
            if len(chatMessage.split()) == 2:
                if targetChannel in self.channels:
                    self.channels[targetChannel].broadcast_message(': Requesting Invite\n', clientName)
                else:
                    clientSocket.sendall('\n> Channel does not exist.\n'.encode('utf8'))
            else:
                if targetChannel in self.channels:
                    self.channels[targetChannel].broadcast_message((': ' + requestMessage + '\n'), clientName)
                else:
                    clientSocket.sendall('\n> Channel does not exist.\n'.encode('utf8'))

    def invite(self, clientSocket, chatMessage, clientName):
        if len(chatMessage.split()) < 3:
            clientSocket.sendall('\n> Must provide a target name and a channel to invite them too.\n'.encode('utf8'))
        else:
            targetName = chatMessage.split()[1]
            targetChannel = chatMessage.split()[2]
            if targetName in self.server_users:
                targetSocket = self.server_users[targetName].clientSocket
                targetSocket.sendall(
                    ('\n> ' + clientName + ' has invited you to channel: ' + targetChannel + '\n').encode('utf8'))
                targetSocket.send(('> Type /join channelName to join their channel!\n').encode('utf8'))

    def ison(self, clientSocket, chatMessage):
        if len(chatMessage.split()) < 2:
            clientSocket.sendall('\n> Must provide a space separated list of the nick names you wish to see are on the network.\n'.encode('utf8'))
        else:
            chatMessage = chatMessage.replace('/ison', '')
            listOfNicks = chatMessage.split(' ')
            onlineNicks = []
            for nick in listOfNicks:
                for user in self.server_users:
                    if self.server_users[user].nickName == nick:
                        onlineNicks.append(nick)
            clientSocket.sendall(('\n> List of online users: ' + ' '.join(onlineNicks) + '\n').encode('utf8'))

    def die(self):
        self.server_shutdown()

    def send_message(self, clientSocket, chatMessage, clientName):
        currentClientName =  self.server_users[clientName].name
        if clientName in self.channels_client_map:
            self.channels[self.channels_client_map[clientName]].broadcast_message(chatMessage, currentClientName + ": ")
        else:
            chatMessage = """\n> You are currently not in any channels:

Use /list to see a list of available channels.
Use /join [channel name] to join a channels.\n\n""".encode('utf8')

            clientSocket.sendall(chatMessage)

    def remove_client(self, clientName):
        if clientName in self.channels_client_map:
            self.channels[self.channels_client_map[clientName]].remove_client_from_channel(clientName)
            del self.channels_client_map[clientName]
        print("Client: " + clientName + " has left\n")

    def server_shutdown(self):
        print("Shutting down chat server.\n")
        self.serverSocket.shutdown(socket.SHUT_RDWR)
        self.serverSocket.close()

def main():
    chatServer = Server()

    print("\nListening on port " + str(chatServer.address[1]))
    print("Waiting for connections...\n")

    chatServer.start_listening()
    chatServer.server_shutdown()

if __name__ == "__main__":
    main()
