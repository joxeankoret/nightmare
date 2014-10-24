import cobra

'''
# To make the CA key
openssl genrsa -des3 -out ca.key 4096
openssl req -new -x509 -days 365 -key ca.key -out ca.crt

# Making the server CSR
openssl genrsa -des3 -out server.key 4096
openssl req -new -key server.key -out server.csr

# Sign the server crt with the CA
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt
'''

cobra.verbose = True

class woot:

    def printwoot(self, x):
        print 'WOOT',x
        return 'DID WOOT'

d = cobra.CobraDaemon(sslcrt='server.crt',sslkey='server.key',)
#d = cobra.CobraDaemon(sslcrt='server.crt',sslkey='server.key',sslca='ca.crt')
d.shareObject(woot(), 'woot', doref=True)
d.serve_forever()
