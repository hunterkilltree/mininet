

import argparse
import json

def my_test(topology):
    with open(topology) as complex_data:
        data = complex_data.read()
        print(data)


# check to see if this is the main thread of execution
if __name__ == '__main__':
    #construct the argument parser and parse command line argument
    parser = argparse.ArgumentParser()
    parser.add_argument('--r', '--read', type=str, help='read json file')

    args = vars(parser.parse_args())

    json_dir = args['r']
    my_test(json_dir)
