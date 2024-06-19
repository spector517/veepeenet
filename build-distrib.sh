#!/bin/bash

set -e

DISTRIB_VERSION=$1
XRAY_VERSION=$2
DISTRIB_PATH="veepeenet-$DISTRIB_VERSION"
DISTRIB_ARCHIVE_NAME="veepeenet.tar.gz"

echo "DISTRIB_VERSION: $DISTRIB_VERSION"
echo "XRAY VERSION: $XRAY_VERSION"
rm -rf "$DISTRIB_PATH"
mkdir "$DISTRIB_PATH"

curl -L "https://github.com/XTLS/Xray-core/releases/download/$XRAY_VERSION/Xray-linux-64.zip" \
  -o "$DISTRIB_PATH"/Xray-linux-64.zip

cp install.sh "$DISTRIB_PATH"
cp install-wg.sh "$DISTRIB_PATH"
cp install-xray.sh "$DISTRIB_PATH"
chmod 755 "$DISTRIB_PATH"/*.sh

cp ./*.py "$DISTRIB_PATH"
cp ./xray.service "$DISTRIB_PATH"

unzip "$DISTRIB_PATH"/Xray-linux-64.zip -d "$DISTRIB_PATH"/Xray-linux-64
rm -f $DISTRIB_ARCHIVE_NAME
tar -czvf $DISTRIB_ARCHIVE_NAME "$DISTRIB_PATH"
rm -r "$DISTRIB_PATH"
