#!/bin/bash

set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: You must run this script as root" >&2
  exit 1
fi

INSTALL_XRAY=0
INSTALL_WIREGUARD=0

if [[ $# -eq 0 ]]; then
  INSTALL_XRAY=1
  INSTALL_WIREGUARD=1
else
  for arg in "$@"; do
    case $arg in
        xray ) INSTALL_XRAY=1;;
        wireguard ) INSTALL_WIREGUARD=1;;
        * ) echo "ERROR: Unexpected component '$arg'" >&2; exit 1;;
    esac
  done
fi

if [[ $INSTALL_WIREGUARD -eq 1 ]] || [[ $INSTALL_XRAY -eq 1 ]]; then
  mkdir -p /usr/local/etc/veepeenet
  cp ./meta.json /usr/local/etc/veepeenet/meta.json
fi

if [[ $INSTALL_XRAY -eq 1 ]]; then
  printf '\n >>> INSTALLING VeePeeNET Xray\n'
  source ./install-xray.sh
fi

if [[ $INSTALL_WIREGUARD -eq 1 ]]; then
  printf '\n >>> INSTALLING VeePeeNET WireGuard\n'
  source ./install-wg.sh
fi
