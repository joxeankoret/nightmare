
import cobra
import cobra.unittests as c_unittests

def msgpacktest():

    testobj = c_unittests.TestObject()

    daemon = cobra.CobraDaemon(port=60610, msgpack=True)
    objname = daemon.shareObject( testobj )
    daemon.fireThread()

    t = cobra.CobraProxy('cobra://localhost:60610/%s?msgpack=1' % objname)
    c_unittests.accessTestObject( t )

c_unittests.addUnitTest( msgpacktest )
