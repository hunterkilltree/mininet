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


import argparse
import json

# define value
BANDWITH = 10 #  bw is expressed as a number in Mbit
DELAY = '10ms'
Max_Queue_Size = 1000 # maximum queue size of  1000 packets using the Hierachical token bucket rate limiter and netem delay/loss
Uses_Htb = True # ??????
LOSS  = 10


def setup_dir(host):
    for i in host:
        i.cmd('cd data ')
        createFolder = 'mkdir ' + str(i)
        i.cmd(createFolder)
        goFolder = 'cd ' + str(i)
        i.cmd(goFolder)
    return host

def deconstructor(host):
    for i in host:
        i.cmd('cd ..')
        removeFolder = 'rmdir ' + str(i)
        i.cmd(removeFolder)



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
    caches = setup_dir(caches)
    clients = setup_dir(clients)
    server[0].cmd('cd data/mainServer')


    print(server[0].cmd('pwd'))





    CLI(net)
    deconstructor(caches)
    deconstructor(clients)
    net.stop()

def my_test(topology):
    with open(topology) as complex_data:
        data = complex_data.read()

    jsonData = json.loads(data)

    # process complex_data
    print ('Topology name: {}'.format(jsonData['NetworkId']))
    for numberOfClients in jsonData['Clients']:
        print ('IP : {}'.format(numberOfClients['UpstreamId']))

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
