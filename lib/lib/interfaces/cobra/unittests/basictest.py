import cobra
import cobra.unittests as c_unittests

def basictest():

    testobj = c_unittests.TestObject()

    daemon = cobra.CobraDaemon(port=60600)
    objname = daemon.shareObject( testobj )
    daemon.fireThread()

    t = cobra.CobraProxy('cobra://localhost:60600/%s' % objname)
    c_unittests.accessTestObject( t )

c_unittests.addUnitTest( basictest )

