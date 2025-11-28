import os
from database import get_db
from licenca import get_modulos

EXTENSIONS_CONF_PATH = '/etc/asterisk/extensions.conf'

# --- Funções de Busca no Banco de Dados ---
def get_all_peers(db):
    peers_raw = db.execute("SELECT ramal FROM ramais ORDER BY ramal").fetchall()
    return [str(p['ramal']) for p in peers_raw]

def get_all_queues(db):
    queues_raw = db.execute("SELECT fila FROM filas ORDER BY fila").fetchall()
    return [str(q['fila']) for q in queues_raw]

def get_all_routes(db):
    routes_raw = db.execute("SELECT * FROM rotas ORDER BY nome").fetchall()
    routes = []
    for r in routes_raw:
        time_conditions = db.execute(
            "SELECT * FROM time_conditions WHERE rota_id = ?", (r['id'],)
        ).fetchall()
        r = dict(r)
        r['time_conditions'] = [dict(tc) for tc in time_conditions]
        routes.append(r)
    return routes

# --- Função Principal de Geração ---
def generate_extensions_conf():
    print("Iniciando a geração do arquivo extensions.conf...")
    db = get_db()

    peers = get_all_peers(db)
    queues = get_all_queues(db)
    routes = get_all_routes(db)
    MODULOS = get_modulos()
    gravar_chamadas = 'record' in MODULOS.lower().split(',')

    conf_parts = [
        "; Arquivo gerado automaticamente pelo Micro PABX",
        "[interno] ; Contexto Unificado para todas as chamadas"
    ]

    # --- Include extensions_custom ---
    conf_parts.extend([
            "\n; --- Include extensions_custom --------",
            "#include \"extensions_custom.conf\"\n"
    ])

    # --- Rotas de Entrada ---
    if routes:
        conf_parts.append("\n; --- Regras Customizadas: Rotas de Entrada ---")
        for route in routes:
            exten = route['numero_entrada']

            fila_else_num = None
            if route['dest_fila_else']:
                fila_else_row = db.execute(
                    "SELECT fila FROM filas WHERE id = ?", (route['dest_fila_else'],)
                ).fetchone()
                if fila_else_row:
                    fila_else_num = fila_else_row['fila']

            conf_parts.append(f"\n; Rota: {route['nome']}")
            conf_parts.append(f"exten => {exten},1,NoOp(### Rota de Entrada: {route['nome']} para o numero {exten} ###)")

            if route['time_conditions']:
                for tc in route['time_conditions']:
                    if not tc['dest_fila_if_time']:
                        continue
                    fila_if_time_row = db.execute(
                        "SELECT fila FROM filas WHERE id = ?", (tc['dest_fila_if_time'],)
                    ).fetchone()
                    if not fila_if_time_row:
                        continue
                    fila_if_time_num = fila_if_time_row['fila']
                    time_start = tc['time_start']
                    time_end = tc['time_end']
                    days = tc['days'].split(',')

                    for day in days:
                        day = day.strip()
                        if not day:
                            continue
                        timestart = time_start.replace(':','-')
                        conf_parts.append(
                            f"exten => {exten},n,GotoIfTime({time_start}-{time_end},{day},*,*?time-{day}-{timestart})"
                        )

                    # Fora do horário
                    if fila_else_num:
                        if gravar_chamadas:
                            conf_parts.append(f"exten => {exten},n,Set(UNIQUEID_SAFE=${{CUT(UNIQUEID,.,1)}})")
                            conf_parts.append(f"exten => {exten},n,Set(ARQUIVO=${{CALLERID(num)}}-${{EXTEN}}-${{UNIQUEID_SAFE}})")
                            conf_parts.append(f"exten => {exten},n,MixMonitor(${{ARQUIVO}}.wav,b)")
                        conf_parts.append(f"exten => {exten},n,Queue({fila_else_num}) ; Rota fora do horario")
                        if gravar_chamadas:
                            conf_parts.append(f"exten => {exten},n,StopMixMonitor()")
                    conf_parts.append(f"exten => {exten},n,Hangup()")

                    # Dentro do horário
                    for day in days:
                        day = day.strip()
                        if not day:
                            continue
                        conf_parts.append(f"exten => {exten},n(time-{day}-{timestart})")
                        if gravar_chamadas:
                            conf_parts.append(f"exten => {exten},n,Set(UNIQUEID_SAFE=${{CUT(UNIQUEID,.,1)}})")
                            conf_parts.append(f"exten => {exten},n,Set(ARQUIVO=${{CALLERID(num)}}-${{EXTEN}}-${{UNIQUEID_SAFE}})")
                            conf_parts.append(f"exten => {exten},n,MixMonitor(${{ARQUIVO}}.wav,b)")
                            conf_parts.append(f"exten => {exten},n,Answer()")
                        conf_parts.append(f"exten => {exten},n,Queue({fila_if_time_num}) ; Rota dentro do horario")
                        if gravar_chamadas:
                            conf_parts.append(f"exten => {exten},n,StopMixMonitor()")
                        conf_parts.append(f"exten => {exten},n,Hangup()")
            else:
                # Sem time condition
                if fila_else_num:
                    if gravar_chamadas:
                        conf_parts.append(f"exten => {exten},n,Set(UNIQUEID_SAFE=${{CUT(UNIQUEID,.,1)}})")
                        conf_parts.append(f"exten => {exten},n,Set(ARQUIVO=${{CALLERID(num)}}-${{EXTEN}}-${{UNIQUEID_SAFE}})")
                        conf_parts.append(f"exten => {exten},n,MixMonitor(${{ARQUIVO}}.wav,b)")
                    conf_parts.append(f"exten => {exten},n,Queue({fila_else_num})")
                    if gravar_chamadas:
                        conf_parts.append(f"exten => {exten},n,StopMixMonitor()")
                conf_parts.append(f"exten => {exten},n,Hangup()")

    # --- Chamadas para Filas ---
    if queues:
        conf_parts.append("\n; --- Regra Automatica: Chamadas para Filas ---")
        for queue in queues:
            conf_parts.append(f"exten => {queue},1,NoOp(### Chamada interna para Fila ${{EXTEN}} ###)")
            if gravar_chamadas:
                conf_parts.append(f"exten => {queue},n,Set(UNIQUEID_SAFE=${{CUT(UNIQUEID,.,1)}})")
                conf_parts.append(f"exten => {queue},n,Set(ARQUIVO=${{CALLERID(num)}}-${{EXTEN}}-${{UNIQUEID_SAFE}})")
                conf_parts.append(f"exten => {queue},n,MixMonitor(${{ARQUIVO}}.wav,b)")
            conf_parts.append(f"exten => {queue},n,Answer()")
            conf_parts.append(f"exten => {queue},n,Queue(${{EXTEN}})")
            if gravar_chamadas:
                conf_parts.append(f"exten => {queue},n,StopMixMonitor()")
            conf_parts.append(f"exten => {queue},n,Hangup()\n")

    # --- Chamadas para Ramais ---
    if peers:
        conf_parts.append("\n; --- Regra Automatica: Chamadas para outros Ramais ---")
        for pattern in ['_X', '_X.']:
            conf_parts.append(f"exten => {pattern},1,NoOp(### Chamada interna para Ramal ${{EXTEN}} ###)")
            if gravar_chamadas:
                conf_parts.append(f"exten => {pattern},n,Set(UNIQUEID_SAFE=${{CUT(UNIQUEID,.,1)}})")
                conf_parts.append(f"exten => {pattern},n,Set(ARQUIVO=${{CALLERID(num)}}-${{EXTEN}}-${{UNIQUEID_SAFE}})")
                conf_parts.append(f"exten => {pattern},n,MixMonitor(${{ARQUIVO}}.wav,b)")
            conf_parts.append(f"exten => {pattern},n,Answer()")
            conf_parts.append(f"exten => {pattern},n,Dial(SIP/${{EXTEN}},20,Ttr)")
            if gravar_chamadas:
                conf_parts.append(f"exten => {pattern},n,StopMixMonitor()")
            conf_parts.append(f"exten => {pattern},n,Hangup()\n")


    db.close()

    # --- Escreve o arquivo ---
    conf_content = "\n".join(conf_parts)
    try:
        with open(EXTENSIONS_CONF_PATH, 'w') as f:
            f.write(conf_content)
        print(f"Sucesso! Arquivo '{EXTENSIONS_CONF_PATH}' foi gerado/atualizado.")
    except Exception as e:
        print(f"ERRO ao escrever extensions.conf: {e}")

if __name__ == "__main__":
    generate_extensions_conf()
