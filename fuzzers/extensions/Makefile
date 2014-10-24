CXXFLAGS=-Wall -D_GNU_SOURCE -fPIC -shared
LDLIBS=-ldl -lmcheck

.libdisable_signal.so:
	g++ $(CXXFLAGS) disable_signal.cpp -o libdisable_signal.so $(LDLIBS)

.libdisable_signal32.so:
	g++ $(CXXFLAGS) -m32 disable_signal.cpp -o libdisable_signal32.so $(LDLIBS)

all: .libdisable_signal.so .libdisable_signal32.so

help:
	@echo "Usage: make (32|64|all|clean)"
	@echo
	@echo "32			Build the 32bit version of the library."
	@echo "64			Build the 64bit version of the library."
	@echo "All		Build both 32 and 64bit versions of the library."
	@echo "Clean	Clean all the generated objects."

64: .libdisable_signal.so

32:	.libdisable_signal32.so

clean:
	rm -f core libdisable_signal.so libdisable_signal32.so
