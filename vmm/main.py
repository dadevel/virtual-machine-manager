#!/usr/bin/env python3
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any
import hashlib
import json
import logging
import os
import secrets
import shutil
import subprocess
import sys
import urllib.request

NAME = 'vmm'
XDG_RUNTIME_DIR = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
XDG_CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))
VMM_RUNTIME_DIR = Path(os.environ.get('VMM_RUNTIME_DIR', XDG_RUNTIME_DIR/NAME))
VMM_STORAGE_DIR = Path(os.environ.get('VMM_STORAGE_DIR', Path.home()/'machines'))
VMM_IMAGE_DIR = Path(os.environ.get('VMM_IMAGE_DIR', Path.home()/'images'))
VMM_PROFILE_DIR = Path(os.environ.get('VMM_PROFILE_DIR', XDG_CONFIG_HOME/'vmm/profiles'))
VMM_MAC_PREFIX = os.environ.get('VMM_MAC_PREFIX', '52:54:00')
VMM_INTERFACE_PREFIX = os.environ.get('VMM_INTERFACE_PREFIX', 'tap-vmm-')
VMM_INTERFACE_MAX_LENGTH = 16
VMM_BRIDGE_INTERFACE = os.environ.get('VMM_BRIDGE_INTERFACE', 'br0')
VMM_EFI_CODE = Path(os.environ.get('VMM_EFI_CODE', '/usr/share/edk2-ovmf/x64/OVMF_CODE.fd'))
VMM_EFI_CODE_SECBOOT = Path(os.environ.get('VMM_EFI_CODE_SECBOOT', '/usr/share/edk2-ovmf/x64/OVMF_CODE.secboot.fd'))
VMM_EFI_VARS = Path(os.environ.get('VMM_EFI_VARS', '/usr/share/edk2-ovmf/x64/OVMF_VARS.fd'))


def main():
    entrypoint = ArgumentParser()
    parsers = entrypoint.add_subparsers(dest='command', required=True)

    parser = parsers.add_parser('list')

    parser = parsers.add_parser('create')
    parser.add_argument('profile', nargs=1)
    parser.add_argument('machine', nargs=1)

    parser = parsers.add_parser('start')
    parser.add_argument('machine', nargs=1)

    parser = parsers.add_parser('stop')
    parser.add_argument('machine', nargs=1)

    parser = parsers.add_parser('connect')
    parser.add_argument('machine', nargs=1)

    args = entrypoint.parse_args()
    if getattr(args, 'machine', None):
        args.machine = args.machine[0]
    if getattr(args, 'profile', None):
        args.profile = args.profile[0]

    logging.basicConfig(stream=sys.stderr, level='INFO')

    try:
        command = f'command_{args.command}'
        fn = globals()[command]
        fn(args)
    except Exception as e:
        logging.exception(e)
        exit(1)


def command_list(_: Namespace) -> None:
    for path in VMM_STORAGE_DIR.glob('*/machine.json'):
        name = path.parent.name
        print(name, _run('systemctl', '--user', 'is-active', f'{NAME}-{name}-qemu.service', capture=True, check=False).strip())


def command_create(args: Namespace) -> None:
    logging.info('creating machine')
    options = _get_setup_profile(args.profile, args.machine)
    Path(options.machine_storage_dir).mkdir(exist_ok=True)
    setup_path = _gather_files(options)
    _setup_firmware_file(options)
    _setup_disk_file(options)
    options = _generate_mac(options)
    _writing_machine_config(options)
    if options.machine_os == 'windows':
        if Path(VMM_PROFILE_DIR/options.machine_guest_type/'unattended').is_dir():
            _build_unattended_iso(options)
            options.machine_cdroms = [setup_path, VMM_IMAGE_DIR/options.virtio_driver_filename, VMM_STORAGE_DIR/options.machine_name/'unattended.iso']
        else:
            options.machine_cdroms = [setup_path, VMM_IMAGE_DIR/options.virtio_driver_filename]
    else:
        options.machine_cdroms = [setup_path]
    input('press enter to boot')
    logging.info('booting machine')
    _setup_network(options)
    _start_qemu(options)
    # TODO: if first boot and windows use qemu send-key to send enter/return
    _start_swtmp(options)
    _start_spicy(options)


