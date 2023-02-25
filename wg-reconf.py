#!/usr/bin/env python3

import argparse
import ipaddress
import itertools
import os
from pathlib import Path
from typing import List

def flatten(l):
    return (item for sublist in l for item in sublist)

def update_key(config: str, key: str, mapper) -> str:
    def update_line(line: str) -> str:
        if key not in line:
            return line
        [orig_key, values] = line.split('=')
        if orig_key.strip() != key:
            return line

        new_values = ', '.join(mapper(
            [value.strip() for value in values.split(',')]))
        return f'{key.strip()} = {new_values}'

    return '\n'.join(
        update_line(line) for line in config.split('\n')
    )

def exclude_ip(ip_addresses: List[str], exclude_ip_address: str):
    def exclude(ip, exclude):
        if ip.supernet_of(exclude):
            return list(ip.address_exclude(exclude))
        return [ip]

    def parse_or_none(t):
        def parse(s):
            try:
                return t(s)
            except ipaddress.AddressValueError:
                return None
        return parse

    ipv4_addresses = (x for x in map(parse_or_none(ipaddress.IPv4Network), ip_addresses) if x is not None)
    ipv6_addresses = (x for x in map(parse_or_none(ipaddress.IPv6Network), ip_addresses) if x is not None)

    exclude_ip_address = ipaddress.IPv4Network(exclude_ip_address)

    ranges = (exclude(ip, exclude_ip_address) for ip in ipv4_addresses)
    ranges = (res_ip.compressed for res_ip in itertools.chain(flatten(ranges), ipv6_addresses))

    return ranges


def main(args):
    basedir = args.basedir
    exclude_addr = args.exclude_addr
    for filename in Path(basedir).glob('*.conf'):
        with filename.open('r', encoding='utf-8') as f:
            config = f.read()
        updated_config = update_key(config, 'AllowedIPs', lambda x: exclude_ip(x, exclude_addr))

        if config != updated_config:
            os.rename(filename, filename.with_suffix(filename.suffix + '~'))
            with filename.open('w', encoding='utf-8') as f:
                f.write(updated_config)


parser = argparse.ArgumentParser(
        prog = 'wg-reconf',
        description = 'Edits wireguard configuration files.')

parser.add_argument('basedir', default='.')
parser.add_argument('--exclude-addr',
    dest='exclude_addr',
    help='The range of IPv4 addresses to exclude from AllowedIPs.',
    required=True)
args = parser.parse_args()

main(args)
