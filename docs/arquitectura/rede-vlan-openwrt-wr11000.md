# VLANs no WR11000 (OpenWrt/LuCI)

Guia especifico para o router detectado em `192.168.10.1` (OpenWrt + LuCI, modelo **WR11000**).

## Estado actual da tua rede

| Item | Valor |
|---|---|
| Gateway / router | `192.168.10.1` |
| PC hub (FRIDAY) | `192.168.10.131` |
| Subnet actual | `192.168.10.0/24` |
| DNS suffix | `lan` |

A rede **Main (VLAN 10)** ja corresponde ao teu LAN actual. Vais **adicionar** VLAN 30 (IoT) e VLAN 99 (Mgmt) sem alterar o IP do PC.

---

## IMPORTANTE — antes de comecar

1. **Faz backup** da configuracao: LuCI → System → Backup / Flash Operations → Generate archive
2. Garante acesso **fisico** ao router (cabo Ethernet) — se algo correr mal, podes reset
3. Aplica num momento em que podes reiniciar a rede se necessario
4. **Nao tenho acesso ao teu router** — segues tu estes passos no browser ou SSH

---

## Opcao A — LuCI (interface web)

Abre: [http://192.168.10.1](http://192.168.10.1) → login

### A1. Criar interface IoT (VLAN 30)

1. **Network → Interfaces → Add new interface**
2. Name: `iot`
3. Protocol: `Static address`
4. IPv4 address: `192.168.30.1`
5. IPv4 netmask: `255.255.255.0`
6. Interface: selecciona ou cria device VLAN (ex.: `br-lan.30` ou eth0.30 — depende do hardware)
7. DHCP Server: activar (range `192.168.30.100` – `192.168.30.200`)
8. Save & Apply

### A2. Criar interface Mgmt (VLAN 99)

1. **Network → Interfaces → Add new interface**
2. Name: `mgmt`
3. Protocol: `Static address`
4. IPv4 address: `192.168.99.1`
5. IPv4 netmask: `255.255.255.0`
6. Interface: device VLAN (ex.: `br-lan.99`)
7. DHCP: opcional (so dispositivos admin)
8. Save & Apply

### A3. Reserva DHCP para PC hub

1. **Network → DHCP and DNS → Static Leases**
2. MAC: `D8-43-AE-90-B5-21` (Ethernet Intel I225-V do teu PC)
3. IPv4: `192.168.10.131`
4. Hostname: `friday-hub`
5. Save & Apply

### A4. Firewall — zonas

1. **Network → Firewall → Zones**
2. Criar zona `iot`:
   - Input: Reject
   - Output: Accept
   - Forward: Reject
   - Covered networks: `iot`
   - **Desmarcar** "Allow forward to wan"
3. Criar zona `mgmt`:
   - Input: Accept (so da LAN admin)
   - Output: Accept
   - Forward: Reject
4. Zona `lan` (Main) existente:
   - Permitir forward para `iot` (Main → IoT)

### A5. Firewall — regras inter-VLAN

**Network → Firewall → Traffic Rules → Add:**

| Nome | Source | Destination | Action |
|---|---|---|---|
| Block-IoT-Internet | iot | wan | Reject |
| Allow-Main-IoT | lan | iot | Accept |
| Block-IoT-Main | iot | lan | Reject |

### A6. Desactivar riscos

1. **Network → Firewall → General Settings** → desactivar **UPnP** (se activo)
2. **Wireless → WPS** → desactivar em todas as radios
3. Save & Apply

---

## Opcao B — SSH (UCI)

Se tiveres SSH activo no router (`ssh root@192.168.10.1`):

1. Copia [`scripts/openwrt-vlan-setup.sh`](../../scripts/openwrt-vlan-setup.sh) para o router
2. **Edita** as variaveis de device VLAN conforme o teu hardware (`ip link` no router)
3. Executa:

```sh
sh openwrt-vlan-setup.sh
```

> O script e um **template** — rever antes de executar. Faz backup primeiro.

---

## Verificar device VLAN no WR11000

Via SSH no router:

```sh
ip link
swconfig dev switch0 show
# ou
bridge vlan show
```

Anota o nome correcto (ex.: `lan1`, `eth1`, `switch0`) — varia por firmware.

---

## Testes pos-configuracao

No **PC hub** (`192.168.10.131`):

```powershell
# Internet — deve funcionar
curl -s -o NUL -w "%{http_code}" https://google.com

# Ping gateway IoT — deve responder apos criar VLAN 30
ping 192.168.30.1
```

Quando tiveres um dispositivo na VLAN IoT:

```powershell
# Do PC hub — deve aceder dispositivo IoT
ping 192.168.30.x
```

Do dispositivo IoT (telefone ligado a SSID IoT ou cabo VLAN 30):

- `https://google.com` → **deve falhar**
- Nao deve aceder a `192.168.10.131` directamente

---

## SSID Wi-Fi separado para IoT (opcional)

Se o WR11000 tiver Wi-Fi:

1. **Network → Wireless → Add**
2. SSID: `FRIDAY-IoT`
3. Network: `iot` (VLAN 30)
4. Security: WPA2/WPA3 forte
5. **Nao** fazer bridge com LAN Main

---

## Rollback

Se perderes acesso:

1. Reset fisico do router (botao reset 10s)
2. Restaurar backup: LuCI → System → Backup → Restore backup

---

## Checklist

Marca em [checklist-vlan.md](checklist-vlan.md) apos cada passo.

| Campo | Valor |
|---|---|
| Plataforma | OpenWrt LuCI — WR11000 |
| Gateway | 192.168.10.1 |
| Hub MAC | D8-43-AE-90-B5-21 |
| Hub IP | 192.168.10.131 |
