# python run.py --read config/json/one_host_one_cache.json
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call

import time
import argparse
import json

# define value
BANDWITH = 10 #  bw is expressed as a number in Mbit
DELAY = '10ms'
Max_Queue_Size = 1000 # maximum queue size of  1000 packets using the Hierachical token bucket rate limiter and netem delay/loss
Uses_Htb = True # ??????
LOSS  = 10 # expressed as a percentage (between 0 and 100)


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
        removeFolder = 'rmdir ' + str(i)
        i.cmd(removeFolder)

def open_port(host):
    for i in host:
        i.cmd('python -m SimpleHTTPServer 80 2> /tmp/http.log &')



# singleSwitch many nodes
def myNetwork(networkInfor):
    net = Mininet(topo=None, build=False, ipBase='10.0.0.0/8')

    info( '*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')

    clients = [] # save information of each client
    info( '*** Add hosts\n')
    for numberOfClients in networkInfor['Clients']:
        InfoClient = net.addHost(numberOfClients['UpstreamId'], cls=Host, ip=numberOfClients['Ip'], defaultRoute=None)
        clients.append(InfoClient)

    caches = [] # save information of each cache
    info( '*** Add caches\n')
    for numberOfCaches in networkInfor['CacheServers']:
        InfoCache = net.addHost(numberOfCaches['Id'], cls=Host, ip=numberOfCaches['Ip'], defaultRoute=None)
        caches.append(InfoCache)

    server = [] # save information of each server
    info( '*** Add main server\n')
    for numberOfServer in networkInfor['OriginServer']:
        InfoServer = net.addHost(numberOfServer['Id'], cls=Host, ip=numberOfServer['Ip'], defaultRoute=None)
        server.append(InfoServer)

    info( '*** Add links\n')
    for item in server:
        net.addLink(s1, item, bw = BANDWITH, delay = DELAY, loss = LOSS, max_queue_size = Max_Queue_Size, uses_htb = Uses_Htb)
    for item in clients:
        net.addLink(s1, item, bw = BANDWITH, delay = DELAY, loss = LOSS, max_queue_size = Max_Queue_Size, uses_htb = Uses_Htb)
    for item in caches:
        net.addLink(s1, item, bw = BANDWITH, delay = DELAY, loss = LOSS, max_queue_size = Max_Queue_Size, uses_htb = Uses_Htb)

    info( '*** Starting network\n')
    net.build()

    info( '*** Starting switches\n')
    net.get('s1').start([])

    info( '*** Post configure switches and hosts\n')
    # set up directory
    server[0].cmd('cd data/mainServer')
    caches = setup_dir(caches)
    clients = setup_dir(clients)


    # get directory
    caches_dir = get_dir(caches)
    clients_dir = get_dir(clients)
    #server_dir = get_dir(server)
    #print(server_dir)
    server_dir = server[0].cmd('pwd')

    # open port 80 get data
    open_port(caches)
    open_port(server)
    time.sleep(1) # 1s

    CLI(net)
    deconstructor(caches)
    deconstructor(clients)
    net.stop()

def my_test(topology):
    with open(topology) as complex_data:
        data = complex_data.read()

    jsonData = json.loads(data)

    return jsonData

# check to see if this is the main thread of execution
if __name__ == '__main__':
    #construct the argument parser and parse command line argument
    parser = argparse.ArgumentParser()
    parser.add_argument('--r', '--read', type=str, help='read json file')

    args = vars(parser.parse_args())

    json_dir = args['r']
    networkInfor = my_test(json_dir)

    setLogLevel( 'info' )
    myNetwork(networkInfor)
