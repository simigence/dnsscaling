
from string import Template

_conf_script = Template(
'''
ARG1=-d
ARG2=$url
''')

_init_script_normal = \
'''
[Unit]
Description=Delete DNS IP
DefaultDependencies=no
Conflicts=reboot.target
Before=poweroff.target halt.target shutdown.target kexec.target
Requires=poweroff.target

[Service]
Type=oneshot
EnvironmentFile=/etc/.dnsscalingdeleteconf
ExecStart=/usr/bin/dnsscaling $ARG1 $ARG2
RemainAfterExit=yes
TimeoutStartSec=0

[Install]
WantedBy=shutdown.target poweroff.target halt.target kexec.target 
'''


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
        #f.write(_init_script.substitute({'url': url}).strip())
        f.write(_init_script_normal)


def write_args_file(url, path):
    with open(path + '.dnsscalingdeleteconf', 'w') as f:
        f.write(_conf_script.substitute({'url': url}).strip())
