import os

def CountNumberOfFiles(tempPath, folder):
    new_name = os.path.join(path, folder)
    #print(new_name)
    files = os.listdir(new_name)
    return len(files)


if __name__ == '__main__':

    # Change path before run
    path = '/home/lqt/Desktop/Project11_test_code/data'

    FilesInCaches = 0
    FilesInMain = 0
    FilesInClients = 0

    subdirs = [os.path.join(path, o) for o in os.listdir(path) if os.path.isdir(os.path.join(path,o))]
    files = os.listdir(path)
    temp = 0

    print("=============================CLIENTS========================")
    for i in files:
        if "client" in i:
            temp = CountNumberOfFiles(path,i)
            print("{} : {}".format(i, temp) )
            FilesInClients += temp

    print("=============================CACHE==========================")
    for i in files:
        if "cache" in i:
            temp = CountNumberOfFiles(path,i)
            print("{} : {}".format(i, temp) )
            FilesInCaches += temp
    print("=============================MAIN===========================")
    print("{} : {}".format("mainServer", CountNumberOfFiles(path, "mainServer")) )


    print("======================FINAL RESULT==========================")
    print("Total files in Caches: {}".format(FilesInCaches))
    print("Total files in clients:{} ".format(FilesInClients))
    print("Total files in MainServer : {}".format(FilesInMain))
