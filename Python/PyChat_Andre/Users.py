import socket

class Users:
    def __init__(self, nickName, password, type, name, clientSocket, awayStatus, awayMessage):
        self.nickName = nickName
        self.password = password
        self.type = type
        self.name = name
        self.clientSocket = clientSocket
        self.awayStatus = awayStatus
        self.awayMessage = awayMessage
        self.channelList = {}  # Channel Name -> Channel Type
        # Channel Type U=user created, S=server created

    def joinChannel(self, channelName, channelType):
        self.channelList[channelName] = channelType

    def leaveChannel(self, channelName):
        del self.channelList[channelName]

