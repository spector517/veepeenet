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
        * ) echo "ERROR: Unexpected component '$arg'"; exit 1;;
    esac
  done
fi

if [[ $INSTALL_XRAY -eq 1 ]]; then
  printf '\n >>> VeePeeNET XRAY\n'
  source ./install-xray.sh
fi

if [[ $INSTALL_WIREGUARD -eq 1 ]]; then
  printf '\n >>> VeePeeNET Wireguard\n'
  source ./install-wg.sh
fi
