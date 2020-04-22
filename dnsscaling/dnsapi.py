"""
Script to perform DNS made easy api calls
"""

import argparse
from datetime import datetime
import hashlib
import hmac
import json
import os
import urllib3
import sys
import time
import traceback

from dnsscaling import write_init_script


class DnsMeApi(object):

    def __init__(self, test_mode=False, credentials_json=''):

        self.url = 'https://api.dnsmadeeasy.com/V2.0/dns/managed'

        self.ipaddress = None
        if not test_mode:
            self.ipaddress = str(get_aws_ip())
            if not self.ipaddress:
                raise Exception('Could not find ip address')

        if not credentials_json:
            # hardcoded path where credentials must be stored
            credentials_json = '/home/ec2-user/efs/credentials/dnsmadeeasy/dme_credentials.json'

        creds = json.loads(open(credentials_json, 'r').read().strip())
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

        http = urllib3.PoolManager()
        r = http.request('GET', url=url, headers=headers)
        if r.status != 200 and r.status != 201:
            s = 'Code ' + str(r.status) + ':' + str(r.text)
            raise Exception(s)

        content = json.loads(r.data.decode('utf-8'))
        if sub:
            return content[sub]
        return content

    def _post(self, url, data, sub=''):

        headers = self._create_headers()
        http = urllib3.PoolManager()
        r = http.request('POST', url=url, headers=headers, body=json.dumps(data).encode('utf-8'))
        if r.status != 200 and r.status != 201:
            s = 'Code ' + str(r.status) + ' : Something went wrong with POST'
            raise Exception(s)

        content = json.loads(r.data.decode('utf-8'))
        if sub:
            return content['sub']
        return content

    def _delete(self, url):

        headers = self._create_headers()
        http = urllib3.PoolManager()
        r = http.request('DELETE', url=url, headers=headers)
        if r.status != 200 and r.status != 201:
            s = 'Code ' + str(r.status)
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

    def add_txt_record(self, site, name, value, ttl=30, robust=True):
        """
        Add an A record to the site with name and ipaddress.

        :param site:
        :param name:
        :param value:
        :param ttl:
        :param robust: will check that the cert exists after an add
        :return:
        """

        data = {'name': name, 'type': 'TXT', 'value': value, 'gtdLocation': 'DEFAULT', 'ttl': ttl}
        site_id = self._get_site_id(site)
        targurl = self.url + '/' + str(site_id) + '/records/'
        try:
            self._post(targurl, data)
        except:
            if robust:
                time.sleep(2)
                try:
                    self._post(targurl, data)
                except:
                    return False
            else:
                return False
        return True

    def add_a_record(self, site, name, ipaddress, ttl=30, robust=True):
        """
        Add an A record to the site with name and ipaddress.

        :param site:
        :param name:
        :param ipaddress:
        :param ttl:
        :param robust: will check that the cert exists after an add
        :return:
        """

        data = {'name': name, 'type': 'A', 'value': ipaddress, 'gtdLocation': 'DEFAULT', 'ttl': ttl}
        site_id = self._get_site_id(site)
        targurl = self.url + '/' + str(site_id) + '/records/'
        try:
            self._post(targurl, data)
            print('post success', targurl)
        except:
            if robust:
                time.sleep(2)
                try:
                    self._post(targurl, data)
                except:
                    pass
            else:
                pass

        if robust:
            # verify
            name_id = self._get_a_record_name(site_id, name, ipaddress)
            if not name_id:
                time.sleep(2)
                self._post(targurl, data)

    def delete_a_record(self, site, name, ipaddress=''):
        """
        Delete an A record from site.

        :param site:
        :param name:
        :return:
        """

        site_id = self._get_site_id(site)
        #with open('/home/ec2-user/efs/tmpdnsdelete.txt', 'a') as f:
        #    f.write('site id grabbed ' + ipaddress + '--' + site_id + '--\n')
        if not site_id:
            raise Exception("No site id found for", site)

        name_id = self._get_a_record_name(site_id, name, ipaddress)
        #with open('/home/ec2-user/efs/tmpdnsdelete.txt', 'a') as f:
        #    f.write('a record name ' + ipaddress + '--' + name_id + '--\n')

        targurl = self.url + '/' + str(site_id) + '/records/' + str(name_id)
        try:
            self._delete(targurl)
        except:
            time.sleep(1)
            self._delete(targurl)

    def _get_a_record_name(self, site_id, name, ipaddress):

        r = self._get_records(site_id, type='A', name=name)

        name_id = None
        if len(r) > 1 and not ipaddress:
            raise Exception('More than one IP address found for the record name, specify an ip address to delete.')
        elif len(r) == 0:
            s = 'No A records found with' + name + 'for site id' + site_id
            raise Exception(s)
        elif len(r) == 1:
            name_id = r[0]['id']
        else:
            for x in r:
                if x['value'] == ipaddress:
                    name_id = x['id']
        if not name_id:
            raise Exception('No id found for name or name and ipaddress')

        return name_id

    def delete_a_ip(self, site, ipaddress=''):

        site_id = self._get_site_id(site)
        r = dnsme._get_records(site_id, type='A', value=ipaddress)
        id_list = [x['id'] for x in r]

        for ip_id in id_list:
            targurl = self.url + '/' + str(site_id) + '/records/' + str(ip_id)
            try:
                self._delete(targurl)
                print('delete success', targurl)
            except:
                time.sleep(0.5)
                self._delete(targurl)
                print('delete success', targurl)


    def _get_a_record_ip(self, site_id, name, ipaddress):

        r = self._get_records(site_id, type='A', name=name)

        name_id = None
        if len(r) > 1 and not ipaddress:
            raise Exception('More than one IP address found for the record name, specify an ip address to delete.')
        elif len(r) == 0:
            s = 'No A records found with' + name + 'for site id' + site_id
            raise Exception(s)
        elif len(r) == 1:
            name_id = r[0]['id']
        else:
            for x in r:
                if x['value'] == ipaddress:
                    name_id = x['id']
        if not name_id:
            raise Exception('No id found for name or name and ipaddress')

        return name_id

    def delete_txt_record(self, site, name):
        """
        Delete all text records from site.

        :param site:
        :param name:
        :return:
        """

        site_id = self._get_site_id(site)
        if not site_id:
            raise Exception("No site id found for", site)

        records = self._get_records(site_id, type='TXT', name=name)
        for del_id in [x['id'] for x in records]:
            try:
                targurl = self.url + '/' + str(site_id) + '/records/' + str(del_id)
                self._delete(targurl)
                print('Deleted: targurl')
            except:
                print("ERROR deleting: {del_id}")


