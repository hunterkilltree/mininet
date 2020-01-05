from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from mininet.topo import Topo

import os

from mininet.link import TCIntf

from subprocess import call
from random import randint
import random
import string

import os
import sys
import time
import argparse
import json
import collections
import multiprocessing

#from src.cacheAlgorithm.FIFO import FIFO
# from traffic import sflow
import networkx as nx

import numpy as np
from os import listdir# listdir, walk


lock = multiprocessing.Lock()

class LinuxRouter(Node):
    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


class CacheStatistic:
    def __init__(self, cacheId):
        self.id = cacheId
        self.miss = 0
        self.hit = 0
    def getHitRate():
        return self.hit / (self.miss + self.hit)

class FileNode(object):
    def __init__(self, fileId, fileSize, freq, time=None):
        self.id = fileId
        self.size = fileSize
        self.time = time
        self.freq = freq
        self.prev = None
        self.next = None

class LinkedList(object):
    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, node):
        node.next, node.prev = None, None  # avoid dirty node
        if self.head is None:
            self.head = node
        else:
            self.tail.next = node
            node.prev = self.tail
        self.tail = node

    def delete(self, node):
        if node.prev:
            node.prev.next = node.next
        else:
            self.head = node.next
        if node.next:
            node.next.prev = node.prev
        else:
            self.tail = node.prev
        node.next, node.prev = None, None  # make node clean

class Cache:
    def __init__(self, cacheId, maxCacheSize):
        self.id = cacheId
        self.maxSize = maxCacheSize
        self.currentSize = 0
        self.stats = CacheStatistic(cacheId)

    def set(self, fileId, fileSize):
        raise NotImplementedError

    def get(self, fileId):
        raise NotImplementedError

    def getWithoutCount(self, fileId):
        raise NotImplementedError

class FIFOCache(Cache):
    def __init__(self, cacheId, maxCacheSize=1000000):
        Cache.__init__(self, cacheId, maxCacheSize)
        self.hashMap = {}
        self.head = None
        self.end = None



    def set(self, fileId, fileSize):
        fileSize = int(fileSize)
        if fileId in self.hashMap:
            return

        newNode = FileNode(fileId, fileSize, freq=None, time=None)
        while self.currentSize + fileSize > self.maxSize:
            del self.hashMap[self.end.id]
            self.remove(self.end)

        self.setHead(newNode)
        self.hashMap[fileId] = newNode

    def get(self, fileId):
        if fileId not in self.hashMap:
            self.stats.miss += 1
            return -1
        fileNode = self.hashMap[fileId]
        self.stats.hit += 1
        return fileNode.size

    def getWithoutCount(self, fileId):
        return self.get(fileId)

    def setHead(self, fileNode):
        if not self.head:
            self.head = fileNode
            self.end = fileNode
        else:
            fileNode.prev = self.head
            self.head.next = fileNode
            self.head = fileNode
        self.currentSize += fileNode.size

    def remove(self, fileNode):
        if not self.head:
            return

        # removing the node from somewhere in the middle; update pointers
        if fileNode.prev:
            fileNode.prev.next = fileNode.next
        if fileNode.next:
            fileNode.next.prev = fileNode.prev

        # head = end = node
        if not fileNode.next and not fileNode.prev:
            self.head = None
            self.end = None

        # if the node we are removing is the one at the end, update the new end
        # also not completely necessary but set the new end's previous to be NULL
        if self.end == fileNode:
            self.end = fileNode.next
            self.end.prev = None
        self.currentSize -= fileNode.size


