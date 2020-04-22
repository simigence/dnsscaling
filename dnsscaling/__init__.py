
from string import Template


_init_script_normal = \
'''
[Unit]
Description=Delete DNS IP
DefaultDependencies=no
Before=poweroff.target halt.target shutdown.target reboot.target kexec.target

[Service]
Type=oneshot
ExecStart=/tmp/ip_removal.sh
RemainAfterExit=yes
KillMode=none

[Install]
WantedBy=poweroff.target halt.target shutdown.target reboot.target kexec.target
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

    with open('/etc/systemd/system/ip_removal.service', 'w') as f:
        f.write(_init_script_normal)

    with open('/tmp/ip_removal.sh', 'w') as f:
        s = '#!/bin/bash'
        s = s + '\nsudo touch /home/ec2-user/efs/dns_ip_addresses/remove/$(curl http://169.254.169.254/latest/meta-data/public-ipv4)'
        s = s + '\nsudo /usr/bin/dnsscaling -r $(curl http://169.254.169.254/latest/meta-data/public-ipv4)'
        f.write(s)