def command_start(args: Namespace) -> None:
    logging.info('booting machine')
    options = _get_startup_profile(args.machine)
    _setup_network(options)
    _start_qemu(options)
    _start_swtmp(options)
    _start_spicy(options)


def _setup_network(options: Namespace) -> None:
    if not _test('ip', 'link', 'show', options.machine_network_interface):
        logging.info('bringing up network')
        _run('sudo', 'ip', 'tuntap', 'add', 'mode', 'tap', options.machine_network_interface)
        _run('sudo', 'ip', 'link', 'set', 'dev', options.machine_network_interface, 'master', options.machine_bridge_interface)
        _run('sudo', 'ip', 'link', 'set', options.machine_network_interface, 'up')
    # TODO: delete tap interface on exit


def _generate_interface_name(name: str) -> str:
    hash = hashlib.md5()
    hash.update(name.encode())
    result = hash.hexdigest()
    return VMM_INTERFACE_PREFIX + result[:VMM_INTERFACE_MAX_LENGTH - len(VMM_INTERFACE_PREFIX) - 1]


def _start_qemu(options: Namespace) -> None:
    logging.info('starting qemu')

    qemu_args = _format_qemu_command(options.machine_qemu_command, options.__dict__)

    cdrom_args = []
    for item in options.machine_cdroms:
        cdrom_args.extend(('-drive', f'media=cdrom,file={item}'))

    if options.machine_tpm:
        tpm_args = [
            '-chardev', f'socket,id=chrtpm,path={options.machine_tpm_socket}',
            '-tpmdev', 'emulator,id=tpm0,chardev=chrtpm',
            '-device', 'tpm-tis,tpmdev=tpm0',
        ]
    else:
        tpm_args = []

    _systemd_run(
        '--user', '--quiet', '--collect',
        '--unit', f'{NAME}-{options.machine_name}-qemu.service',
        '--property', f'RuntimeDirectory={NAME}/{options.machine_name}',
        '--', *qemu_args, *cdrom_args, *tpm_args,
    )


def _format_qemu_command(command: list[str], variables: dict[str, Any]) -> list[str]:
    return [word.format(**variables, xdg_runtime_dir=XDG_RUNTIME_DIR) for word in command]


def _start_swtmp(options: Namespace) -> None:
    if not options.machine_tpm:
        return
    options.machine_tpm_dir.mkdir(exist_ok=True)
    logging.info('starting swtpm')
    _systemd_run(
        '--user', '--quiet', '--collect',
        '--unit', f'{NAME}-{options.machine_name}-swtpm.service',
        '--property', f'BindsTo={NAME}-{options.machine_name}-qemu.service',
        '--', 'swtpm', 'socket', '--tpmstate', f'dir={options.machine_tpm_dir}', '--ctrl', f'type=unixio,path={options.machine_tpm_socket}', '--tpm2',
    )


def _start_spicy(options: Namespace) -> None:
    if options.machine_display_mode != 'spice':
        return
    logging.info('starting spicy')
    _systemd_run(
        '--user', '--quiet', '--collect',
        '--unit', f'{NAME}-{options.machine_name}-spicy.service',
        '--property', f'BindsTo={NAME}-{options.machine_name}-qemu.service',
        '--', 'spicy', '--uri', f'spice+unix://{options.machine_spice_socket}',
    )


def command_stop(args: Namespace) -> None:
    _run('systemctl', '--user', 'stop', f'{NAME}-{args.machine}-qemu.service')


def command_connect(args: Namespace) -> None:
    _run('nc', '-U', VMM_RUNTIME_DIR/args.machine/'monitor.sock')


