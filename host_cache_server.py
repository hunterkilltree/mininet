#!/usr/bin/python

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
import random
import os
from os import listdir# listdir, walk
import matplotlib.pyplot as plt
import numpy as np
import decimal
from decimal import Decimal


def setup_dir(h1, cache, server) :
    h1.cmd('cd host1_data')
    cache.cmd('cd cache_data')
    server.cmd('cd server_data')
    return h1, cache, server

def get_dir(h1, cache, server):
    client_dir = h1.cmd('pwd')
    cache_dir = cache.cmd('pwd')
    server_dir = server.cmd('pwd')

    client_dir = client_dir.replace('\r\n', '')
    cache_dir = cache_dir.replace('\r\n', '')
    server_dir = server_dir.replace('\r\n', '')

    return client_dir, cache_dir,server_dir

def open_port(cache, server):
    cache.cmd('python -m SimpleHTTPServer 80 2> /tmp/http.log &')
    server.cmd('python -m SimpleHTTPServer 80 2> /tmp/http.log &')

def get_memmory_size(path):

    total_size = 0
    files = os.listdir(path)
    for f in files:
        fp = os.path.join(path, f)
        # skip if it is symbolic link
        if not os.path.islink(fp):
            total_size += os.path.getsize(fp)

    #print('total_size : {} bytes'.format(total_size))

    return total_size

def get_memmory_info(path):
    #print(os.listdir(path))
    return os.listdir(path)

def get_file_size(dir_server, name):
    fp = os.path.join(dir_server, name)
    #if not os.path.islink(fp):
    return os.path.getsize(fp)

def draw_bar_chart(hitRate, traffic, worstTraffic, dir_cache, dir_server):
    names= ['Cache', 'MainServer']
    values =[]
    values.append(hitRate)
    values.append(100)

    plt.figure(figsize=(20, 3))
    plt.subplot(131)
    #y = np.arange(len(names))
    plt.bar(names, values)

    for i, v in enumerate(values):
        plt.text(i - 0.1, v,str(values[i]), color='blue', fontweight='bold')

    plt.title("Hit rate from hosts", fontsize=18)
    plt.xlabel('hosts')
    plt.ylabel('hit rate (%)')

    plt.subplot(132)
    cases = ['Simulate traffic', 'Wosrt traffic']
    trafficValues =[]
    #y_pos = np.arange(len(cases))
    trafficValues.append(traffic)
    trafficValues.append(worstTraffic)

    plt.bar(cases, trafficValues)

    for i, v in enumerate(trafficValues):
        plt.text(i - 0.1, v,str(trafficValues[i]), color='blue', fontweight='bold')

    plt.title("Estimate traffic", fontsize=18)
    plt.xlabel('cases')
    plt.ylabel('traffic')

    plt.subplot(133)

    plt.title("FIFO", fontsize=18)
    plt.xlabel('memmory')
    plt.ylabel('bytes')

    memmory = []
    memmory.append(get_memmory_size(dir_cache))
    memmory.append(get_memmory_size(dir_server))
    plt.bar(names, memmory)

    for i, v in enumerate(memmory):
        plt.text(i - 0.1, v,str(memmory[i]), color='blue', fontweight='bold')

    plt.show()