class LRUCache(Cache):
    def __init__(self, cacheId, maxCacheSize=1000000, delta=10000):
        Cache.__init__(self, cacheId, maxCacheSize)
        self.hashMap = {}
        self.head = None
        self.end = None

    def get(self, fileId):
        if fileId not in self.hashMap:
            self.stats.miss += 1
            return -1

        fileNode = self.hashMap[fileId]
        if self.head == fileNode:
            return fileNode.size
        self.remove(fileNode)
        self.setHead(fileNode)
        self.stats.hit += 1
        return fileNode.size

    def getWithoutCount(self, fileId):
        fileNode = self.hashMap[fileId]
        return fileNode.size

    def set(self, fileId, fileSize):
        fileSize = int(fileSize)
        if fileId in self.hashMap:
            fileNode = self.hashMap[fileId]
            fileNode.size = fileSize

            # small optimization (2): update pointers only if this is not head; otherwise return
            if self.head != fileNode:
                self.remove(fileNode)
                self.setHead(fileNode)
        else:
            newNode = FileNode(fileId, fileSize, freq=None, time=time.time())

            while self.currentSize + fileSize > self.maxSize:
                del self.hashMap[self.end.id]
                self.remove(self.end)
            self.setHead(newNode)
            self.hashMap[fileId] = newNode

    def setHead(self, fileNode):
        if not self.head:
            self.head = fileNode
            self.end = fileNode
        else:
            fileNode.prev = self.head
            self.head.next = fileNode
            self.head = fileNode
        self.currentSize += fileNode.size

    def remove(self, fileNode):
        if not self.head:
            return

        # removing the node from somewhere in the middle; update pointers
        if fileNode.prev:
            fileNode.prev.next = fileNode.next
        if fileNode.next:
            fileNode.next.prev = fileNode.prev

        # head = end = node
        if not fileNode.next and not fileNode.prev:
            self.head = None
            self.end = None

        # if the node we are removing is the one at the end, update the new end
        # also not completely necessary but set the new end's previous to be NULL
        if self.end == fileNode:
            self.end = fileNode.next
            self.end.prev = None
        self.currentSize -= fileNode.size


class LFUCache(Cache):
    def __init__(self, cacheId, maxCacheSize=1000000, delta=10000):
        Cache.__init__(self, cacheId, maxCacheSize)
        self.hashMap = {}
        self.min_freq = 0
        self.freq_to_nodes = collections.defaultdict(LinkedList)
        self.key_to_node = {}

    def get(self, fileId):
        if fileId not in self.key_to_node:
            self.stats.miss += 1
            return -1

        old_node = self.key_to_node[fileId]
        self.key_to_node[fileId] = FileNode(fileId, old_node.size, old_node.freq)
        self.freq_to_nodes[old_node.freq].delete(old_node)
        if not self.freq_to_nodes[self.key_to_node[fileId].freq].head:
            del self.freq_to_nodes[self.key_to_node[fileId].freq]
            if self.min_freq == self.key_to_node[fileId].freq:
                self.min_freq += 1

        self.key_to_node[fileId].freq += 1
        self.freq_to_nodes[self.key_to_node[fileId].freq].append(self.key_to_node[fileId])
        self.stats.hit += 1
        return self.key_to_node[fileId].size

    def getWithoutCount(self, fileId):
        fileNode = self.key_to_node[fileId]
        return fileNode.size

    def set(self, fileId, fileSize):
        fileSize = int(fileSize)
        if self.get(fileId) != -1:
            self.key_to_node[fileId].size = fileSize
        else:
            while self.currentSize + fileSize > self.maxSize:
                deletedSize = self.key_to_node[self.freq_to_nodes[self.min_freq].head.id].size
                del self.key_to_node[self.freq_to_nodes[self.min_freq].head.id]
                self.freq_to_nodes[self.min_freq].delete(self.freq_to_nodes[self.min_freq].head)
                if not self.freq_to_nodes[self.min_freq].head:
                    del self.freq_to_nodes[self.min_freq]
                self.currentSize -= deletedSize

            self.min_freq = 1
            self.key_to_node[fileId] = FileNode(fileId, fileSize, self.min_freq)
            self.freq_to_nodes[self.key_to_node[fileId].freq].append(self.key_to_node[fileId])
            self.currentSize += fileSize

def setup_dir(host):
    for i in host:
        i.cmd('cd data ')
        createFolder = 'mkdir ' + str(i)
        i.cmd(createFolder)
        goFolder = 'cd ' + str(i)
        i.cmd(goFolder)
    return host

def get_dir(host):
    host_dir = []

    for i in host:
        directory = i.cmd('pwd')
        directory = directory.replace('\r\n', '')
        host_dir.append(directory)

    return host_dir

def deconstructor(host):
    for i in host:
        i.cmd('cd ..')
        removeFolder = 'rm ' + '-rf '+ str(i)
        i.cmd(removeFolder)

def open_port(host):
    for i in host:
        i.cmd('python -m SimpleHTTPServer 80 2> /tmp/http.log &')

def loadJSON(jsonFile):
    with open(jsonFile) as config:
        data = config.read()
    return json.loads(data)



def loadClientId2CacheIdMap(clientIds, graph, routerCacheMap):
    result = {}
    for clientId in clientIds:
        routerIdPath = nx.dijkstra_path(graph, "mainServer", clientId, "weight")[1:-1]
        result[clientId] = []
        for routerId in routerIdPath:
            cacheId = routerCacheMap[routerId]
            result[clientId].append(cacheId)
    return result

