import os

import cobra
import cobra.unittests as c_unittests
import cobra.auth.shadowfile as c_auth_shadow

def shadowauth():

    testobj = c_unittests.TestObject()

    daemon = cobra.CobraDaemon(port=60602)
    shadowfile = os.path.join(os.path.dirname(__file__),'shadowpass.txt')
    authmod = c_auth_shadow.ShadowFileAuth( shadowfile )
    daemon.setAuthModule( authmod )

    daemon.fireThread()

    objname = daemon.shareObject( testobj )

    # Now lets succeed
    authinfo = { 'user':'invisigoth', 'passwd':'secret' }
    t = cobra.CobraProxy('cobra://localhost:60602/%s' % objname, authinfo=authinfo)
    c_unittests.accessTestObject( t )
    assert( t.getUser() == 'invisigoth' )

c_unittests.addUnitTest( shadowauth )
