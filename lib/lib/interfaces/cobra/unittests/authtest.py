import cobra
import cobra.auth as c_auth
import cobra.unittests as c_unittests

def authtest():

    testobj = c_unittests.TestObject()

    daemon = cobra.CobraDaemon(port=60601)
    daemon.setAuthModule( c_auth.CobraAuthenticator() )
    daemon.fireThread()

    objname = daemon.shareObject( testobj )

    # Lets fail because of no-auth first
    try:
        p = cobra.CobraProxy('cobra://localhost:60601/%s' % objname)
        raise Exception('Allowed un-authd connection!')
    except cobra.CobraAuthException, e:
        pass

    # Now fail with wrong auth
    try:
        p = cobra.CobraProxy('cobra://localhost:60601/%s' % objname, authinfo={})
        raise Exception('Allowed bad-auth connection!')
    except cobra.CobraAuthException, e:
        pass

    # Now lets succeed
    authinfo = { 'user':'invisigoth', 'passwd':'secret' }
    t = cobra.CobraProxy('cobra://localhost:60601/%s' % objname, authinfo=authinfo)
    c_unittests.accessTestObject( t )

c_unittests.addUnitTest( authtest )
