
from string import Template

_init_script = Template(
'''#!/bin/sh
# chkconfig: 345 99 1
# Required-Start:    networking
# Required-Stop:     networking
# Default-Start:     345
# Default-Stop:      0126

# Source function library.
. /etc/rc.d/init.d/dnsscalingdelete

start(){
    touch /var/lock/subsys/dnsscalingdelete
}
stop(){
    sudo /usr/local/bin/dnsscaling -d $url
    sleep 3	
    rm -f /var/lock/subsys/dnsscalingdelete
}

restart(){
    stop
    start
}

case $$1 in
start)
        start
        ;;
stop)
        stop
        ;;
restart)
        restart
        ;;
*)
        echo "Wrong Argument"
        exit 1
esac
exit 0
''')


def write_init_script(url, path):
    with open(path + 'dnsscalingdelete', 'w') as f:
        f.write(_init_script.substitute({'url': url}).strip())
