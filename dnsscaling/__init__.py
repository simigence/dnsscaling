
from string import Template


_init_script = Template(
'''
[Unit]
Description=Delete DNS IP
DefaultDependencies=false
Before=shutdown.target reboot.target

[Service]
Type=oneshot
ExecStart=/usr/bin/dnsscaling -d $url
ExecStop=/usr/bin/dnsscaling -d $url
RemainAfterExit=yes

[Install]
WantedBy=shutdown.target 
''')


_init_script_old = Template(
'''#!/bin/sh
# chkconfig: 345 99 1
# description: Script for DNS deregistration

start(){
    touch /var/lock/subsys/dnsscalingdelete
    sudo dnsscaling -a $url
    sleep 3
}

stop(){
    sudo dnsscaling -d $url
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
    with open(path + 'dnsscalingdelete.service', 'w') as f:
        f.write(_init_script.substitute({'url': url}).strip())
