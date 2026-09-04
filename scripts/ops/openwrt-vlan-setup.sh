#!/bin/sh
# OpenWrt VLAN setup template — WR11000 / F.R.I.D.A.Y-AI
#
# ATENCAO: Rever e editar antes de executar. Fazer backup primeiro.
# Executar no router via SSH: sh openwrt-vlan-setup.sh
#
# LuCI backup: System → Backup / Flash Operations → Generate archive

set -e

# --- EDITAR conforme hardware (correr "ip link" no router) ---
# Exemplos comuns: br-lan.30, eth0.30, switch0.30
IOT_DEVICE="${IOT_DEVICE:-br-lan.30}"
MGMT_DEVICE="${MGMT_DEVICE:-br-lan.99}"

HUB_MAC="d8:43:ae:90:b5:21"
HUB_IP="192.168.10.131"
HUB_HOSTNAME="friday-hub"

echo "=== FRIDAY VLAN Setup ==="
echo "Device IoT:  $IOT_DEVICE"
echo "Device Mgmt: $MGMT_DEVICE"
echo ""
echo "Pressione Ctrl+C para cancelar ou Enter para continuar..."
read dummy

# Reserva DHCP hub
echo ">>> Reserva DHCP para hub"
uci add dhcp host
uci set dhcp.@host[-1].name="$HUB_HOSTNAME"
uci set dhcp.@host[-1].mac="$HUB_MAC"
uci set dhcp.@host[-1].ip="$HUB_IP"
uci commit dhcp

# Interface IoT (VLAN 30)
echo ">>> Interface IoT (192.168.30.0/24)"
uci set network.iot=interface
uci set network.iot.proto='static'
uci set network.iot.ipaddr='192.168.30.1'
uci set network.iot.netmask='255.255.255.0'
uci set network.iot.device="$IOT_DEVICE"

uci set dhcp.iot=dhcp
uci set dhcp.iot.interface='iot'
uci set dhcp.iot.start='100'
uci set dhcp.iot.limit='100'
uci set dhcp.iot.leasetime='12h'

# Interface Mgmt (VLAN 99)
echo ">>> Interface Mgmt (192.168.99.0/24)"
uci set network.mgmt=interface
uci set network.mgmt.proto='static'
uci set network.mgmt.ipaddr='192.168.99.1'
uci set network.mgmt.netmask='255.255.255.0'
uci set network.mgmt.device="$MGMT_DEVICE"

# Firewall zone IoT
echo ">>> Firewall zone IoT"
uci add firewall zone
uci set firewall.@zone[-1].name='iot'
uci set firewall.@zone[-1].input='REJECT'
uci set firewall.@zone[-1].output='ACCEPT'
uci set firewall.@zone[-1].forward='REJECT'
uci add_list firewall.@zone[-1].network='iot'

# Firewall zone Mgmt
echo ">>> Firewall zone Mgmt"
uci add firewall zone
uci set firewall.@zone[-1].name='mgmt'
uci set firewall.@zone[-1].input='ACCEPT'
uci set firewall.@zone[-1].output='ACCEPT'
uci set firewall.@zone[-1].forward='REJECT'
uci add_list firewall.@zone[-1].network='mgmt'

# Allow lan -> iot forwarding
echo ">>> Forwarding lan -> iot"
uci add firewall forwarding
uci set firewall.@forwarding[-1].src='lan'
uci set firewall.@forwarding[-1].dest='iot'

# Block iot -> wan
echo ">>> Block iot -> wan"
uci add firewall rule
uci set firewall.@rule[-1].name='Block-IoT-Internet'
uci set firewall.@rule[-1].src='iot'
uci set firewall.@rule[-1].dest='wan'
uci set firewall.@rule[-1].target='REJECT'
uci set firewall.@rule[-1].proto='all'

# Block iot -> lan
echo ">>> Block iot -> lan"
uci add firewall rule
uci set firewall.@rule[-1].name='Block-IoT-Main'
uci set firewall.@rule[-1].src='iot'
uci set firewall.@rule[-1].dest='lan'
uci set firewall.@rule[-1].target='REJECT'
uci set firewall.@rule[-1].proto='all'

uci commit network
uci commit firewall

echo ">>> Aplicar alteracoes"
/etc/init.d/network restart
/etc/init.d/firewall restart
/etc/init.d/dnsmasq restart

echo ""
echo "=== Concluido ==="
echo "Validar:"
echo "  ping 192.168.30.1  (do PC hub)"
echo "  curl https://google.com  (do PC hub — deve funcionar)"
echo ""
echo "Guia completo: docs/arquitectura/rede-vlan-openwrt-wr11000.md"
