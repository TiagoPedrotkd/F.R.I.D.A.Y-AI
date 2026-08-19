# Topologia de Rede — VLANs F.R.I.D.A.Y-AI

Configurar **antes da Fase 3** (casa inteligente + câmaras).

## VLANs

| VLAN | ID | Subnet | Gateway | Dispositivos | Internet |
|---|---|---|---|---|---|
| **Main** | 10 | `192.168.10.0/24` | `192.168.10.1` | PC hub, telemóvel, portátil | Permitido (filtrado) |
| **IoT** | 30 | `192.168.30.0/24` | `192.168.30.1` | Câmaras RTSP, sensores, smart plugs | **Bloqueado** |
| **Mgmt** | 99 | `192.168.99.0/24` | `192.168.99.1` | Router, APs, switch managed | Admin only |

O PC hub está actualmente em `192.168.10.131` (VLAN Main).

## Regras de firewall

```
IoT → Internet:       DENY   (câmaras nunca saem de casa)
IoT → Main:           DENY   (excepto respostas a pedidos iniciados pelo hub)
Main → IoT:           ALLOW  (hub acede RTSP, Home Assistant API)
Guest → All:          DENY
Internet → Hub:       DENY   (sem port forwarding)
Main → Internet:      ALLOW  (HTTPS outbound — calendar, email, banking, updates)
```

## Diagrama físico

```
Internet ── modem/router (VLAN-capable)
              │
         Switch PoE (futuro, P5)
         ├── [VLAN10] PC Windows (hub FRIDAY) — 192.168.10.131
         ├── [VLAN30] Câmaras PoE (RTSP only)
         └── [VLAN30] Home Assistant / radios IoT
```

## Checklist de configuração

- [ ] Criar VLAN 10 (Main), 30 (IoT), 99 (Mgmt) no router/switch
- [ ] Atribuir subnets conforme tabela acima
- [ ] Reserva DHCP fixa para PC hub (`192.168.10.131`)
- [ ] Aplicar regras de firewall inter-VLAN
- [ ] Bloquear internet na VLAN IoT
- [ ] Testar: PC hub acede RTSP na VLAN IoT (quando câmaras existirem)
- [ ] Testar: dispositivo IoT **não** acede internet
- [ ] Exportar configuração do router (backup offline)
- [ ] Documentar passwords admin do router no Vaultwarden (Fase 6)

## Configuração por plataforma

### TP-Link Omada

1. Controller → Settings → Wired Networks → LAN → Create New Network
2. VLAN ID: 30, Gateway/Subnet: `192.168.30.1/24`
3. Settings → Transmission → Firewall → ACL → Add Rule:
   - Source: IoT (VLAN 30) → Destination: Internet → Action: Deny
4. Switch → Port profile: assign VLAN 30 to camera ports

### UniFi (Ubiquiti)

1. Settings → Networks → Create New → VLAN ID 30
2. Settings → Firewall → LAN In → Block IoT → Internet
3. Settings → Firewall → LAN In → Allow Main → IoT (established only)
4. Switch → Port → Network: VLAN 30 (cameras)

### ASUS Merlin / Fritz!Box

1. LAN → VLAN → Add VLAN 30 with subnet `192.168.30.0/24`
2. Firewall → Guest network isolation (adapt for IoT VLAN)
3. Assign ports to VLAN via switch config

**Implementado (Cudy WR11000):** Guest Network isolada — ver [rede-vlan-cudy-wr11000.md](rede-vlan-cudy-wr11000.md).

### OpenWrt / LuCI — WR11000 (LuCI avancado)

Router detectado em `192.168.10.1` (OpenWrt + LuCI, modelo WR11000).

**Guia completo:** [rede-vlan-openwrt-wr11000.md](rede-vlan-openwrt-wr11000.md)

**Script SSH (template):** [`scripts/openwrt-vlan-setup.sh`](../../scripts/openwrt-vlan-setup.sh)

Resumo rapido LuCI:
1. Network → Interfaces → criar `iot` (192.168.30.1/24) e `mgmt` (192.168.99.1/24)
2. Network → DHCP → reserva estatica MAC `D8-43-AE-90-B5-21` → `192.168.10.131`
3. Network → Firewall → zona `iot` sem forward para WAN; regra Block IoT → Internet
4. Desactivar UPnP e WPS

> Adaptar passos ao firmware exacto. O princípio é o mesmo: **3 VLANs, IoT sem internet, Main acede IoT**.

## DNS local (opcional, Fase 3+)

- **AdGuard Home** ou **Pi-hole** no Docker (gratuito)
- VLAN IoT usa DNS do hub para bloquear telemetria de dispositivos
- Container config (futuro):

```yaml
# adguardhome:
#   image: adguard/adguardhome
#   ports:
#     - "53:53/tcp"
#     - "53:53/udp"
#     - "3000:3000/tcp"
```

## Acesso remoto (opcional)

- **Tailscale** (gratuito, 100 devices) — mesh VPN sem port forwarding
- Instalar no PC hub: `winget install Tailscale.Tailscale`
- Nunca expor Frigate, Home Assistant ou LM Studio directamente à internet

## Testes de validação

```powershell
# Do PC hub (VLAN Main) — quando câmaras existirem:
curl rtsp://192.168.30.x:554/stream

# De um dispositivo na VLAN IoT — deve falhar:
curl https://google.com

# Do PC hub — deve funcionar:
curl https://google.com
```

## Notas de segurança

- Câmaras IP são vectores de ataque frequentes — VLAN IoT isolada mitiga acesso ao PC
- Desactivar UPnP no router
- Desactivar WPS nos APs
- Firmware do router/APs sempre actualizado
