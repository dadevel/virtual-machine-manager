# Virtual Machine Manager

![Windows 11 with Secure Boot and TPM](./assets/windows-11.png)

`vmm` is a Python script that utilizes Systemd to manage your Qemu VMs.
It was inspired by [quickemu](https://github.com/quickemu-project/quickemu) but is tailored to my personal use case.

## Setup

System dependencies:

- cdrtools for `mkisofs`
- iproute2
- qemu-desktop for `qemu-system-x86_64`
- qemu-img
- systemd

Installation:

a) With [pipx](https://github.com/pypa/pipx).

~~~ bash
pipx install git+https://github.com/dadevel/virtual-machine-manager.git@main
~~~

b) With `pip`.

~~~ bash
pip install --user git+https://github.com/dadevel/virtual-machine-manager.git@main
~~~

c) As standalone script.

~~~ bash
curl -o ~/.local/bin/vmm https://raw.githubusercontent.com/dadevel/vmm/main/vmm/main.py
chmod +x ~/.local/bin/vmm
~~~

In all cases don't forget to copy the [profiles](./profiles/) you need into `~/.config/vmm/profiles/`.

## Networking

`vmm` is intended to be used with [Qemu Bridge Networking](https://www.linux-kvm.org/page/Networking#Private_Virtual_Bridge).
This can be quickly setup with `systemd-networkd` and `systemd-resolved`.
Configuration files for a dual stack setup with DHCP and DNS can be found [here](./extras/networking/).

## Usage

Create a new VM based on the [windows-11 profile](./profiles/windows-11/).

~~~ bash
vmm create windows-11 win11-test
~~~

Boot the VM.

~~~ bash
vmm start win11-test
~~~
