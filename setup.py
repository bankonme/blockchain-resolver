from setuptools import setup

install_requires = [
    'dnspython>=1.12.0',
    'requests>=2.5.1'
]

test_requires = [
    'mock>=1.0.1'
]

setup(
    name='bcresolver',
    version='0.0.2',
    packages=['bcresolver'],
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='tests',
    url='https://github.com/netkicorp/blockchain-resolver',
    download_url='https://github.com/netkicorp/blockchain-resolver/tarball/0.0.2',
    platforms=['any'],
    license='BSD',
    author='mdavid',
    author_email='opensource@netki.com',
    description='Blockchain to DNS with DNSSEC Resolver Library'
)

print('\n*** Requirement pyUnbound is not available via pip. Please see README.md for installation information ***')