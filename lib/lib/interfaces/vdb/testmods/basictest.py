import sys
import time
import ctypes
import threading

def dostuff():
    print '++ Hi! Im the new thread! (sleeping for 3)\n'
    time.sleep(3)
    print '++ Now Im going to memory fault (reading 0x41414141)\n'
    try:
        x = ctypes.string_at(0x41414141, 20)
    except Exception, e:
        print e
    print '++ Sorry... my bad... ;)'
    print '++ Now Im going to exit... (value 30)\n'
    return 30


if __name__ == '__main__':


    print '== You should see a thread create\n'
    t = threading.Thread(target=dostuff)
    t.setDaemon(True)
    t.start()

    print '== He should exit in a couple seconds (sleeping for 5)\n'
    time.sleep(5)

    print '== I will exit now...\n'


