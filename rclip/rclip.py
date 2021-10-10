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
    out_status = 0
    out_message = None

    if message is None:
        fd = sys.stdin
        try:
            if filename is not None and filename != '-':
                fd = open(filename)
            message = fd.read()
            if fd != sys.stdin:
                fd.close()
        except Exception as e:
            exception_name = type(e).__name__
            detail = str(e)
            out_message = f'{exception_name} {detail}'
            return errno.EIO, out_message

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
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            out_status = errno.ENOENT
            if text is not None:
                detail = text['detail']
                out_message = f'{status} {detail}'
            else:
                out_message = f'{status} ({content_type})'
        else:
            out_message = text['response']['key']

    return out_status, out_message

def receive(url):
    out_status = 0
    out_message = None

    res = None
    try:
        res = requests.get(url)
    except Exception as e:
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            out_status = errno.ENOENT
            if text is not None:
                detail = text['detail']
                out_message = f'{status} {detail}'
            else:
                out_message = f'{status} ({content_type})'
        else:
            out_message = text['response']['message']

    return out_status, out_message

def delete(url):
    out_status = 0
    out_message = None

    res = None
    try:
        res = requests.delete(url)
    except Exception as e:
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            out_status = errno.ENOENT
            if text is not None:
                detail = text['detail']
                out_message = f'{status} {detail}'
            else:
                out_message = f'{status} ({content_type})'
        else:
            out_message = f'{status}'

    return out_status, out_message

def push(url, url_keys, filename, ttl, chunk_size):
    out_status = 0
    part_messages = []

    fd = None
    keys = []

    if chunk_size:
        chunk_size = int(chunk_size)
    else:
        chunk_size = 1000000

    try:
        file_size = os.path.getsize(filename)
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

            res = None
            try:
                res = requests.post(url, files=files)
            except Exception as e:
                out_status = errno.EIO
                exception_name = type(e).__name__
                detail = str(e)
                part_messages.append(f'#{file_number} {exception_name} {detail}')

            if res is not None:
                status = res.status_code
                content_type = res.headers['Content-Type']
                if content_type != 'application/json':
                    text = None
                else:
                    text = json.loads(res.text)

                if status >= 400:
                    out_status = errno.NOENT
                    if text is not None:
                        detail = text['detail']
                        part_messages.append(f'#{file_number} {status} {detail}')
                    else:
                        part_messages.append(f'#{file_number} {status} ({content_type})')
                else:
                    key = text['response']['key']
                    keys.append(key)

            read_size = read_size + len(data)
            file_number = file_number + 1

        fd.close()

    except Exception as e:
        if fd is not None:
            fd.close()
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if out_status != 0 or len(keys) == 0:
        out_message = '\n'.join(part_messages)
    else:
        out_status, out_message = send(url_keys, None, ':'.join(keys), ttl)

    return out_status, out_message

def pull(url_base, url_keys, filename):

    key_status, key_list = receive(url_keys)
    if key_status != 0:
        return key_status, key_list

    keys = key_list.split(':')
    if len(keys) == 0:
        return errno.ENOENT, key_list

    out_status = 0
    out_message = filename
    part_messages = []

    try:
        fd = open(filename, 'wb')

        for key in keys:
            res = None
            try:
                res = requests.get(url_base + key)
            except Exception as e:
                out_status = errno.EIO
                exception_name = type(e).__name__
                detail = str(e)
                part_messages.append(f'{key} {exception_name} {detail}')

            if res is not None:
                status = res.status_code
                content_type = res.headers['Content-Type']
                if content_type != 'application/json':
                    text = None
                else:
                    text = json.loads(res.text)

                if status >= 400:
                    out_status = errno.NOENT
                    if text is not None:
                        detail = text['detail']
                        part_messages.append(f'{key} {status} {detail}')
                    else:
                        part_messages.append(f'{key} {status} ({content_type})')
                else:
                    fd.write(res.content)
                    size = len(res.content)

        fd.close()
    except Exception as e:
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if out_status != 0:
        out_message = '\n'.join(part_messages)

    return out_status, out_message

def ping(url, do_show_client_information):
    out_status = 0
    out_message = None

    res = None
    try:
        res = requests.get(url)
    except Exception as e:
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            out_status = errno.ENOENT
            if text is not None:
                detail = text['detail']
                out_message = f'{status} {detail}'
            else:
                out_message = f'{status} ({content_type})'
        else:
            acq = text['response']['acq']
            if do_show_client_information:
                host = text['response']['client']['host']
                port = text['response']['client']['port']
                out_message = f'{acq} {host} {port}'
            else:
                out_message = f'{acq}'

    return out_status, out_message

def flush(url):
    out_status = 0
    out_message = None

    res = None
    try:
        res = requests.delete(url)
    except Exception as e:
        exception_name = type(e).__name__
        detail = str(e)
        out_message = f'{exception_name} {detail}'
        return errno.EIO, out_message

    if res is not None:
        status = res.status_code
        content_type = res.headers['Content-Type']
        if content_type != 'application/json':
            text = None
        else:
            text = json.loads(res.text)

        if status >= 400:
            out_status = errno.ENOENT
            if text is not None:
                detail = text['detail']
                out_message = f'{status} {detail}'
            else:
                out_message = f'{status} ({content_type})'
        else:
            result = text['response']['result']
            out_message = f'{status} {result}'

    return out_status, out_message

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
    out_status = 0
    if method == 'send' or method == 's':
        url = urljoin(api, base_messages)
        f = args.file[0] if args.file else None
        t = args.text[0] if args.text else None
        ttl = args.ttl[0] if args.ttl else None
        out_status, out_message = send(url, f, t, ttl)
    elif method == 'receive' or method == 'r':
        url = urljoin(api, base_messages + args.key[0])
        out_status, out_message = receive(url)
    elif method == 'delete' or method == 'd':
        url = urljoin(api, base_messages + args.key[0])
        out_status, out_message = delete(url)
    elif method == 'push':
        url = urljoin(api, base_files)
        url_keys = urljoin(api, base_messages)
        f = args.file[0]
        ttl = args.ttl[0] if args.ttl else None
        chunksize = args.chunksize[0] if args.chunksize else None
        out_status, out_message = push(url, url_keys, f, ttl, chunksize)
    elif method == 'pull':
        url_base = urljoin(api, base_files)
        url_keys = urljoin(api, base_messages + args.key[0])
        f = args.file[0]
        out_status, out_message = pull(url_base, url_keys, f)
    elif method == 'ping':
        url = urljoin(api, base_clipboard)
        out_status, out_message = ping(url, args.client)
    elif method == 'flush':
        url = urljoin(api, base_clipboard)
        out_status, out_message = flush(url)

    if out_status != 0:
        print(out_message, file=sys.stderr)
    else:
        print(out_message, end='')

    return out_status

if __name__ == '__main__':
    exit(main())
