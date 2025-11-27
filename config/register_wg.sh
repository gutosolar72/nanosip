#!/bin/bash
set -e

# Diretórios e arquivos
KEY_DIR="/etc/wireguard"
WG_CONF="/etc/wireguard/wg0.conf"
PRIVATE_KEY_FILE="$KEY_DIR/private.key"
PUBLIC_KEY_FILE="$KEY_DIR/public.key"
LICENSE_FILE="/opt/nanosip/venv/bin/.lic/.lic.json"
#LICENSE_HASH=$(jq -r '.hardware_id' venv/bin/.lic/.lic.json)
API_URL="https://gerenciamento.nanosip.com.br/api/remote_access"

if [ -f "$WG_CONF" ]; then
    exit 0
fi

if [ ! -f "$LICENSE_FILE" ]; then
    exit 0
fi

LICENSE_HASH=$(jq -r '.hardware_id' $LICENSE_FILE)

# 1️⃣ Gerar chaves locais se ainda não existirem
if [ ! -f "$PRIVATE_KEY_FILE" ] || [ ! -f "$PUBLIC_KEY_FILE" ]; then
    echo "Gerando chaves WireGuard..."
    PRIVATE_KEY=$(wg genkey)
    echo "$PRIVATE_KEY" > "$PRIVATE_KEY_FILE"
    chmod 600 "$PRIVATE_KEY_FILE"

    PUBLIC_KEY=$(echo "$PRIVATE_KEY" | wg pubkey)
    echo "$PUBLIC_KEY" > "$PUBLIC_KEY_FILE"
    chmod 644 "$PUBLIC_KEY_FILE"

    echo "Chaves geradas com sucesso."
else
    echo "Chaves já existem, pulando geração."
    PRIVATE_KEY=$(cat "$PRIVATE_KEY_FILE")
fi

echo ---- $PUBLIC_KEY
# 2️⃣ Registrar na API e criar wg0.conf se não existir
if [ ! -f "$WG_CONF" ]; then
    echo "Registrando no servidor e criando wg0.conf..."
    RESPONSE=$(jq -n --arg chave_licenca "$LICENSE_HASH" --arg public_key "$PUBLIC_KEY" '{chave_licenca: $chave_licenca, public_key: $public_key}' | \
        curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d @-)

    # Extrair dados da API
    ADDRESS=$(echo "$RESPONSE" | jq -r '.wg_config.address')
    ALLOWED_IPS=$(echo "$RESPONSE" | jq -r '.wg_config.allowed_ips')
    DNS=$(echo "$RESPONSE" | jq -r '.wg_config.dns')
    ENDPOINT=$(echo "$RESPONSE" | jq -r '.wg_config.endpoint')
    SERVER_PUBLIC_KEY=$(echo "$RESPONSE" | jq -r '.wg_config.server_public_key')

    # Criar wg0.conf
    cat > "$WG_CONF" <<EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = $ADDRESS

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
AllowedIPs = $ALLOWED_IPS
Endpoint = $ENDPOINT
PersistentKeepalive = 25
EOF

    chmod 600 "$WG_CONF"

    # Reiniciar WireGuard
    sleep 5
    systemctl restart wg-quick@wg0.service
    echo "WireGuard registrado e iniciado com sucesso!"
fi

