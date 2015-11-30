set disassembly-flavor intel
set environment MALLOC_CHECK_=2
handle SIGPIPE nostop noprint
set follow-fork-mode child

run
echo @@@START-OF-CRASH\n

echo @@@PROGRAM-COUNTER\n

x /i $pc
echo @@@REGISTERS\n

i r
echo @@@START-OF-STACK-TRACE\n

back 128

echo @@@END-OF-STACK-TRACE\n

echo @@@START-OF-DISASSEMBLY-AT-PC\n

x /16i $pc-16

echo @@@END-OF-DISASSEMBLY-AT-PC\n

echo @@@END-OF-CRASH\n

quit
