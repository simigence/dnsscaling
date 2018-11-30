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

    def __init__(self, url, efs_path='', lets_encrypt_path='', test_mode=False):

        self.url = url
        self.test_mode = test_mode

        # hardcoded defaults
        if not efs_path:
            efs_path = '/home/ec2-user/efs/letsencryt/'
        if not lets_encrypt_path:
            lets_encrypt_path = '/etc/letsencrypt/'
        self.efs_path = efs_path
        self.lets_encrypt_path = lets_encrypt_path

        self.efs_cert_path = efs_path + self.url
        self.archive_cert_path = lets_encrypt_path + 'archive/' + self.url
        self.live_cert_path = lets_encrypt_path + 'live/' + self.url

        self.pem_files = ['fullchain.pem', 'privkey.pem', 'cert.pem', 'chain.pem']
        self.pem_1_files = ['fullchain1.pem', 'privkey1.pem', 'cert1.pem', 'chain1.pem']

        self.run_certbot = True
        if os.path.isdir(self.efs_cert_path):

            if not all([os.path.exists(os.path.join(self.efs_cert_path, pem)) for pem in self.pem_files]):
                # something is wrong with efs directory so delete to reset certs
                shutil.rmtree(self.efs_cert_path)
                os.makedirs(self.efs_cert_path)

            elif os.path.isdir(self.archive_cert_path):

                # check if all files are the same
                same = True
                for i, pem in enumerate(self.pem_files):

                    src = os.path.join(self.efs_cert_path, pem)
                    archive = os.path.join(self.archive_cert_path, self.pem_1_files[i])

                    with open(src, 'rb') as f1:
                        with open(archive, 'rb') as f2:
                            if f1.read() != f2.read():
                                same = False
                                break

                if not same:
                    shutil.rmtree(self.archive_cert_path)
                    os.makedirs(self.archive_cert_path)
                    self.copy_link()
                else:
                    self.run_certbot = False

            else:
                # if local doesn't exist create directory and copy all files
                os.makedirs(self.archive_cert_path)
                self.copy_link()

        elif os.path.isdir(self.archive_cert_path):

            # make the directory and copy contents
            os.makedirs(self.efs_cert_path)

            # need to copy the other direction
            for pem in self.pem_files:
                src = os.path.join(self.efs_cert_path, pem)
                archive = os.path.join(self.archive_cert_path, pem)
                shutil.copy2(archive, src)

        else:

            # need to run initial creation and copy of certification
            cmd = "/certbot-auto certonly --standalone --agree-tos -m soren@simigence.com -n -d " \
                  "{0} --debug && {1}".format(self.url, self._cat_copy())
            print("EXECUTE: {0}".format(cmd))
            if not self.test_mode:
                args = shlex.split(cmd)
                result = subprocess.call(args)

        if self.run_certbot:
            self.system_exec_certbot()

    def copy_link(self):

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

    def system_exec_certbot(self):

        pre_hook = "\"docker stop $(docker ps | grep haproxy | awk '{0}print $1{1}')\"".format('{', '}')
        post_hook = self._cat_copy()
        cmd = "/certbot-auto renew --pre-hook {0} --post-hook {1}".format(pre_hook, post_hook)
        print("EXECUTE: {0}".format(cmd))
        if not self.test_mode:
            args = shlex.split(cmd)
            result = subprocess.call(args)

    def _cat_copy(self):

        cat_copy = "\"sudo cat {1}live/{0}/fullchain.pem {1}live/{0}/privkey.pem > " \
                   "{1}simpa/haproxy.pem && sudo cp {1}live/{0}/*.pem {2}{0}\"".format(
            self.url, self.lets_encrypt_path, self.efs_path)

        return cat_copy


def run_sslcredentials():

    parser = argparse.ArgumentParser(description="Check for ssl credentials on centralized system")

    parser.add_argument('-u', '--url', type=str, default='', help="Domain url for ssl")

    args = parser.parse_args()

    if not args.url:
        parser.print_help()
        sys.exit()

    ssl = SslCredentials(args.url)
