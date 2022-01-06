#!/usr/bin/env python3

import argparse
import errno
import io
import json
import os
import requests
import sys
import urllib.parse
from argparse import RawDescriptionHelpFormatter
from operator import attrgetter
from urllib.parse import urljoin

rclip_category_file_fragment_list = 'file-fragment-list'
rclip_status_file_fragment_list = 278

verbose = False

def send(url, message, ttl=None, control_message=False):
    out_status = 0
    out_message = None

    if message is None:
        try:
            message = sys.stdin.read()
        except Exception as e:
            exception_name = type(e).__name__
            detail = str(e)
            out_message = f'{exception_name} {detail}'
            return errno.EIO, out_message

    data = {
        'message': message
    }

    category = None
    if control_message is True:
        category = rclip_category_file_fragment_list
        data.update({
            'category': category
        })

    headers = {}
    if ttl is not None:
        headers.update({
            'X-ttl': ttl
        })

    res = None
    try:
        res = requests.post(url, json=data, headers=headers)
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

    if verbose:
        print(f'post url: {url}, ttl: {ttl}, category: {category}', file=sys.stderr)

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
            category = text['response']['category']
            if category == rclip_category_file_fragment_list:
                out_status = rclip_status_file_fragment_list

    if verbose:
        print(f'get url: {url}', file=sys.stderr)

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

    if verbose:
        print(f'del url: {url}', file=sys.stderr)

    return out_status, out_message

def send_file(url, url_keys, filename, ttl=None, chunk_size = None):
    out_status = 0
    part_messages = []

    keys = []

    if chunk_size:
        chunk_size = int(chunk_size)
    else:
        chunk_size = 1000000

    basename = os.path.basename(filename)
    keys.append(urllib.parse.quote(basename))

    try:
        file_size = os.path.getsize(filename)
        with open(filename, 'rb') as fd:
            read_size = 0
            file_number = 0
            while read_size < file_size:
                fd.seek(read_size)
                data = fd.read(chunk_size)
                sz = len(data)
                bd = io.BytesIO(data)

                files = {
                    'file': (f'{basename}.{file_number}', bd, 'application/octet-stream')
                }

                headers = {}
                if ttl is not None:
                    headers.update({
                        'X-ttl': ttl
                    })

                res = None
                try:
                    res = requests.post(url, files=files, headers=headers)
                except Exception as e:
                    out_status = errno.EIO
                    exception_name = type(e).__name__
                    detail = str(e)
                    part_messages.append(f'#{file_number} {exception_name} {detail}')
                    out_message = '\n'.join(part_messages)
                    return out_status, out_message

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

                    if verbose:
                        print(f'post url: {url}, file: {basename}.{file_number}, length: {sz}', file=sys.stderr)

                read_size = read_size + sz
                file_number = file_number + 1

    except Exception as e:
        out_status = errno.EIO
        exception_name = type(e).__name__
        detail = str(e)
        part_messages.append(f'* {exception_name} {detail}')
        out_message = '\n'.join(part_messages)
        return out_status, out_message

    key_status, key_message = send(url_keys, ':'.join(keys), ttl, control_message=True)
    if key_status == 0:
        out_message = key_message
    else:
        part_messages.append(f'* {key_status} {key_message}')
        out_message = '\n'.join(part_messages)
        out_status = key_status
    return out_status, out_message

def receive_file(url_base, filename, keys_string, force=False):
    out_status = 0
    out_message = None
    part_messages = []

    keys = keys_string.split(':')
    original_basename = urllib.parse.unquote(keys[0])
    keys = keys[1:]

    try:
        if filename is None:
            filename = original_basename

        mode = 'wb' if force is True else 'xb'
        with open(filename, mode) as fd:

            for key in keys:
                sz = 0
                res = None
                try:
                    url = url_base + key
                    res = requests.get(url)
                except Exception as e:
                    out_status = errno.EIO
                    exception_name = type(e).__name__
                    detail = str(e)
                    part_messages.append(f'{key} {exception_name} {detail}')
                    out_message = '\n'.join(part_messages)
                    return out_status, out_message

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
                            part_messages.append(f'{key} {status} {detail}')
                        else:
                            part_messages.append(f'{key} {status} ({content_type})')
                    else:
                        fd.write(res.content)
                        sz = len(res.content)

                if verbose:
                    print(f'get url: {url}, length: {sz}', file=sys.stderr)

    except Exception as e:
        out_status = errno.EIO
        exception_name = type(e).__name__
        detail = str(e)
        part_messages.append(f'* {exception_name} {detail}')
        out_message = '\n'.join(part_messages)
        return out_status, out_message

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

    if verbose:
        print(f'get url: {url}', file=sys.stderr)

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

    if verbose:
        print(f'del url: {url}', file=sys.stderr)

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
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    subparsers = parser.add_subparsers(dest='subparser_name', title='methods')
    subparser_ping = subparsers.add_parser('ping', help='ping clipboard')
    subparser_ping.add_argument('-c', '--client', action='store_true', help='show client information')
    subparser_flush = subparsers.add_parser('flush', help='flush clipboard')
    subparser_send = subparsers.add_parser('send', aliases=['s'], help='send message')
    subparser_send.add_argument('-T', '--ttl', nargs=1, help='time to live')
    subparser_send_group = subparser_send.add_mutually_exclusive_group()
    subparser_send_group.add_argument('-f', '--file', nargs=1, help='message file')
    subparser_send_group.add_argument('-t', '--text', nargs=1, help='message text')
    subparser_receive = subparsers.add_parser('receive', aliases=['r'], help='receive message')
    subparser_receive.add_argument('key', nargs=1, help='message key')
    subparser_receive.add_argument('-o', '--output', nargs=1, help='output file')
    subparser_receive.add_argument('-F', '--force', action='store_true', help='force to overwrite existing file')
    subparser_delete = subparsers.add_parser('delete', aliases=['d'], help='delete message')
    subparser_delete.add_argument('key', nargs=1, help='message key')

    if len(sys.argv) == 1:
        print(parser.format_usage(), file=sys.stderr)
        return 0

    args = parser.parse_args()

    if args.api:
        api = args.api[0]

    global verbose
    verbose = args.verbose

    base_messages = 'api/v1/messages'
    base_files = 'api/v1/files'
    base_clipboard = 'api/v1/clipboard'
    method = args.subparser_name
    out_status = 0
    if method == 'send' or method == 's':
        f = args.file[0] if args.file else None
        t = args.text[0] if args.text else None
        ttl = args.ttl[0] if args.ttl else None
        if f:
            file_url = urljoin(api, base_files)
            keys_url = urljoin(api, base_messages)
            out_status, out_message = send_file(file_url, keys_url, f, ttl)
        else:
            url = urljoin(api, base_messages)
            out_status, out_message = send(url, t, ttl)
    elif method == 'receive' or method == 'r':
        o = args.output[0] if args.output else None
        keys_url = urljoin(api, base_messages + '/' + args.key[0])
        out_status, out_message = receive(keys_url)
        if out_status == rclip_status_file_fragment_list:
            base_url = urljoin(api, base_files)
            out_status, out_message = receive_file(base_url, o, out_message, force=args.force)
    elif method == 'delete' or method == 'd':
        url = urljoin(api, base_messages + '/' + args.key[0])
        out_status, out_message = delete(url)
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
