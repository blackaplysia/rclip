#!/usr/bin/env python3

import argparse
import errno
import io
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
    message = None

    res = None
    try:
        res = requests.get(url)
    except Exception as e:
        print(e, file=sys.stderr)
        return (errno.ENOENT, None)

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

    return (0, message)

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

def push(url, url_keys, filename, ttl, chunk_size):
    file_size = os.path.getsize(filename)
    keys = []
    fd = None

    if chunk_size:
        chunk_size = int(chunk_size)
    else:
        chunk_size = 1000000

    try:
        fd = open(filename, 'rb')
        read_size = 0
        file_number = 0
        while read_size < file_size:
            fd.seek(read_size)
            data = fd.read(chunk_size)
            bd = io.BytesIO(data)

            files = {
                'file': (f'{filename}.{file_number}', bd, 'application/octet-stream')
            }

            res = requests.post(url, files=files)
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
                    keys.append(key)

            read_size = read_size + len(data)
            file_number = file_number + 1

        fd.close()

    except Exception as e:
        if fd is not None:
            fd.close()
        print(e, file=sys.stderr)
        return errno.ENOENT

    if len(keys) > 0:
        return send(url_keys, None, ':'.join(keys), ttl)

    return 0

def pull(url_base, url_keys, filename):

    (key_status, key_list) = receive(url_keys)
    if key_status != 0:
        return key_status

    keys = key_list.split(':')

    try:
        fd = open(filename, 'wb')

        for key in keys:
            res = requests.get(url_base + key)
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
    subparser_push.add_argument('-T', '--ttl', nargs=1, help='time to live')
    subparser_push.add_argument('-C', '--chunksize', nargs=1, help='chunk size')
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
        (exit_status, message) = receive(url)
    elif method == 'delete' or method == 'd':
        url = urljoin(api, base_messages + args.key[0])
        exit_status = delete(url)
    elif method == 'push':
        url = urljoin(api, base_files)
        url_keys = urljoin(api, base_messages)
        f = args.file[0]
        ttl = args.ttl[0] if args.ttl else None
        chunksize = args.chunksize[0] if args.chunksize else None
        exit_status = push(url, url_keys, f, ttl, chunksize)
    elif method == 'pull':
        url_base = urljoin(api, base_files)
        url_keys = urljoin(api, base_messages + args.key[0])
        f = args.file[0]
        exit_status = pull(url_base, url_keys, f)
    elif method == 'ping':
        url = urljoin(api, base_clipboard)
        exit_status = ping(url, args.client)
    elif method == 'flush':
        url = urljoin(api, base_clipboard)
        exit_status = flush(url)

    return exit_status

if __name__ == '__main__':
    exit(main())
