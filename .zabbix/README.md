# VeePeeNET Zabbix Integration

Files in this directory:

- template_veepeenet_zabbix7.yaml: import into Zabbix 7.0 LTS
- zabbix_agent2_veepeenet.conf: drop-in for zabbix-agent2
- veepeenet_status.sh: helper script for the UserParameter

Recommended deployment on the monitored host:

1. Copy veepeenet_status.sh to /etc/zabbix/scripts/veepeenet_status.sh
2. Run chmod 0755 /etc/zabbix/scripts/veepeenet_status.sh
3. Copy zabbix_agent2_veepeenet.conf to /etc/zabbix/zabbix_agent2.d/veepeenet.conf
4. Add a sudoers rule for the zabbix user:

   zabbix ALL=(root) NOPASSWD: /usr/local/bin/xrayctl status --json

5. Restart zabbix-agent2
6. Import template_veepeenet_zabbix7.yaml into Zabbix and link the template to the host

The template stores the full xrayctl status payload in the raw item veepeenet.status.raw.
This means you can add more dependent items in Zabbix later and extract any extra field from the same JSON.
By default, the raw item is configured as an active agent item with a 5 minute interval.