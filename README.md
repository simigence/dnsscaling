# dnsscaling
Basic api to DNS Made Easy to add and remove A records.   Used for AWS cloud deployments.

Needed commands in AWS user-data file to add the ipaddress of the server as an A record

    curl -O https://bootstrap.pypa.io/get-pip.py
    sudo yum install git
    sudo ~/.local/bin/pip install git+https://github.com/simigence/dnsscaling.git
    dnsscaling -a {subdomain}.{domain.com}

Needed commands in the AWS user-data file to delete the A record of the server on termination
  
For local debugging via ssh

    sudo ~/.local/bin/pip uninstall dnsscaling   # for uninstalling in ssh