def get_aws_ip():
    try:
        # check for aws ec2 instance
        http = urllib3.PoolManager()
        r = http.request('GET', url='http://169.254.169.254/latest/meta-data/public-ipv4', timeout=0.5)
        aws_ip = r.data
    except:
        aws_ip = None
    return aws_ip


def get_domain(fulldomain):
    """Split the full domain into subdomain and domain"""
    domain = '.'.join(fulldomain.split('.')[-2:])
    subdomain = '.'.join(fulldomain.split('.')[0:-2])
    return subdomain, domain


def run_dnsscaling():

    parser = argparse.ArgumentParser(description="Dnsmadeeasy automatic A record assignment")

    parser.add_argument('-a', '--add_record', type=str, default='', help="Add an A record associated with the domain")
    parser.add_argument('-d', '--delete_record', type=str, default='', help="Delete an A record "
                                                                            "associated with the domain")
    parser.add_argument('-i', '--init_script', type=str, default='', help="Create and store the init script for the"
                                                                          "domain")


    if not len(sys.argv) > 1:
        parser.print_help()
        sys.exit()

    args = parser.parse_args()
    if args.init_script:
        # write new script
        write_init_script(args.init_script, '/etc/systemd/system/')
        sys.exit()

    elif (not args.add_record and not args.delete_record) or (args.add_record and args.delete_record):
        parser.print_help()
        sys.exit()

    D = DnsMeApi()

    if args.add_record:
        subdomain, domain = get_domain(args.add_record)
        print("ADDING", domain, subdomain, D.ipaddress)
        D.add_a_record(domain, subdomain, D.ipaddress)

    elif args.delete_record:

        s = 'shutdown ' + D.ipaddress + ' ' + str(time.time()) + '\n'
        #with open('/home/ec2-user/efs/tmpdnsdelete.txt', 'a') as f:
        #    f.write(s)
        subdomain, domain = get_domain(args.delete_record)
        print("DELETING", domain, subdomain, D.ipaddress)
        try:
            #with open('/home/ec2-user/efs/tmpdnsdelete.txt', 'a') as f:
            #    f.write('start ip call ' + D.ipaddress + '\n')
            D.delete_a_record(domain, subdomain, ipaddress=D.ipaddress)
            #with open('/home/ec2-user/efs/tmpdnsdelete.txt', 'a') as f:
            #    f.write('success ' + D.ipaddress + '\n')
        except:
            pass
            #with open('/home/ec2-user/efs/tmpdnsdelete.txt', 'a') as f:
            #    f.write('error ' + traceback.format_exc() + '\n')

if __name__ == '__main__':
    dnsme = DnsMeApi(test_mode=True, credentials_json='dme_credentials.json')
    iptest = '35.163.201.231'
    site = 'simpa.io'
    sttime = time.time()
    #dnsme.add_a_record('simpa.io', 'junk', iptest)
    dnsme.delete_a_ip(site, iptest)
    print(time.time()-sttime)