def createRandomFile(host, fileName, fileSize="1M"):
    host.cmd("fallocate -l " + str(fileSize) + " " + fileName)

def removeFile(host, fileName):
    host.cmd("rm " +  fileName)

def requestHttpToCacheServer(serverNode, clientNode, cacheMemory, fileId):
    fileSize = cacheMemory.get(fileId)
    fileName = "file_" + fileId + ".txt"

    if fileSize == -1:
        return False

    createRandomFile(serverNode, fileName, fileSize)


    wget_cmd = "wget --server-response " + serverNode.IP() + "/" + fileName + " 2>&1| grep -c '200 OK'"
    isSuccess = clientNode.cmd(wget_cmd).split("\n")[-2]

    removeFile(serverNode, fileName)
    if int(isSuccess) == 1:
        return True
    else:
        return False

def requestHttpToMainServer(serverNode, clientNode, fileId, fileSize):
    fileName = "file_" + fileId + ".txt"
    createRandomFile(serverNode, fileName, fileSize)
    wget_cmd = "wget --server-response " + serverNode.IP() + "/" + fileName + " 2>&1| grep -c '200 OK'"
    isSuccess = clientNode.cmd(wget_cmd).split("\n")[-2]

    removeFile(serverNode, fileName)
    if int(isSuccess) == 1:
        return True
    else:
        return False

def sendFile(dstNode, srcNode, fileId, fileSize, port=12345):
    dst_dir = get_dir([dstNode])[0]
    src_dir = get_dir([srcNode])[0]
    fileName = "file_" + fileId + ".txt"

    dst_cmd = 'nc -l %d > %s' % (port, os.path.join(dst_dir, fileName))
    src_cmd = 'nc %s %s < %s' % (dstNode.IP(), port, os.path.join(src_dir, fileName))

    dstProcess = dstNode.popen( dst_cmd, shell=True)
    srcProcess = srcNode.popen( src_cmd, shell=True)

    dstProcess.kill()
    srcProcess.kill()

def updateTraversedHosts(traversedHostServers, net, cacheMemoryDict, fileId, fileSize):
    for idx in range(1, len(traversedHostServers)):
        src = net[traversedHostServers[idx-1]]
        dst = net[traversedHostServers[idx]]

        randPort = randint(9999, 60000)
        sendFile(dst, src, fileId, fileSize, randPort)
        fileName = "file_" + fileId + ".txt"
        removeFile(src, fileName)

        if idx == 1:
            srcCacheMemory = cacheMemoryDict[traversedHostServers[idx-1]]
            srcCacheMemory.set(fileId, fileSize)

        if idx != len(traversedHostServers)-1: # cache server, client server at idx== len(traversedHostServers)
            srcCacheMemory = cacheMemoryDict[traversedHostServers[idx-1]]
            dstCacheMemory = cacheMemoryDict[traversedHostServers[idx]]

            fileSize = srcCacheMemory.getWithoutCount(fileId)
            dstCacheMemory.set(fileId, fileSize)

def getRemoteFile(clientId, net, clientId2CacheIdMap, cacheMemoryDict, fileId, fileSize="1M"):
    lock.acquire()
    try:
        cacheIds = clientId2CacheIdMap[clientId]
        for idx, cacheId in enumerate(cacheIds):
            if idx != 0:
                previousCacheId = cacheIds[idx-1]
            else:
                previousCacheId = clientId
            if cacheId != "mainServer":
                isSuccess = requestHttpToCacheServer(net[cacheId], net[previousCacheId], cacheMemoryDict[cacheId], fileId)
            else:
                isSuccess = requestHttpToMainServer(net[cacheId], net[previousCacheId], fileId, fileSize)
            if isSuccess:
                if idx - 1 >= 0:
                    traversedHostServers = ([clientId] +  cacheIds[0:idx])
                    traversedHostServers.reverse()
                    updateTraversedHosts(traversedHostServers, net, cacheMemoryDict, fileId, fileSize)
                return True
        return False
    finally:
        lock.release()

