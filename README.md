# dnsscaling
A script used to automatically add/delete A records for a server in an AWS autoscaling group on startup 
and termination.  The script will pick up the public ipaddress from the server on startup
 and add an A record for the specified domain.   Then on termination it will delete the same A record. 
 
Configured by adding appropriate commands to the user-data text.

Needed commands in AWS user-data file to add the ipaddress of the server as an A record

    curl -O https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py --user
    sudo yum install -y git
    sudo ~/.local/bin/pip install git+https://github.com/simigence/dnsscaling.git
    dnsscaling -a <subdomain>.<domain.ending>

Needed commands in the AWS user-data file to delete the A record of the server on termination
  
For local debugging via ssh

    sudo ~/.local/bin/pip uninstall dnsscaling   # for uninstalling in ssh
   
The script uses the AWS EFS file system to store dnsmadeeasy credentials. The path

    ~/efs/credentials/dnsmadeeasy/dme_credentials.json

must exist and hold a json of ```{"apikey': "<apikey>",  "apisecret": "<apisecret>"}``` needed
to access the dnsmadeeasy api.


# needed in /etc/dnsscalingdelete
    # /usr/local/bin/dnsscaling -d junktmp.simpa.io
# sudo ln -s /etc/dnsscalingdelete /etc/rc0.d/S01dnsscalingdelete