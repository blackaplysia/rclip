#!/usr/bin/env python3

import argparse
import errno
import json
import os
import requests
import sys
from argparse import RawDescriptionHelpFormatter
from operator import attrgetter
from urllib.parse import urljoin

def send(url, filename, message, ttl):
    if message is None:
        fd = sys.stdin
        try:
            if filename is not None and filename != '-':
                fd = open(filename)
            message = fd.read()
            if fd != sys.stdin:
                fd.close()
        except Exception as e:
            print(e, file=sys.stderr)
            return errno.ENOENT

    data = {
        'message': message
    }
    if ttl is not None:
        data.update({
            'ttl': ttl
        })
    res = None
    try:
        res = requests.post(url, json=data)
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            key = text['response']['key']
            print(f'{key}')

    return 0

def receive(url):
    res = None
    try:
        res = requests.get(url)
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            message = text['response']['message']
            print(f'{message}', end='')

    return 0

def delete(url):
    res = None
    try:
        res = requests.delete(url)
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            print(f'{status}')

    return 0

def push(url, filename):
    res = None
    try:
        fd = open(filename, 'rb')
        files = {
            'file': (filename, fd, 'application/octet-stream')
        }
        try:
            res = requests.post(url, files=files)
        except Exception as e:
            print(e, file=sys.stderr)
            return errno.ENOENT

        fd.close()
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            key = text['response']['key']
            print(f'{key}')

    return 0

def pull(url, filename):
    res = None
    try:
        res = requests.get(url)
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            try:
                fd = open(filename, 'wb')
                fd.write(res.content)
                fd.close()
            except Exception as e:
                print(e, file=sys.stderr)
                return errno.ENOENT

    return 0

def ping(url, do_show_client_information):
    res = None
    try:
        res = requests.get(url)
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            acq = text['response']['acq']
            if do_show_client_information:
                host = text['response']['client']['host']
                port = text['response']['client']['port']
                print(f'{acq} {host} {port}')
            else:
                print(f'{acq}')

    return 0

def flush(url):
    res = None
    try:
        res = requests.delete(url)
    except Exception as e:
        print(e, file=sys.stderr)
        return errno.ENOENT

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            if text is not None:
                detail = text['detail']
                print(f'{status} {detail}')
            else:
                print(f'{status} ({content_type})')
        else:
            result = text['response']['result']
            print(f'{status} {result}')

    return 0

def main():

    class SortingHelpFormatter(RawDescriptionHelpFormatter):
        def add_arguments(self, actions):
            actions = sorted(actions, key=attrgetter('option_strings'))
            super(SortingHelpFormatter, self).add_arguments(actions)

    api = os.environ.get('RCLIP_API', 'http://localhost/')

    parser = argparse.ArgumentParser(description='Remote clip', formatter_class=SortingHelpFormatter,
                                     epilog=f'''Current message api url: {api}
You can modify this value with -a or $RCLIP_API.''')
    parser.add_argument('-a', '--api', nargs=1, help='message api url')
    subparsers = parser.add_subparsers(dest='subparser_name', title='methods')
    subparser_ping = subparsers.add_parser('ping', help='ping clipboard')
    subparser_ping.add_argument('-c', '--client', action='store_true', help='show client information')
    subparser_flush = subparsers.add_parser('flush', help='flush clipboard')
    subparser_send = subparsers.add_parser('send', aliases=['s'], help='send message')
    subparser_send.add_argument('-T', '--ttl', nargs=1, help='time to live')
    subparser_send_group = subparser_send.add_mutually_exclusive_group()
    subparser_send_group.add_argument('-f', '--file', nargs=1, help='message from file (\'-\' for stdin)')
    subparser_send_group.add_argument('-t', '--text', nargs=1, help='message text')
    subparser_receive = subparsers.add_parser('receive', aliases=['r'], help='receive message')
    subparser_receive.add_argument('key', nargs=1, help='message key')
    subparser_delete = subparsers.add_parser('delete', aliases=['d'], help='delete message')
    subparser_delete.add_argument('key', nargs=1, help='message key')
    subparser_push = subparsers.add_parser('push', help='push file')
    subparser_push.add_argument('file', nargs=1, help='source data file name')
    subparser_pull = subparsers.add_parser('pull', help='pull file')
    subparser_pull.add_argument('key', nargs=1, help='file key')
    subparser_pull.add_argument('file', nargs=1, help='destination data file name')

    if len(sys.argv) == 1:
        print(parser.format_usage(), file=sys.stderr)
        return 0

    args = parser.parse_args()

    if args.api:
        api = args.api[0]

    base_messages = '/api/v1/messages/'
    base_files = '/api/v1/files/'
    base_clipboard = '/api/v1/clipboard'
    method = args.subparser_name
    exit_status = 0
    if method == 'send' or method == 's':
        url = urljoin(api, base_messages)
        f = args.file[0] if args.file else None
        t = args.text[0] if args.text else None
        ttl = args.ttl[0] if args.ttl else None
        exit_status = send(url, f, t, ttl)
    elif method == 'receive' or method == 'r':
        url = urljoin(api, base_messages + args.key[0])
        exit_status = receive(url)
    elif method == 'delete' or method == 'd':
        url = urljoin(api, base_messages + args.key[0])
        exit_status = delete(url)
    elif method == 'push':
        url = urljoin(api, base_files)
        f = args.file[0]
        exit_status = push(url, f)
    elif method == 'pull':
        url = urljoin(api, base_files + args.key[0])
        f = args.file[0]
        exit_status = pull(url, f)
    elif method == 'ping':
        url = urljoin(api, base_clipboard)
        exit_status = ping(url, args.client)
    elif method == 'flush':
        url = urljoin(api, base_clipboard)
        exit_status = flush(url)

    return exit_status

if __name__ == '__main__':
    exit(main())
