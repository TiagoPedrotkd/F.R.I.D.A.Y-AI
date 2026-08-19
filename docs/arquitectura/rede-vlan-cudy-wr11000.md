# Rede IoT — Cudy WR11000 (Guest Network)

Configuracao aplicada em **2026-08-19** no router **Cudy WR11000** (`192.168.10.1`).

Substitui VLAN 30/99 completa (nao exposta na UI Cudy) por **Guest Network isolada** — suficiente para Fase 3.

## Topologia actual

| Rede | Subnet | Uso |
|---|---|---|
| **Main (LAN)** | `192.168.10.0/24` | PC hub, telemoveis, portateis |
| **Guest 2.4G (IoT)** | Subnet guest isolada | Dispositivos IoT futuros |
| **Mgmt** | Router admin @ `192.168.10.1` | Administracao |

## Configuracao Guest Network

| Setting | Valor |
|---|---|
| **2.4G Guest** | Activado |
| **5G / 6G Guest** | Desactivado (por agora) |
| **Access Filter** | Activado |
| **Access intranet** | **OFF** (nao acede a `192.168.10.x`) |

## Outras configuracoes

| Item | Estado |
|---|---|
| IP fixo PC hub (`192.168.10.131`) | IP/MAC Binding — MAC `D8-43-AE-90-B5-21` |
| WPS | Desactivado |
| UPnP | Desactivado |
| Backup router | Recomendado — System → Backup / Restore |

## Validacao (2026-08-19)

| Teste | Resultado |
|---|---|
| PC `curl http://localhost:8080/health` | 200 OK |
| Telemovel **Main** Wi-Fi → `http://192.168.10.131:8080/health` | OK (HTTP, nao HTTPS) |
| Telemovel **Guest** Wi-Fi → `http://192.168.10.131:8080/health` | Bloqueado (isolamento OK) |
| Firewall Windows porta 8080 | Regra `FRIDAY-Healthcheck` activa |

## Notas

- Usar **`http://`** no telemovel, nunca `https://` (servico local sem TLS)
- Router quarto (mesh): funciona se for o **mesmo SSID Main**; Guest continua isolada
- VLAN 802.1Q completa (30/99) fica para **switch managed** futuro (roadmap P5)

## Documentos relacionados

- [rede-vlan.md](rede-vlan.md) — topologia generica VLAN
- [rede-vlan-openwrt-wr11000.md](rede-vlan-openwrt-wr11000.md) — LuCI avancado (alternativa)
- [checklist-vlan.md](checklist-vlan.md) — checklist actualizado
- [../fase-0/rede-local.md](../fase-0/rede-local.md) — acesso LAN FRIDAY