class NetTopology (Topo):
    def __init__( self, jsonFile, *args, **params):
        self.networkInfo = loadJSON(jsonFile)
        self.graph = nx.Graph()
        super(NetTopology, self).__init__()

    def build(self, **params):
        self.routerCacheMap = {}

        self.routerIds = []
        info( '*** Add routers\n')
        for routerInfo in self.networkInfo["Routers"]:
            routerId = routerInfo["ID"].encode()
            self.routerIds.append(self.addNode(routerId, cls=LinuxRouter, ip=routerInfo["defaultIP"]))
            self.graph.add_node(routerId, ip=routerInfo["defaultIP"])

        self.clientIds = []
        info( '*** Add clients\n')
        for clientInfo in self.networkInfo['Clients']:
            clientId = clientInfo['ID'].encode()
            self.clientIds.append(self.addHost(clientId, cls=Host, ip=clientInfo['IP'], defaultRoute="via " + clientInfo['defaultRoute']))
            self.graph.add_node(clientId, ip=clientInfo["IP"], gw=clientInfo['defaultRoute'])

        self.cacheMemoryDict = {}
        info( '*** Add caches\n')
        for cacheInfo in self.networkInfo['CacheServers']:
            cacheId = cacheInfo['ID'].encode()
            self.addHost(cacheId, cls=Host, ip=cacheInfo['IP'], defaultRoute="via " + cacheInfo['defaultRoute'])
            if cacheInfo["type"] == "FIFO":
                self.cacheMemoryDict[cacheId] = FIFOCache(cacheId, cacheInfo['maxSize'])
            elif cacheInfo["type"] == "LRU":
                self.cacheMemoryDict[cacheId] = LRUCache(cacheId, cacheInfo['maxSize'])
            elif cacheInfo["type"] == "LFU":
                self.cacheMemoryDict[cacheId] = LFUCache(cacheId, cacheInfo['maxSize'])
            self.graph.add_node(cacheId, ip=cacheInfo["IP"], gw=cacheInfo['defaultRoute'])

        ## only have one mainServer
        info( '*** Add main server\n')
        serverInfo = self.networkInfo['MainServer']
        self.addHost("mainServer", cls=Host, ip=serverInfo['IP'], defaultRoute="via " + serverInfo['defaultRoute'])
        self.graph.add_node("mainServer", ip=serverInfo["IP"], gw=serverInfo['defaultRoute'])

        info( '*** Add links\n')
        for linkInfo in self.networkInfo['Links']:
            nodeIds = linkInfo['NodeIds']
            nodeId_1, interface_1 = nodeIds[0].split("/")
            params1Info = linkInfo['params1']
            if 'params2' in linkInfo:
                nodeId_2, interface_2 = nodeIds[1].split("/")
                params2Info = linkInfo['params2']
                self.addLink(nodeId_1.encode(), nodeId_2.encode(), intf = TCIntf, intfName1=interface_1, intfName2=interface_2,
                             params1={'ip': params1Info['ip'], 'bw': params1Info['bw'] , 'delay': params1Info['delay']}, #
                             params2={'ip': params2Info['ip']})
                self.graph.add_edge(nodeId_1.encode(), nodeId_2.encode(), interface_1=interface_1, interface_2=interface_2, id_1=nodeId_1.encode(),
                                    ip_1=params1Info['ip'], ip_2=params2Info['ip'], weight=1/params1Info['bw']) # , weight=1/bw

            else:
                nodeId_2 = nodeIds[1]
                self.addLink(nodeId_1.encode(), nodeId_2.encode(), intf = TCIntf, intfName1=interface_1,
                             params1={'ip': params1Info['ip'], 'bw': params1Info['bw'] , 'delay': params1Info['delay']})  # , 'bw': params1Info['bw'] , 'delay': params1Info['delay']
                if "cache" in nodeId_2.encode():
                    self.routerCacheMap[nodeId_1.encode()]= nodeId_2.encode()
                elif "mainServer" in nodeId_2.encode():
                    self.routerCacheMap[nodeId_1.encode()]= "mainServer"
                ip_1 = params1Info['ip']
                if ".1/" in ip_1:
                    ip_2 = ip_1.replace(".1/", ".2/")
                elif ".2/" in ip_1:
                    ip_2 = ip_1.replace(".2/", ".1/")
                elif ".66/" in ip_1:
                    ip_2 = ip_1.replace(".66/", ".65/")
                elif ".65/" in ip_1:
                    ip_2 = ip_1.replace(".65/", ".66/")
                else:
                    print("error ip: " + str(ip_1))
                self.graph.add_edge(nodeId_1.encode(), nodeId_2.encode(), interface_1=interface_1, id_1=nodeId_1.encode(), ip_1=params1Info['ip'],
                                    interface_2="eth0", ip_2=ip_2, weight=1/params1Info['bw']) # , "bw":  weight=1/bw

        info( '\n' )

