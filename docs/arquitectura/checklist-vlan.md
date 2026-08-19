# Checklist VLAN — F.R.I.D.A.Y-AI

Executar **antes da Fase 3** (casa inteligente + câmaras). Guia completo: [rede-vlan.md](rede-vlan.md).

## Pré-requisitos

- [ ] Confirmar que router/switch suporta VLANs (802.1Q)
- [ ] Exportar configuração actual do router (backup)

## Criação de VLANs

- [ ] VLAN 10 — Main (`192.168.10.0/24`, gateway `192.168.10.1`)
- [ ] VLAN 30 — IoT (`192.168.30.0/24`, gateway `192.168.30.1`)
- [ ] VLAN 99 — Mgmt (`192.168.99.0/24`, gateway `192.168.99.1`)

## Atribuição de dispositivos

- [ ] PC hub na VLAN 10 — reserva DHCP `192.168.10.131`
- [ ] Portas de câmaras na VLAN 30 (quando existirem)
- [ ] Router/APs na VLAN 99

## Firewall

- [ ] IoT → Internet: **DENY**
- [ ] IoT → Main: **DENY** (excepto respostas a pedidos do hub)
- [ ] Main → IoT: **ALLOW**
- [ ] Internet → Hub: **DENY** (sem port forwarding)
- [ ] Desactivar UPnP no router
- [ ] Desactivar WPS nos APs

## Testes

- [ ] PC hub acede internet (HTTPS)
- [ ] Dispositivo IoT **não** acede internet
- [ ] PC hub acede dispositivo IoT (quando existir)
- [ ] Dispositivo IoT **não** acede PC hub directamente

## Pós-configuração

- [ ] Exportar nova configuração do router (backup)
- [ ] Documentar passwords admin (Vaultwarden, Fase 6)

## Data de conclusão

| Campo | Valor |
|---|---|
| Concluída em | _preencher_ |
| Plataforma router | _preencher (Omada/UniFi/ASUS/etc.)_ |
| Notas | _preencher_ |
