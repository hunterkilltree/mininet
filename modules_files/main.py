#!/usr/bin/python

import subprocess
from src.add import add
from src.sub import sub

# check to see if this is the main thread of execution
if __name__ == '__main__':
    print('main files')

    result = add(5, 9)
    print(result)

    result = sub(9, 5 )
    print(result)

    subprocess.call('./clean.sh')
