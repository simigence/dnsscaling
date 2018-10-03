"""
Script to perform DNS made easy api calls
"""

import argparse
from datetime import datetime
import hashlib
import hmac
import json
import os
import requests
import sys


class DnsMeApi(object):

    def __init__(self, test_mode=False):

        self.url = 'https://api.dnsmadeeasy.com/V2.0/dns/managed'

        self.ipaddress = None
        if not test_mode:
            self.ipaddress = str(get_aws_ip())
            if not self.ipaddress:
                raise Exception('Could not find ip address')

        path = os.path.join(os.environ["HOME"], 'efs/credentials/dnsmadeeasy/dme_credentials.json')

        creds = json.loads(open(path, 'r').read().strip())
        self.apisecret = creds['apisecret']
        self.apikey = creds['apikey']

    @staticmethod
    def _get_str_time():
        return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    @staticmethod
    def _get_dns_hash(message, key):
        return hmac.new(key.encode('utf-8'), message.encode('utf-8'), hashlib.sha1).hexdigest()

    def _create_headers(self):

        request_date = self._get_str_time()
        hmac = self._get_dns_hash(request_date, self.apisecret)
        headers = {
            'x-dnsme-apiKey': self.apikey,
            'x-dnsme-requestDate': request_date,
            'x-dnsme-hmac': hmac,
            'Content-Type': 'application/json'
        }

        return headers

    def _get(self, url, sub=''):

        headers = self._create_headers()

        r = requests.get(url, headers=headers)
        if r.status_code != 200 and r.status_code != 201:
            s = 'Code ' + str(r.status_code) + ':' + str(r.text)
            raise Exception(s)

        content = json.loads(r.content)
        if sub:
            return content[sub]
        return content

    def _post(self, url, data, sub=''):

        headers = self._create_headers()
        r = requests.post(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        if r.status_code != 200 and r.status_code != 201:
            s = 'Code ' + str(r.status_code) + ' : Something went wrong with POST'
            raise Exception(s)

        content = json.loads(r.content)
        if sub:
            return content['sub']
        return content

    def _delete(self, url):

        headers = self._create_headers()
        r = requests.delete(url, headers=headers)
        if r.status_code != 200 and r.status_code != 201:
            s = 'Code ' + str(r.status_code)
            raise Exception(s)
        return r

    def _get_account_data(self):
        return self._get(self.url, sub='data')

    def _get_site_id(self, site):

        data = self._get_account_data()

        for d in data:
            if d['name'] == site:
                return str(d['id'])

        return ''

    def _get_records(self, site_id, type='', name='', value=''):

        targurl = self.url + '/' + str(site_id) + '/records'

        content = self._get(targurl, sub='data')

        if not type and not name and not value:
            return content

        ret_list = []
        for x in content:
            if type and not type == x['type']:
                continue
            if name and not name == x['name']:
                continue
            if value and not value == x['value']:
                continue
            ret_list.append(x)
        return ret_list

    def add_a_record(self, site, name, ipaddress, ttl=300):
        """
        Add an A record to the site with name and ipaddress.

        :param site:
        :param name:
        :param ipaddress:
        :param ttl:
        :return:
        """

        data = {'name': name, 'type': 'A', 'value': ipaddress, 'gtdLocation': 'DEFAULT', 'ttl': ttl}
        site_id = self._get_site_id(site)
        targurl = self.url + '/' + str(site_id) + '/records/'
        self._post(targurl, data)

    def delete_a_record(self, site, name, ipaddress=''):
        """
        Delete an A record from site.

        :param site:
        :param name:
        :return:
        """

        site_id = self._get_site_id(site)
        if not site_id:
            raise Exception("No site id found for", site)
        r = self._get_records(site_id, type='A', name=name)

        name_id = None
        if len(r) > 1 and not ipaddress:
            raise Exception('More than one IP address found for the record name, specify an ip address to delete.')
        elif len(r) == 0:
            s = 'No A records found for' + site + 'with' + name
            raise Exception(s)
        elif len(r) == 1:
            name_id = r[0]['id']
        else:
            for x in r:
                if x['value'] == ipaddress:
                    name_id = x['id']
        if not name_id:
            raise Exception('No id found for name or name and ipaddress')

        targurl = self.url + '/' + str(site_id) + '/records/' + str(name_id)
        self._delete(targurl)


def get_aws_ip():
    try:
        # check for aws ec2 instance
        r = requests.get('http://169.254.169.254/latest/meta-data/public-ipv4', timeout=0.25)
        aws_ip = r.text
    except:
        aws_ip = None
    return aws_ip


def get_domain(fulldomain):
    """Split the full domain into subdomain and domain"""
    subdomain = fulldomain.split('.')[0]
    domain = '.'.join(fulldomain.split('.')[1:])
    return subdomain, domain


def run_dnsscaling():

    parser = argparse.ArgumentParser(description="Dnsmadeeasy automatic A record assignment")

    parser.add_argument('-a', '--add_record', type=str, default='', help="Add an A record associated with the domain")
    parser.add_argument('-d', '--delete_record', type=str, default='', help="Delete an A record "
                                                                            "associated with the domain")

    if not len(sys.argv) > 1:
        parser.print_help()
        sys.exit()

    args = parser.parse_args()
    if (not args.add_record and not args.delete_record) or (args.add_record and args.delete_record):
        parser.print_help()
        sys.exit()

    D = DnsMeApi()

    if args.add_record:
        subdomain, domain = get_domain(args.add_record)
        print("ADDING", domain, subdomain, D.ipaddress)
        D.add_a_record(domain, subdomain, D.ipaddress)

    elif args.delete_record:
        subdomain, domain = get_domain(args.delete_record)
        print("DELETING", domain, subdomain, D.ipaddress)
        D.delete_a_record(domain, subdomain, ipaddress=D.ipaddress)


if __name__ == '__main__':

    D = DnsMeApi(test_mode=True)
    D.delete_a_record('simpa.io', 'junk2', '54.245.30.178')