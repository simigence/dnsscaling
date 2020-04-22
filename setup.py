

from setuptools import find_packages, setup
import io

setup(
    name='dnsscaling',
    version='0.0.1',
    description='DNS made easy scripts along with AWS interaction',
    long_description=io.open('README.md', 'r', encoding='utf-8').read(),
    classifiers=[''],
    keywords='',
    author='',
    author_email='',
    url='http://www.simigence.com',
    license='',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests',
        'urllib3',
    ],
    entry_points={
        'console_scripts': [
            'dnsscaling=dnsscaling.dnsapi:run_dnsscaling',
            'dnscertbot=dnsscaling.ssl_credentials:run_sslcredentials',
        ],
    },
)
