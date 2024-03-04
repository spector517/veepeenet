import sys
import os
import subprocess
import json
import shutil

ROUTE_FILE_PATH = '/proc/net/route'
UFW_BEFORE_RULES_PATH = '/etc/ufw/before.rules'
SYSCTL_FILE_PATH = '/etc/sysctl.conf'
FORWARD_POLICY_FILE = '/etc/default/ufw'
SSHD_CONFIG_PATH = '/etc/ssh/sshd_config'
ENCODING = 'UTF-8'
RUN_COMMAND_TIMEOUT = 20_000

DEFAULT_SSH_PORT = 22
DEFAULT_NO_UFW = False
DEFAULT_CLIENTS = []
DEFAULT_DNS = ['1.1.1.1', '1.0.0.1']

CHECK_MODE = False
DEFAULT_CLIENTS_DIR = os.path.expanduser('~/.veepeenet/clients')
RESULT_LOG_PATH = os.path.expanduser('~/.veepeenet/result.json')
CONFIG_PATH = os.path.expanduser('~/.veepeenet/config.json')
RESULT = {
    'has_error': False,
    'meta': {
        'interpreter': sys.executable,
        'interpreter_version':
            f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
        'run_args': sys.argv
    },
    'actions': []
}


def handle_result(func: callable) -> callable:
    def wrapper(*args, **kwargs) -> any:
        action = {}
        try:
            res = func(*args, **kwargs)
            action.update({'result': str(res)})
        except Exception as ex:
            RESULT['has_error'] = True
            action.update({'error': str(ex)})
            write_text_file(RESULT_LOG_PATH, json.dumps(RESULT, indent=2))
            raise ex
        finally:
            action.update({
                'name': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            })
            RESULT['actions'].append(action)
        return res

    return wrapper


def write_text_file(file_path: str, text: str, mode: int = 0) -> None:
    if CHECK_MODE:
        print(f'{file_path}:\n{text}\n')
        return

    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    else:
        if mode:
            os.chmod(file_path, mode)
        with open(file_path, 'rt', encoding=ENCODING) as fd:
            if fd.read() == text:
                return

    with open(file_path, 'wt', encoding=ENCODING) as fd:
        fd.write(text)


@handle_result
def run_command(command: str, stdin: str = '') -> tuple:
    if CHECK_MODE:
        command = f'echo "{command}"'
    try:
        run_result = subprocess.run(
            command,
            input=stdin.encode(ENCODING),
            capture_output=True,
            check=True,
            timeout=RUN_COMMAND_TIMEOUT,
            shell=True
        )

        return (run_result.returncode,
                run_result.stdout.decode(ENCODING).strip(),
                run_result.stderr.decode(ENCODING).strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as ex:
        raise ex


@handle_result
def clean_configuration(config_path: str, clients_dir: str) -> None:
    if os.path.exists(config_path):
        os.remove(config_path)
    if os.path.exists(clients_dir):
        shutil.rmtree(clients_dir)
