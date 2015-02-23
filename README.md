# Blockchain Resolver

Netki Blockchain (Namecoin) Resolver Library

# General

A resolver library that resolves Blockchain-based (*Namecoin*) domain names and uses **DNSSEC** to validate
the results of the query.  Blockchain-based (Namecoin) domains currently reside in the .bit TLD. For more information about 
Namecoin, please visit the [Namecoin WIKI](https://wiki.namecoin.info/).

# Requirements

- Access to a **Namecoin** node (this module uses the *name_show* RPC call).

## Python Modules
- [dnspython](http://www.dnspython.org) - http://www.dnspython.org
- [requests](http://docs.python-requests.org/en/latest/) - http://docs.python-requests.org/en/latest/
- [pyUnbound](https://www.unbound.net/documentation/pyunbound/) - https://www.unbound.net/documentation/pyunbound/

**NOTE:** pyUnbound is **NOT** available via pip. Please follow the instructions below to install and setup PyUnbound

# PyUnbound Setup
This version of **bcresolver** has been tested with Unbound v1.4.22. ([https://unbound.net/downloads/unbound-1.4.22.tar.gz](https://unbound.net/downloads/unbound-1.4.22.tar.gz))

## Install via Repository

**unbound-python** is available via installation by yum and is available in the [EPEL](https://fedoraproject.org/wiki/EPEL) repository.

    [user@host ~]$ yum install -y unbound-python
    
This will install unbound-python, compat-libevent, and unbound-libs packages.

## Manual Download, Installation and Setup 

When ./configure-ing unbound, make sure to use the **--with-pyunbound** flag. This will make pyunbound available after make and make install

Please refer to [https://www.unbound.net/documentation/pyunbound/install.html](https://www.unbound.net/documentation/pyunbound/install.html) for Unbound installation help.

Use the [unbound-anchor](https://www.unbound.net/documentation/unbound-anchor.html) tool to setup the ICANN-supplied DNSSEC Root Trust Anchor.

Make sure to set the **PYTHON_VERSION** environment variable if you have multiple *Python* versions installed, otherwise
the module will be installed for the default system *Python* version.

    [user@host ~]$ export set PYTHON_VERSION=2.7
    [user@host ~]$ wget https://unbound.net/downloads/unbound-1.4.22.tar.gz
    [user@host ~]$ tar -xzf unbound-1.4.22-py.tar.gz
    [user@host ~]$ cd unbound-1.4.22
    [user@host ~]$ ./configure --with-pyunbound
    [user@host ~]$ make
    [user@host ~]$ make install
    
# Usage

**blockchain-resolver** provides the bcresolver.NamecoinResolver class which has the resolve(name, qtype) function available. 
This can be used to resolve a Namecoin-based DNS entry using Namecoin-stored NS and DS records and then chaining up to standard DNS+DNSSEC using that 
information as the trust anchor.

**NOTE:** We recommend setting the temp_dir parameter to a ramdisk-backed directory to prevent disk thrashing.

## Success Example

    >>> from bcresolver import NamecoinResolver
    >>> nc_resolver = NamecoinResolver(
    ... host='127.0.0.1',
    ... user='namecoin',
    ... password='XXXXXXXXXXXXXXXX',
    ... port=8336,
    ... temp_dir=None)
    >>> nc_resolver.resolve('_wallet.wallet.mattdavid.bit', 'TXT')
    btc
    
    >>> nc_resolver.resolve('www.mattdavid.bit', 'A')
    108.162.204.31
    
    >>> nc_resolver.resolve('www2.mattdavid.bit', 'CNAME')
    www.mattdavid.bit.
    
    >>> nc_resolver.resolve('mattdavid.bit', 'MX')
    (10, 'mx.mattdavid.bit.')
    
    >>> nc_resolver.resolve('_btc._wallet.sample.walletname.bit', 'TXT')
    1CpLXM15vjULK3ZPGUTDMUcGATGR9xGitv

## No DS Records in Namecoin Value Example

    >>> from bcresolver import NamecoinResolver
    >>> nc_resolver = NamecoinResolver(
    ... host='127.0.0.1',
    ... user='namecoin',
    ... password='XXXXXXXXXXXXXXXX',
    ... port=8336,
    ... temp_dir=None)
    >>> nc_resolver.resolve('www.explorer.bit', 'A')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "bcresolver/__init__.py", line 162, in resolve
        raise NoDSRecordException()
    bcresolver.NoDSRecordException

## Additional Examples

See the examples/ directory for additional use examples for this module.