def FIFO(h1, cache, server, dir_cache, dir_server, link_host_cache, link_cache_server, numberOfRequests):
    hitInCache = 0
    hitRate = 0 # hitInCache / numberOfRequests
    traffic = 0 # increase 1 unit for each time requests

    total_files = get_memmory_info(dir_server)
    cache_queue = []

    while True:
        file_name = random.choice(total_files)
        print(file_name)
        if file_name in cache_queue:
            request = link_host_cache + file_name
            h1.cmd(request)

        else:

            max_cache_memmory = get_memmory_size(dir_cache)
            max_cache_memmory = max_cache_memmory + get_file_size(dir_server, file_name)
            print(get_file_size(dir_server, file_name))
            print(max_cache_memmory)

            if (max_cache_memmory >= 40000):
                break
            else:
                request = link_cache_server + file_name
                cache.cmd(request)
                cache_queue.append(file_name)

                request = link_host_cache + file_name
                h1.cmd(request)

    # end
    # DEBUG: show queue
    print(cache_queue)

    for i in range(int(numberOfRequests)):
        print(i)
        file_name = random.choice(total_files)

        if file_name in cache_queue:
            request = link_host_cache + file_name
            h1.cmd(request)

            hitInCache += 1
            traffic += 1
        else:
            while True:
                max_cache_memmory = get_memmory_size(dir_cache)
                max_cache_memmory = int(max_cache_memmory) + int(get_file_size(dir_server, file_name))
                #set max cache memmory 1MB
                if (max_cache_memmory >= 40000):
                    if len(cache_queue) != 0:
                        temp = cache_queue.pop(0)
                        # delete
                        fp = os.path.join(dir_cache, temp)
                        os.remove(fp)
                else:
                    break


            request_from_cache_to_server = link_cache_server + file_name
            cache.cmd(request_from_cache_to_server)
            traffic += 1
            cache_queue.append(file_name)

            request_from_host_to_cache = link_host_cache + file_name
            h1.cmd(request_from_host_to_cache)
            traffic += 1

    print('Inside:')
    print(cache_queue)
    # set global precision :
    decimal.getcontext().prec = 3
    hitRate = decimal.Decimal(hitInCache)/ decimal.Decimal(int(numberOfRequests)) * 100
    print('Hit : {}'.format(hitInCache))
    print('Hit rate: {} %'.format(hitRate))
    worstTraffic =  int(numberOfRequests) * 2
    print('Traffic increase 1 unit for each time requests: {}/{}'.format(traffic, worstTraffic))

    draw_bar_chart(hitRate, traffic, worstTraffic, dir_cache, dir_server)

def myNetwork():

    net = Mininet( topo=None,
                   build=False,
                   ipBase='10.0.0.0/8')

    info( '*** Adding controller\n' )
    info( '*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')

    info( '*** Add hosts\n')
    server = net.addHost('server', cls=Host, ip='10.0.0.2', defaultRoute=None)
    cache = net.addHost('cache', cls=Host, ip='10.0.0.3', defaultRoute=None)
    h1 = net.addHost('h1', cls=Host, ip='10.0.0.1', defaultRoute=None)

    info( '*** Add links\n')
    net.addLink(s1, server)
    net.addLink(h1, s1)
    net.addLink(cache, s1)
    info( '*** Starting network\n')
    net.build()

    info( '*** Starting switches\n')
    net.get('s1').start([])

    info( '*** Post configure switches and hosts\n')

    # set up directory
    h1, cache, server = setup_dir(h1, cache, server)
    # get directory
    dir_h1, dir_cache, dir_server = get_dir(h1, cache, server)

    # DEBUG: show dir
    print(dir_h1)
    print(dir_cache)
    print(dir_server)

    # open port 80 get data
    open_port(cache, server)
    time.sleep(1) # 1s

    #links
    link_host_cache = 'wget ' + '10.0.0.3/'
    link_cache_server = 'wget ' + '10.0.0.2/'

    # DEBUG: testing with input
    # request = raw_input('request file:')
    # full_link = link_cache_server + request
    # print(cache.cmd(full_link))

    # DEBUG: random; get file name; get size
    # files = get_memmory_info(dir_server)
    # numberOfRequests = raw_input('Number of requests:')
    # for i in range(int(numberOfRequests)):
    #     # unifrom
    #     print(random.choice(files))
    #
    # # get the size of memmory
    # get_memmory_size(dir_server)

    # DEBUG:  delete file from cache_data
    # request = raw_input('request file:')
    # fp = os.path.join(dir_cache, request)
    # os.remove(fp)

    numberOfRequests = raw_input('Number of requests:')

    FIFO(h1, cache, server, dir_cache, dir_server, link_host_cache, link_cache_server, numberOfRequests)


    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()
