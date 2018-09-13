"""
Script to perform DNS made easy api calls
"""

from datetime import datetime
import hashlib
import hmac
import json
import os
import requests




class DnsMeApi(object):

    def __init__(self, apikey: str='', apisecret: str=''):

        self.url = 'https://api.dnsmadeeasy.com/V2.0/dns/managed'

        if not apikey:
            apikey = os.environ['DNSME_APIKEY']
        if not apisecret:
            apisecret = os.environ['DNSME_APISECRET']

        self.apisecret = apisecret
        self.apikey = apikey

    @staticmethod
    def _get_str_time() -> str:
        return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    @staticmethod
    def _get_dns_hash(message: str, key: str) -> str:
        return hmac.new(key.encode('utf-8'), message.encode('utf-8'), hashlib.sha1).hexdigest()

    def _create_headers(self):

        request_date = self._get_str_time()
        hmac = self._get_dns_hash(request_date, self.apisecret)
        headers = {
            'x-dnsme-apiKey': apikey,
            'x-dnsme-requestDate': request_date,
            'x-dnsme-hmac': hmac,
            'Content-Type': 'application/json'
        }
        headers['Content-Type'] = 'application/json'

        return headers

    def _get(self, url: str, sub: str=''):

        headers = self._create_headers()

        r = requests.get(url, headers=headers)
        if r.status_code != 200 and r.status_code != 201:
            raise Exception(f'Code {r.status_code}: {r.text}')

        content = json.loads(r.content)
        if sub:
            return content[sub]
        return content

    def _post(self, url: str, data: dict, sub: str=''):

        headers = self._create_headers()
        r = requests.post(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        if r.status_code != 200 and r.status_code != 201:
            print(r)
            raise Exception(f'Code {r.status_code}: Something went wrong with POST')

        content = json.loads(r.content)
        if sub:
            return content['sub']
        return content

    def _delete(self, url: str):

        headers = self._create_headers()
        r = requests.delete(url, headers=headers)
        if r.status_code != 200 and r.status_code != 201:
            print(r)
            raise Exception(f'Code {r.status_code}')
        return r

    def _get_account_data(self) -> list:
        return self._get(self.url, sub='data')

    def get_site_id(self, site: str) -> str:

        data = self._get_account_data()

        for d in data:
            if d['name'] == site:
                return d['id']

        return ''

    def get_records(self, site: str, type: str='', name: str='', value: str=''):
        site_id = self.get_site_id(site)
        return self._get_records(site_id, type=type, name=name, value=value)

    def _get_records(self, site_id: str, type: str='', name: str='', value: str=''):

        targurl = self.url + f'/{site_id}/records'

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

    def add_a_record(self, site: str, name: str, ipaddress: str, ttl: int=86400):

        site_id = self.get_site_id(site)
        targurl = self.url + f'/{site_id}/records/'

        data = {'name': name, 'type': 'A', 'value': ipaddress, 'gtdLocation': 'DEFAULT', 'ttl': ttl}
        content = self._post(targurl, data)

    def delete_a_record(self, site: str, name: str):

        site_id = self.get_site_id(site)
        r = self._get_records(site_id, type='A', name=name)
        if len(r) != 1:
            print(r)
            raise Exception('Not valid lenght of return values')

        name_id = r[0]['id']
        targurl = self.url + f'/{site_id}/records/{name_id}'
        content = self._delete(targurl)


if __name__ == '__main__':

    D = DnsMeApi(apikey=apikey, apisecret=secretkey)
    D.add_a_record('simpa.io', 'testdomain2', '11.14.1.111')
    D.delete_a_record('simpa.io', 'testdomain2')