class SimulatedNetwork:
    def __init__(self, topo):
        self.net = Mininet(topo=topo)
        self.topo = topo

    def pingList(self, sourceList, destList):
        """Ping between all specified hosts.
           hosts: list of hosts
           returns: ploss packet loss percentage"""
        # should we check if running?
        packets = 0
        lost = 0
        ploss = None
        for node in sourceList : #(self.routers + self.caches) :
            print '%s -> ' % node.name, ""
            for dest in destList:
                if node != dest:
                    opts = ''
                    if dest.intfs:
                        result = node.cmd( 'ping -c1 %s %s' %
                                           (opts, dest.IP()) )
                        sent, received = self.net._parsePing( result )
                    else:
                        sent, received = 0, 0
                    packets += sent
                    if received > sent:
                        print( '*** Error: received too many packets' )
                        print '%s' % result, ""
                        node.cmdPrint( 'route' )
                        exit( 1 )
                    lost += sent - received
                    print  ( '%s ' % dest.name ) if received else 'X ' , ""
            print( '\n' )
        if packets > 0:
            ploss = 100.0 * lost / packets
            received = packets - lost
            print( "*** Results: %i%% dropped (%d/%d received)\n" %
                    ( ploss, received, packets ) )
        else:
            ploss = 0
            print( "*** Warning: No packets sent\n" )
        return ploss


    def buildRTable(self):
        for hostId in (self.topo.cacheMemoryDict.keys() + self.topo.clientIds):
            shortestPath = nx.dijkstra_path(self.topo.graph, "mainServer", hostId, "weight")
            for i in range(1, len(shortestPath)-1):
                nodeId = shortestPath[i]
                next=nodeId
                for j in range(i-1, -1, -1):
                    previousNodeId = shortestPath[j]
                    edgeData = self.topo.graph.get_edge_data(previousNodeId, next)
                    if edgeData["id_1"] == previousNodeId:
                        previousNodeIP = edgeData["ip_1"].replace(".1/", ".0/").replace(".2/", ".0/").replace(".65/", ".64/").replace(".66/", ".64/").split("/")[0]
                        previousNodeNetmask = "255.255.255.192" if edgeData["ip_1"].split("/")[1] == "26" else "255.255.255.0"
                        if j == i-1:
                            nodeGateway = edgeData["ip_1"].split("/")[0]
                            nodeInterface = edgeData["interface_2"]
                    else:
                        previousNodeIP = edgeData["ip_2"].replace(".1/", ".0/").replace(".2/", ".0/").replace(".65/", ".64/").replace(".66/", ".64/").split("/")[0]
                        previousNodeNetmask = "255.255.255.192" if edgeData["ip_2"].split("/")[1] == "26" else "255.255.255.0"
                        if j == i-1:
                            nodeGateway = edgeData["ip_2"].split("/")[0]
                            nodeInterface = edgeData["interface_1"]
                    self.net[nodeId].cmd("route add -net {} netmask {} gw {} dev {}".format(previousNodeIP, previousNodeNetmask, nodeGateway, nodeInterface))
                    next=previousNodeId
                prev=nodeId
                for j in range(i+1, len(shortestPath)):
                    nextNodeId = shortestPath[j]
                    edgeData = self.topo.graph.get_edge_data(prev, nextNodeId)
                    if edgeData["id_1"] == nextNodeId:
                        nextNodeIP = edgeData["ip_1"].replace(".1/", ".0/").replace(".2/", ".0/").replace(".65/", ".64/").replace(".66/", ".64/").split("/")[0]
                        nextNodeNetmask = "255.255.255.192" if edgeData["ip_1"].split("/")[1] == "26" else "255.255.255.0"
                        if j == i+1:
                            nodeGateway = edgeData["ip_1"].split("/")[0]
                            nodeInterface = edgeData["interface_2"]
                    else:
                        nextNodeIP = edgeData["ip_2"].replace(".1/", ".0/").replace(".2/", ".0/").replace(".65/", ".64/").replace(".66/", ".64/").split("/")[0]
                        nextNodeNetmask = "255.255.255.192" if edgeData["ip_2"].split("/")[1] == "26" else "255.255.255.0"
                        if j == i+1:
                            nodeGateway = edgeData["ip_2"].split("/")[0]
                            nodeInterface = edgeData["interface_1"]
                    self.net[nodeId].cmd("route add -net {} netmask {} gw {} dev {}".format(nextNodeIP, nextNodeNetmask, nodeGateway, nodeInterface))
                    prev=nextNodeId

    def buildNet(self):
        info( '*** Building network\n')
        self.net.build()

    def startNet(self):
        info( '*** Starting network\n')
        self.net.start()

    def postConfig(self):
        self.servers = [self.net["mainServer"]]
        self.caches = [self.net[cacheId] for cacheId in self.topo.cacheMemoryDict.keys()]
        self.clients = [self.net[clientId] for clientId in self.topo.clientIds]
        self.routers = [self.net[routerId] for routerId in self.topo.routerIds]

        info(' *** Build Routing Table from mainServer to other hosts\n')
        self.buildRTable()

        info(' *** Test Ping from mainServer to other hosts\n')
        self.caches =  [self.net["cache_1"],  self.net["cache_2"]]
        self.clients = [self.net["client_1"],  self.net["client_2"]]

        self.pingList(self.servers, (self.caches + self.clients))

        info(' *** Loading ClientId to CacheId Map\n')
        self.clientId2CacheIdMap = loadClientId2CacheIdMap(self.topo.clientIds, self.topo.graph, self.topo.routerCacheMap)

        info( '*** Post configure switches and hosts\n')
        # set up directory
        setup_dir(self.servers)
        setup_dir(self.caches)
        setup_dir(self.clients)

        # get directory
        caches_dir = get_dir(self.caches)
        print(caches_dir)
        clients_dir = get_dir(self.clients)
        print(clients_dir)
        servers_dir = get_dir(self.servers)
        print(servers_dir)

        # open port 80 get data
        open_port(self.caches)
        open_port(self.servers)
        time.sleep(1) # 1s

    def stopNet(self):
        deconstructor(self.caches)
        deconstructor(self.clients)
        deconstructor(self.servers)
        self.net.stop()

    def useCLI(self):
        CLI(self.net)



