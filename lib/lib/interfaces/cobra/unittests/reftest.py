
import cobra
import cobra.unittests as c_unittests

def reftest():

    testobj = c_unittests.TestObject()

    daemon = cobra.CobraDaemon(port=60660)
    objname = daemon.shareObject( testobj, doref=True )
    daemon.fireThread()

    with cobra.CobraProxy('cobra://localhost:60660/%s' % objname) as t:
        c_unittests.accessTestObject( t )

    assert( daemon.getSharedObject( objname ) == None )

c_unittests.addUnitTest( reftest )
