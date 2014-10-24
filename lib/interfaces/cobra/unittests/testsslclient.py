

import cobra

cobra.verbose = True

#p = cobra.CobraProxy('cobrassl://localhost/woot', sslca='ca.crt', sslkey='client.key', sslcrt='client.crt')
p = cobra.CobraProxy('cobrassl://localhost/woot', sslca='ca.crt')
print p.printwoot('blah')
