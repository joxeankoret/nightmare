import cobra
import traceback

class TestObject:

    def __init__(self):
        self.x = 10
        self.y = 20
        self.z = 90

    def addToZ(self, val):
        self.z += val

    def getUser(self):
        return cobra.getUserInfo()

def accessTestObject( t ):
    assert( t.x == 10 )
    t.y = 333
    assert( t.y == 333 )
    t.addToZ( 10 )
    assert( t.z == 100 )

testfuncs = []

def addUnitTest( testfunc ):
    testfuncs.append( testfunc )

def runUnitTests():

    for testfunc in testfuncs:
        try:
            testfunc()
            print('%s: ok' % testfunc.__name__ )
        except Exception, e:
            traceback.print_exc()
            print('%s: %s' % (testfunc.__name__, e))

