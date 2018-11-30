"""
Object/script to manage ssl credentials with a centralized AWS EFS repository
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys


class SslCredentials(object):

    def __init__(self, url, email, efs_path='', lets_encrypt_path='', test_mode=False):

        self.url = url
        self.email = email
        self.test_mode = test_mode

        # hardcoded defaults
        if not efs_path:
            efs_path = '/home/ec2-user/efs/letsencrypt/'
        if not lets_encrypt_path:
            lets_encrypt_path = '/etc/letsencrypt/'
        self.efs_path = efs_path
        self.lets_encrypt_path = lets_encrypt_path

        self.efs_cert_path = efs_path + self.url
        self.archive_cert_path = lets_encrypt_path + 'archive/' + self.url
        self.live_cert_path = lets_encrypt_path + 'live/' + self.url

        self.pem_files = ['fullchain.pem', 'privkey.pem', 'cert.pem', 'chain.pem']
        self.pem_1_files = ['fullchain1.pem', 'privkey1.pem', 'cert1.pem', 'chain1.pem']

        if os.path.isdir(self.efs_cert_path):

            if not all([os.path.exists(os.path.join(self.efs_cert_path, pem)) for pem in self.pem_files]):
                # something is wrong with efs directory so delete to reset certs
                shutil.rmtree(self.efs_cert_path)
                os.makedirs(self.efs_cert_path)
                self.init_cert()

            elif os.path.isdir(self.live_cert_path):

                # check if all files are the same
                same = True
                for i, pem in enumerate(self.pem_files):

                    src = os.path.join(self.efs_cert_path, pem)
                    live = os.path.join(self.live_cert_path, pem)

                    if not os.path.exists(src) or not os.path.exists(live):
                        same = False
                        break

                    with open(src, 'rb') as f1:
                        with open(live, 'rb') as f2:
                            if f1.read() != f2.read():
                                same = False
                                break

                if not same:

                    shutil.rmtree(self.archive_cert_path)
                    shutil.rmtree(self.live_cert_path)
                    os.makedirs(self.archive_cert_path)
                    os.makedirs(self.live_cert_path)
                    self.copy_link_efs()

            else:
                # if local doesn't exist create directory and copy all files
                os.makedirs(self.archive_cert_path)
                os.makedirs(self.live_cert_path)
                self.copy_link_efs()

        elif os.path.isdir(self.live_cert_path):

            # make the directory and copy contents
            os.makedirs(self.efs_cert_path)

            # need to copy live certs to efs
            for i, pem in enumerate(self.pem_files):
                src = os.path.join(self.efs_cert_path, pem)
                live = os.path.join(self.live_cert_path, pem)
                shutil.copy2(live, src)

        else:

            self.init_cert()

        cmd = "/certbot-auto renew --pre-hook {0} --post-hook {1}".format(self._stop_haproxy_str(),
                                                                          self._cat_copy_str())
        self._execute_cmd(cmd)

    def init_cert(self):

        # need to run initial creation and copy of certification
        cmd = "/certbot-auto certonly --standalone --agree-tos -m {2} -n -d " \
              "{0} --debug && {1}".format(self.url, self._cat_copy_str(), self.email)
        self._execute_cmd(cmd)

    def copy_link_efs(self):

        # copy and symlink all files in live directory
        for i, pem in enumerate(self.pem_files):

            src = os.path.join(self.efs_cert_path, pem)
            live = os.path.join(self.live_cert_path, pem)

            archive = os.path.join(self.archive_cert_path, self.pem_1_files[i])
            shutil.copy2(src, archive)
            if not os.path.isdir(self.live_cert_path):
                os.makedirs(self.live_cert_path)

            archive_sym = '../../archive/' + self.url + '/' + self.pem_1_files[i]
            os.symlink(archive_sym, live)

        # prep command for haproxy and make sure efs in sync
        self._execute_cmd(self._cat_copy_str())
        # stop haproxy
        self._execute_cmd(self._stop_haproxy_str())

    def _execute_cmd(self, cmd):

        print("EXECUTE: {0}".format(cmd))
        if not self.test_mode:
            args = shlex.split(cmd)
            result = subprocess.call(args)

    def _stop_haproxy_str(self):
        return "\"docker stop $(docker ps | grep haproxy | awk '{0}print $1{1}')\"".format('{', '}')

    def _cat_copy_str(self):

        cat_copy = "\"sudo cat {1}live/{0}/fullchain.pem {1}live/{0}/privkey.pem > " \
                   "{1}simpa/haproxy.pem && sudo cp {1}live/{0}/*.pem {2}{0}\"".format(
            self.url, self.lets_encrypt_path, self.efs_path)

        return cat_copy


def run_sslcredentials():

    parser = argparse.ArgumentParser(description="Check for ssl credentials on centralized system")

    parser.add_argument('-u', '--url', type=str, default='', help="Domain url for ssl")
    parser.add_argument('-e', '--email', type=str, default='', help="Email for ssl initialization")

    args = parser.parse_args()

    if not args.url or not args.email:
        parser.print_help()
        sys.exit()

    ssl = SslCredentials(args.url, args.email)