# check to see if this is the main thread of execution
from multiprocessing import Process

def runTestCase(argsList):
    for args in argsList:
        clientId, fileId, fileSize, net, clientId2CacheIdMap, cacheMemoryDict = args
        getRemoteFile(clientId, net, clientId2CacheIdMap, cacheMemoryDict, fileId, fileSize)


def countNumberOfFiles(tempPath, folder):
    new_name = os.path.join(path, folder)
    #print(new_name)
    files = os.listdir(new_name)
    return len(files)

def verification(path):
    FilesInCaches = 0
    FilesInMain = 0
    FilesInClients = 0

    subdirs = [os.path.join(path, o) for o in os.listdir(path) if os.path.isdir(os.path.join(path,o))]
    files = os.listdir(path)
    temp = 0

    print("=============================CLIENTS========================")
    for i in files:
        if "client" in i:
            temp = countNumberOfFiles(path,i)
            print("{} : {}".format(i, temp) )
            FilesInClients += temp

    print("=============================CACHE==========================")
    for i in files:
        if "cache" in i:
            temp = countNumberOfFiles(path,i)
            print("{} : {}".format(i, temp) )
            FilesInCaches += temp
    print("=============================MAIN===========================")
    print("{} : {}".format("mainServer", countNumberOfFiles(path, "mainServer")) )


    print("======================FINAL RESULT==========================")
    print("Total files in Caches: {}".format(FilesInCaches))
    print("Total files in clients:{} ".format(FilesInClients))
    print("Total files in MainServer : {}".format(FilesInMain))


if __name__ == '__main__':
    #construct the argument parser and parse command line argument
    setLogLevel( 'info' )
#     myNetwork(networkInfor)
    json_dir = "/home/lqt/Desktop/Project11_test_code/config/json/ntt.json"
    topo = NetTopology(json_dir)
    net = SimulatedNetwork(topo)
    net.startNet()
    net.postConfig()



    clientReqs = {"client_1": [["client_1", str(randint(0, 15)),  "1024", net.net, net.clientId2CacheIdMap, net.topo.cacheMemoryDict] for number in range(50)],
                 "client_2": [["client_2", str(randint(10, 30)),  "1024", net.net, net.clientId2CacheIdMap, net.topo.cacheMemoryDict] for number in range(50)]}

    #runTestCase(clientReqs["client_1"])
    for clientReqId in clientReqs:
        p = Process(target=runTestCase, args=(clientReqs[clientReqId],))
        p.start()

    # Change path before run
    path = '/home/lqt/Desktop/Project11_test_code/data'
    verification(path)






    net.useCLI()
    net.stopNet()

    os.system('./clean.sh')
