#!/bin/sh
set -eu

if [ -n "${XRAYCTL_PATH:-}" ] && [ -x "${XRAYCTL_PATH}" ]; then
    xrayctl_cmd="${XRAYCTL_PATH}"
else
    xrayctl_cmd=""
    for candidate in "$(command -v xrayctl 2>/dev/null || true)" /usr/local/bin/xrayctl /usr/bin/xrayctl; do
        if [ -n "${candidate}" ] && [ -x "${candidate}" ]; then
            xrayctl_cmd="${candidate}"
            break
        fi
    done
fi

if [ -z "${xrayctl_cmd}" ]; then
    echo 'xrayctl executable not found' >&2
    exit 1
fi

exec sudo -n "${xrayctl_cmd}" status --json