def _get_setup_profile(profile: str, machine: str, **kwargs: Any) -> Namespace:
    options = _get_default_profile(machine)
    with open(VMM_PROFILE_DIR/profile/'profile.json', 'r') as file:
        options.__dict__.update(json.load(file))
    options.__dict__.update(kwargs, machine_guest_type=profile)
    return options


def _get_startup_profile(machine: str, **kwargs: Any) -> Namespace:
    options = _get_default_profile(machine)
    with open(VMM_STORAGE_DIR/machine/'machine.json', 'r') as file:
        options.__dict__.update(json.load(file))
    with open(VMM_PROFILE_DIR/options.machine_guest_type/'profile.json', 'r') as file:
        options.__dict__.update(json.load(file))
    options.__dict__.update(kwargs)
    return options


def _get_default_profile(machine: str) -> Namespace:
    return Namespace(
        machine_name=machine,
        machine_runtime_dir=VMM_RUNTIME_DIR/machine,
        machine_storage_dir=VMM_STORAGE_DIR/machine,
        machine_build_dir=VMM_STORAGE_DIR/machine/'build',
        machine_mac_file=VMM_STORAGE_DIR/machine/'mac.txt',
        machine_efi_code=VMM_STORAGE_DIR/machine/'efi-code.bin',
        machine_efi_vars=VMM_STORAGE_DIR/machine/'efi-vars.bin',
        machine_tpm_dir=VMM_STORAGE_DIR/machine/'tpm',
        machine_disk_prefix=VMM_STORAGE_DIR/machine/'disk',
        machine_monitor_socket=VMM_RUNTIME_DIR/machine/'monitor.sock',
        machine_spice_socket=VMM_RUNTIME_DIR/machine/'spice.sock',
        machine_tpm_socket=VMM_RUNTIME_DIR/machine/'swtpm.sock',
        machine_architecture='x86_64',
        machine_guest_type='',
        machine_boot_mode='bios',
        machine_secureboot=False,
        machine_tpm=False,
        machine_disk_size='16g',
        machine_disk_format='qcow2',
        machine_cdroms=[],
        machine_bridge_interface=VMM_BRIDGE_INTERFACE,
        machine_network_interface=_generate_interface_name(machine),
        machine_mac='',  # set later
        machine_cpu_cores=2,
        machine_cpu_threads=2,  # threads per core, 1 disables smt aka hyper threading',
        machine_ram_size='8g',
        machine_display_mode='none',
        machine_qemu_command=[],  # set in profile
        machine_iso_url='',
        machine_iso_filename='',
        virtio_driver_url='https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso',
        virtio_driver_filename='virtio-win.iso',
        virtio_driver_version='',
        spice_guest_tools_url='https://www.spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe',
        spice_guest_tools_filename='spice-guest-tools.exe',
        unattended_license_key='W269N-WFGWX-YVC9B-4J6C9-T83GX',  # generic windows 10 and 11 pro key from https://docs.microsoft.com/en-us/windows-server/get-started/kmsclientkeys#windows-10-all-supported-semi-annual-channel-versions
        unattended_user_name='Nobody',
        unattended_user_password='passw0rd',
        unattended_language='en-US',
        unattended_region='de-DE',
        unattended_keyboard_layout='0407:00000407',  # de-DE
        unattended_timezone='W. Europe Standard Time',  # or UTC
    )


def _gather_files(options: Namespace) -> Path:
    logging.info('gathering files')
    if options.machine_iso_filename:
        setup_path = VMM_IMAGE_DIR/options.machine_iso_filename
        if not setup_path.exists():
            logging.critical(f'please download setup ISO from {options.machine_iso_url} to {setup_path}')
            exit(1)
    else:
        while True:
            setup_path = Path(input('enter iso file path: ')).absolute()
            if setup_path.is_file():
                break
            logging.error('invalid path given')
    if options.machine_os == 'windows':
        _download_file(options.virtio_driver_url, VMM_IMAGE_DIR/options.virtio_driver_filename)
        _download_file(options.spice_guest_tools_url, VMM_IMAGE_DIR/options.spice_guest_tools_filename)
    return setup_path


