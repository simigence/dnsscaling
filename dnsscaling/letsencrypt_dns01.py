
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import josepy as jose
import OpenSSL
import re
import time

from acme import challenges
from acme import client
from acme import crypto_util
from acme import messages

from dnsscaling.dnsapi import DnsMeApi

# Constants:

# This is the staging point for ACME-V2 within Let's Encrypt.
DIRECTORY_URL = 'https://acme-staging-v02.api.letsencrypt.org/directory'
PROD_DIRECTORY_URL = 'https://acme-v02.api.letsencrypt.org/directory'

USER_AGENT = 'python-acme'
EMAIL = 'soren@simpa.io'


# Account key size
ACC_KEY_BITS = 2048
# Certificate private key size
CERT_PKEY_BITS = 2048

# Domain name for the certificate.
DOMAIN = 'simpa.io'


def new_csr_comp(domain_name, pkey_pem=None):
    """Create certificate signing request."""
    if pkey_pem is None:
        # Create private key.
        pkey = OpenSSL.crypto.PKey()
        pkey.generate_key(OpenSSL.crypto.TYPE_RSA, CERT_PKEY_BITS)
        pkey_pem = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, pkey)
    csr_pem = crypto_util.make_csr(pkey_pem, [domain_name])
    return pkey_pem, csr_pem


def select_dns01_chall(orderr):
    """Extract authorization resource from within order resource."""
    # Authorization Resource: authz.
    # This object holds the offered challenges by the server and their status.
    authz_list = orderr.authorizations

    for authz in authz_list:
        # Choosing challenge.
        # authz.body.challenges is a set of ChallengeBody objects.
        for i in authz.body.challenges:
            # Find the supported challenge.
            if isinstance(i.chall, challenges.DNS01):
                return i

    raise Exception('HTTP-01 challenge was not offered by the CA server.')


def create_dns01(production=False, wildcard=True, dnsme_credentials_file='dme_credentials.json'):
    """This example executes the whole process of fulfilling a HTTP-01
    challenge for one specific domain.
    The workflow consists of:
    (Account creation)
    - Create account key
    - Register account and accept TOS
    (Certificate actions)
    - WWite DNS value
    - Issue certificate
    - Renew certificate
    - Revoke certificate
    (Account update actions)
    - Change contact information
    - Deactivate Account
    """
    # Create account key

    acc_key = jose.JWKRSA(
        key=rsa.generate_private_key(public_exponent=65537,
                                     key_size=ACC_KEY_BITS,
                                     backend=default_backend()))

    # Register account and accept TOS
    if production:
        directory_url = PROD_DIRECTORY_URL
    else:
        directory_url = DIRECTORY_URL

    net = client.ClientNetwork(acc_key, user_agent=USER_AGENT)
    directory = messages.Directory.from_json(net.get(directory_url).json())
    client_acme = client.ClientV2(directory, net=net)

    # Terms of Service URL is in client_acme.directory.meta.terms_of_service
    # Registration Resource: regr
    # Creates account with contact information.
    email = (EMAIL)
    msg = messages.NewRegistration.from_data(
            email=email, terms_of_service_agreed=True)
    regr = client_acme.new_account(msg)

    # Create domain private key and CSR
    domain = DOMAIN
    if wildcard:
        domain = f'*.{DOMAIN}'
    print("GETTING CERT FOR", domain)
    pkey_pem, csr_pem = new_csr_comp(domain)

    # Issue certificate
    orderr = client_acme.new_order(csr_pem)

    # Select DNS01 within offered challenges by the CA server
    challb = select_dns01_chall(orderr)
    response, validation = challb.response_and_validation(client_acme.net.key)

    # write challenge to DNS made easy
    dnsme = DnsMeApi(test_mode=True, credentials_json=dnsme_credentials_file)
    dnsme.delete_txt_record(DOMAIN, '_acme-challenge')
    success = dnsme.add_txt_record(DOMAIN, '_acme-challenge', validation)
    time.sleep(8)
    print("Trying challenge...")

    try:
        # get full pem via challenge
        x = client_acme.answer_challenge(challb, response)
        finalized_orderr = client_acme.poll_and_finalize(orderr)
        fullpem = finalized_orderr.fullchain_pem

        s = fullpem + pkey_pem.decode()
        s = re.sub(f'\n+', '\n', s)
        with open('haproxy.pem', 'w') as proxypem:
            proxypem.write(s)
    finally:
        # delete
        dnsme.delete_txt_record(DOMAIN, '_acme-challenge')


    '''
    # Renew certificate
    _, csr_pem = new_csr_comp(DOMAIN, pkey_pem)

    orderr = client_acme.new_order(csr_pem)

    challb = select_dns01_chall(orderr)

    # Performing challenge
    fullchain_pem = perform_http01(client_acme, challb, orderr)

    # Revoke certificate

    fullchain_com = jose.ComparableX509(
        OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM, fullchain_pem))

    try:
        client_acme.revoke(fullchain_com, 0)  # revocation reason = 0
    except errors.ConflictError:
        # Certificate already revoked.
        pass

    # Query registration status.
    client_acme.net.account = regr
    try:
        regr = client_acme.query_registration(regr)
    except errors.Error as err:
        if err.typ == messages.OLD_ERROR_PREFIX + 'unauthorized' \
                or err.typ == messages.ERROR_PREFIX + 'unauthorized':
            # Status is deactivated.
            pass
        raise

    # Change contact information
    email = 'newfake@example.com'
    regr = client_acme.update_registration(
        regr.update(
            body=regr.body.update(
                contact=('mailto:' + email,)
            )
        )
    )

    # Deactivate account/registration
    regr = client_acme.deactivate_registration(regr)
    '''


if __name__ == "__main__":
    create_dns01(production=False, wildcard=True)