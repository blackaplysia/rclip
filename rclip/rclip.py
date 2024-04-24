#!/usr/bin/env python3

import argparse
import chardet
import errno
import io
import json
import os
import requests
import subprocess
import sys
import time
import urllib.parse
from argparse import RawDescriptionHelpFormatter
from operator import attrgetter
from urllib.parse import urljoin
from subprocess import PIPE

rclip_category_file_fragment_list = 'file-fragment-list'
rclip_status_file_fragment_list = 278

verbose = False

def read_from_stdin(pipe_input=None, pipe_encoding=None):
    if pipe_input is None:
        try:
            message = sys.stdin.read()
        except Exception as e:
            exception_name = type(e).__name__
            detail = str(e)
            out_message = f'{exception_name} {detail}'
            return None, errno.EIO, out_message
    else:
        proc = subprocess.Popen(pipe_input, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        if proc.returncode > 0:
            coding_err = chardet.detect(err)['encoding']
            if coding_err == None:
                coding_err = 'utf-8'
            return None, proc.returncode, err.decode(coding_err)
        if pipe_encoding:
            coding = pipe_encoding
        else:
            coding = chardet.detect(out)['encoding']
            if coding == None:
                coding = 'utf-8'
        message = out.decode(coding)

    return message, 0, None

def write_to_stdout(message, method, pipe_output=None, pipe_encoding=None, no_r_stdout=False, no_s_pipe=False):
    if message is not None:

        if method != 'receive' or no_r_stdout != True:
            print(message, end='')

        if method != 'send' or no_s_pipe != True:
            if pipe_output is not None:
                fifo_name = f'named_pipe.{os.path.basename(sys.argv[0])}.{os.getpid()}.{time.time()}'
                os.mkfifo(fifo_name, mode=0o777)

                fifo_in = os.open(fifo_name, os.O_RDONLY | os.O_NONBLOCK)
                proc = subprocess.Popen(pipe_output, shell=True, stdin=fifo_in, stdout=PIPE, stderr=PIPE, text=True)
                os.close(fifo_in)

                if pipe_encoding:
                    coding = pipe_encoding
                else:
                    coding = 'utf-8'

                fifo_out = os.open(fifo_name, os.O_WRONLY)
                os.write(fifo_out, bytes(message, coding))
                os.close(fifo_out)

                out, err = proc.communicate()
                if proc.returncode > 0:
                    if verbose:
                        coding_err = chardet.detect(err)['encoding']
                        if coding_err == None:
                            coding_err = 'utf-8'
                        print(f'pipe: {err.decode(coding_err)}', file=sys.stderr)

                os.unlink(fifo_name)

def send(url, message, ttl=None, control_message=False):
    out_status = 0
    out_message = None

    if message is None:
        out_message = 'No message'
        return errno.ENOENT, out_message

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
            if res.encoding is None:
                res.encoding = 'utf-8'
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
                    out_status = errno.ENOENT
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
                    url = url_base + '/' + key
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

    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    class SortingHelpFormatter(RawDescriptionHelpFormatter):
        def add_arguments(self, actions):
            actions = sorted(actions, key=attrgetter('option_strings'))
            super(SortingHelpFormatter, self).add_arguments(actions)

    api = os.environ.get('RCLIP_API', 'http://localhost/')

    parser = argparse.ArgumentParser(description='Remote clip', formatter_class=SortingHelpFormatter,
                                     epilog=f'''Current message api url: {api}
You can modify this value with -a or $RCLIP_API.''')
    parser.add_argument('--api', nargs=1, help='message api url')
    parser.add_argument('--input-from', nargs=1, metavar='COMMAND', help='pipe input from command')
    parser.add_argument('--input-encoding', nargs=1, metavar='CODING', help='encoding of pipe input')
    parser.add_argument('--output-to', nargs=1, metavar='COMMAND', help='pipe output to command')
    parser.add_argument('--output-encoding', nargs=1, metavar='CODING', help='encoding of pipe input')
    parser.add_argument('--no-receive-stdout', action='store_true', help='no standard output when to receive message')
    parser.add_argument('--no-send-pipe', action='store_true', help='no pipe output when to send message')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    parser.add_argument('-T', '--ttl', nargs=1, help='time to live')
    parser.add_argument('-F', '--force', action='store_true', help='force to overwrite existing file')
    parser.add_argument('-d', '--delete', action='store_true', help='delete message')
    parser.add_argument('-o', '--output', nargs=1, help='output file')
    subparser_group = parser.add_mutually_exclusive_group()
    subparser_group.add_argument('--ping', action='store_true', help='ping clipboard')
    subparser_group.add_argument('--flush', action='store_true', help='flush clipboard')
    subparser_group.add_argument('-f', '--file', nargs=1, help='message file')
    subparser_group.add_argument('-t', '--text', nargs=1, help='message text')
    subparser_group.add_argument('key', nargs='?', help='message key')

    args = parser.parse_args()

    if args.api:
        api = args.api[0]

    global verbose
    verbose = args.verbose

    base_messages = 'api/v1/messages'
    base_files = 'api/v1/files'
    base_clipboard = 'api/v1/clipboard'

    method = None
    out_statuses = []
    out_messages = []
    if args.ping is True:
        url = urljoin(api, base_clipboard)
        out_status, out_message = ping(url, True)
        out_statuses.append(out_status)
        out_messages.append(out_message)
    elif args.flush is True:
        url = urljoin(api, base_clipboard)
        out_status, out_message = flush(url)
        out_statuses.append(out_status)
        out_messages.append(out_message)
    elif args.delete is True:
        url = urljoin(api, base_messages + '/' + args.key)
        out_status, out_message = delete(url)
        out_statuses.append(out_status)
        out_messages.append(out_message)
    elif args.key is None:
        method='send'

        f = args.file[0] if args.file else None
        t = args.text[0] if args.text else None
        ttl = args.ttl[0] if args.ttl else None
        if f:
            file_url = urljoin(api, base_files)
            keys_url = urljoin(api, base_messages)
            out_status, out_message = send_file(file_url, keys_url, f, ttl)
            out_statuses.append(out_status)
            out_messages.append(out_message)
        else:
            if t is None:
                pipe = args.input_from[0] if args.input_from else None
                pipe_encoding = args.input_encoding[0] if args.input_encoding else None
                t, out_status, out_message = read_from_stdin(pipe, pipe_encoding)
                if t is None:
                    out_statuses.append(out_status)
                    out_messages.append(out_message)
            if t is not None:
                url = urljoin(api, base_messages)
                out_status, out_message = send(url, t, ttl)
                out_statuses.append(out_status)
                out_messages.append(out_message)
    else:
        method='receive'

        o = args.output[0] if args.output else None
        keys_url = urljoin(api, base_messages + '/' + args.key)
        out_status, out_message = receive(keys_url)
        if out_status == rclip_status_file_fragment_list:
            base_url = urljoin(api, base_files)
            out_status, out_message = receive_file(base_url, o, out_message, force=args.force)
        out_statuses.append(out_status)
        out_messages.append(out_message)

    exit_status = 0
    for s, m in zip(out_statuses, out_messages):
        if s != 0:
            print(m, file=sys.stderr)
            if exit_status == 0:
                exit_status = s
        else:
            pipe = args.output_to[0] if args.output_to else None
            pipe_encoding = args.output_encoding[0] if args.output_encoding else None
            write_to_stdout(m, method, pipe, pipe_encoding, no_r_stdout=args.no_receive_stdout, no_s_pipe=args.no_send_pipe)

    return exit_status

if __name__ == '__main__':
    exit(main())