def _setup_firmware_file(options: Namespace) -> None:
    if options.machine_boot_mode != 'efi':
        return
    logging.info('creating efi code')
    shutil.copy2(VMM_EFI_CODE_SECBOOT if options.machine_secureboot else VMM_EFI_CODE, options.machine_efi_code)
    if not Path(options.machine_efi_vars).exists():
        logging.info('creating efi vars')
        shutil.copy2(VMM_EFI_VARS, options.machine_efi_vars)


def _setup_disk_file(options: Namespace) -> None:
    path = Path(options.machine_storage_dir)/f'{options.machine_disk_prefix}.{options.machine_disk_format}'
    if not path.exists():
        logging.info('creating virtual disk')
        _run('qemu-img', 'create', '-f', options.machine_disk_format, '--', path, options.machine_disk_size)


def _generate_mac(options: Namespace) -> Namespace:
    if not options.machine_mac:
        logging.info('generating mac address')
        # from https://superuser.com/a/218650
        options.machine_mac = f'{VMM_MAC_PREFIX}:{_random_hex_double_digit()}:{_random_hex_double_digit()}:{_random_hex_double_digit()}'
    return options


def _build_unattended_iso(options: Namespace) -> None:
    logging.info('building unattended iso')
    machine_build_dir = Path(options.machine_build_dir)
    if machine_build_dir.exists():
        shutil.rmtree(machine_build_dir)
    shutil.copytree(VMM_PROFILE_DIR/options.machine_guest_type/'unattended', machine_build_dir)
    shutil.copy2(VMM_IMAGE_DIR/options.spice_guest_tools_filename, machine_build_dir/options.spice_guest_tools_filename)

    # TODO: windows setup: language, keyboard layout
    # TODO: oob setup: language, keyboard layout
    text = Path(VMM_PROFILE_DIR/options.machine_guest_type/'unattended/autounattend.xml').read_text().format(**options.__dict__, xdg_runtime_dir=XDG_RUNTIME_DIR)
    Path(machine_build_dir/'autounattend.xml').write_text(text)

    _run('mkisofs', '-quiet', '-l', '-o', VMM_STORAGE_DIR/options.machine_name/'unattended.iso', machine_build_dir)
    shutil.rmtree(machine_build_dir)


def _writing_machine_config(options: Namespace) -> None:
    logging.info('writing machine config')
    path = options.machine_storage_dir/'machine.json'
    defaults = _get_setup_profile(options.machine_guest_type, options.machine_name)
    changes = {key: value for key, value in options.__dict__.items() if value != getattr(defaults, key) or key == 'machine_guest_type'}
    with open(path, 'w') as file:
        json.dump(changes, file, indent=2, sort_keys=False)


def _random_hex_double_digit() -> str:
    return f'{secrets.randbelow(256):2x}'


def _download_file(url: str, dest: Path) -> None:
    if dest.exists():
        return
    logging.info(f'downloading {url}')
    with urllib.request.urlopen(url) as response:
        body = response.read()
    dest.write_bytes(body)


def _systemd_run(*args: int|str|Path) -> None:
    logging.info(f'systemd-run {" ".join(str(arg) for arg in args)}')
    _run('systemd-run', *args)


def _test(*args: int|str|Path) -> bool:
    try:
        _run(*args, check=True, capture=True)
        return True
    except ProcessError:
        return False


def _run(*args: int|str|Path, check=True, capture=False) -> str:
    pipe = subprocess.PIPE if capture else None
    process = subprocess.Popen([str(arg) for arg in args], stdout=pipe, stderr=pipe, text=True)
    stdout, stderr = process.communicate()
    rc = process.wait()
    if check and rc != 0:
        raise ProcessError(args, stderr)
    if capture:
        return stdout
    return ''


class ProcessError(Exception):
    def __init__(self, command: tuple[int|str|Path], error: str) -> None:
        super().__init__(f'command {" ".join(str(word) for word in command)} failed: {error}')


if __name__ == '__main__':
    main()
