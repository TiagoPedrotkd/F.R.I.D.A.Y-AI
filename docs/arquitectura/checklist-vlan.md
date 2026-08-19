# Checklist VLAN — F.R.I.D.A.Y-AI

Executar **antes da Fase 3** (casa inteligente + câmaras).

**Implementado (2026-08-19):** Guest Network isolada no **Cudy WR11000** em vez de VLAN 30/99 completa. Ver [rede-vlan-cudy-wr11000.md](rede-vlan-cudy-wr11000.md).

## Pré-requisitos

- [x] Confirmar que router suporta segmentação — **Cudy WR11000 @ 192.168.10.1**
- [ ] Exportar configuração actual do router (backup) — ver passos abaixo

### Backup router (manual — LuCI)

1. Abrir [http://192.168.10.1](http://192.168.10.1) → login
2. **System** → **Backup / Restore**
3. **Generate archive** → guardar ficheiro `.tar.gz` em local seguro
4. Marcar este item quando concluído

## Criação de VLANs / isolamento IoT

- [x] VLAN 10 — Main (`192.168.10.0/24`) — **LAN actual**
- [x] Rede IoT isolada — **Guest 2.4G** + Access Filter (substitui VLAN 30)
- [ ] VLAN 99 Mgmt dedicada — **Adiado** (admin via router `192.168.10.1`)

## Atribuição de dispositivos

- [x] PC hub na Main — IP `192.168.10.131`, MAC `D8-43-AE-90-B5-21`
- [ ] Portas de câmaras na rede IoT (quando existirem) — ligar ao Guest Wi-Fi ou Ethernet VLAN futuro

## Firewall / segurança

- [x] Guest **sem** acesso intranet (Main) — validado no telemóvel
- [x] Internet no PC Main — OK
- [x] Firewall Windows porta 8080 — regra `FRIDAY-Healthcheck`
- [x] Desactivar WPS
- [x] Desactivar UPnP

## Testes

- [x] PC hub acede internet (HTTPS)
- [x] Telemóvel Guest **não** acede `192.168.10.131:8080`
- [x] Telemóvel Main acede `http://192.168.10.131:8080/health`
- [ ] Dispositivo IoT real na Guest (quando existir câmara/sensor)

## Pós-configuração

- [ ] Exportar configuração do router (backup)
- [ ] Documentar passwords admin (Vaultwarden, Fase 6)

## Data de conclusão

| Campo | Valor |
|---|---|
| Concluída em | 2026-08-19 |
| Plataforma router | Cudy WR11000 (OpenWrt-based UI) |
| Abordagem | Guest Network 2.4G + Access Filter |
| Guia | [rede-vlan-cudy-wr11000.md](rede-vlan-cudy-wr11000.md) |
