#!/bin/bash

set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: You must run this script as root" >&2
  exit 1
fi

REMOVE_XRAY=0
REMOVE_WIREGUARD=0

if [[ $# -eq 0 ]]; then
  REMOVE_XRAY=1
  REMOVE_WIREGUARD=1
else
  for arg in "$@"; do
    case $arg in
        xray ) REMOVE_XRAY=1;;
        wireguard ) REMOVE_WIREGUARD=1;;
        * ) echo "ERROR: Unexpected component '$arg'"; exit 1;;
    esac
  done
fi

if [[ $REMOVE_XRAY -eq 1 ]]; then
  printf '\n >>> REMOVING VeePeeNET XRAY\n'
  source ./uninstall-xray.sh
fi

if [[ $REMOVE_WIREGUARD -eq 1 ]]; then
  printf '\n >>> REMOVING VeePeeNET WireGuard\n'
  source ./uninstall-wg.sh
fi
