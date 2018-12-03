
import os
import shutil
import tempfile
import unittest

from dnsscaling.ssl_credentials import SslCredentials

PEMFILES = ['fullchain.pem', 'privkey.pem', 'cert.pem', 'chain.pem']
PEM1FILES = ['fullchain1.pem', 'privkey1.pem', 'cert1.pem', 'chain1.pem']


class TestSslCredentials(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tdir = tempfile.mkdtemp(dir='./')
        cls.url = 'tmp.url.com'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tdir)
        pass

    def _get_paths(self, intermediate_dir):

        efspath = os.path.join(self.tdir, intermediate_dir, 'efs') + '/'
        letsencrypt = os.path.join(self.tdir, intermediate_dir, 'letsencrypt') + '/'

        return efspath, letsencrypt

    def _write_certs(self, dir, value):

        for pem in PEMFILES:
            with open(os.path.join(dir, pem), 'wb') as f:
                f.write(pem + value)

    def test_empty_efs(self):

        ep, lp = self._get_paths('empty')
        os.makedirs(ep + self.url)

        s = SslCredentials(self.url, 'dummy@email.com', efs_path=ep, lets_encrypt_path=lp, test_mode=True)
        self.assertEqual(True, os.path.exists(ep + self.url))

    def test_start_efs(self):

        subdir = 'start'
        ep, lp = self._get_paths(subdir)
        os.makedirs(ep + self.url)
        self._write_certs(ep + self.url, 'p')

        s = SslCredentials(self.url, 'demail@email.com', efs_path=ep, lets_encrypt_path=lp, test_mode=True)

        ap = os.path.join(self.tdir, subdir, 'letsencrypt/archive', self.url)
        lp = os.path.join(self.tdir, subdir, 'letsencrypt/live', self.url)

        self.assertTrue(all([os.path.exists(os.path.join(ap, p)) for p in PEM1FILES]))
        self.assertTrue(all([os.path.exists(os.path.join(lp, p)) for p in PEMFILES]))

        for i, p in enumerate(PEMFILES):
            with open(os.path.join(ep + self.url, p)) as f:
                with open(os.path.join(ap, PEM1FILES[i])) as f1:
                    self.assertEqual(f.read(), f1.read())


if __name__ == '__main__':
    unittest.main()
