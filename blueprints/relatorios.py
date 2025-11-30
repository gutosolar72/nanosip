import csv
import os
import glob
from werkzeug.utils import safe_join
from flask import abort, send_from_directory, Blueprint, render_template, request, url_for, flash
from datetime import datetime
from licenca import get_modulos
from .main import license_message, license_context
from auth import login_required

relatorios_bp = Blueprint("relatorios", __name__, template_folder="../templates")

CSV_DIR = "/var/log/asterisk/cdr-csv"
CSV_FILE_PATTERN = os.path.join(CSV_DIR, "Master.csv*")
MONITOR_DIR = "/var/spool/asterisk/monitor"
MAX_FILES = 7


def parse_cdr():
    """Lê e processa os arquivos CSV do CDR do Asterisk."""
    registros = []

    arquivos = sorted(
        glob.glob(CSV_FILE_PATTERN),
        key=os.path.getmtime,
        reverse=True
    )[:MAX_FILES]

    for arquivo in arquivos:
        if not os.path.isfile(arquivo):
            flash(f"Arquivo {arquivo} não encontrado.", "warning")
            continue

        try:
            with open(arquivo, newline="", encoding="utf-8") as f:
                reader = list(csv.reader(f))
                for row in reversed(reader):
                    if not row or len(row) < 17:
                        continue

                    try:
                        dt = datetime.strptime(row[9], "%Y-%m-%d %H:%M:%S")
                        calldate_br = dt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        calldate_br = row[9]

                    uniqueid = row[16]
                    duration = row[12]
                    billsec = row[13]
                    disposition = row[14].strip().upper() if len(row) > 14 else "UNKNOWN"

                    # Arquivo de gravação
                    grava_file = os.path.join(MONITOR_DIR, f"{uniqueid}.wav")
                    recording = grava_file if os.path.isfile(grava_file) else None

                    # Mapeamento de status
                    status_map = {
                        "ANSWERED": "Atendida",
                        "BUSY": "Ocupado",
                        "FAILED": "Falha",
                        "NO ANSWER": "Não atendida",
                        "CANCEL": "Cancelada",
                        "CONGESTION": "Congestionada"
                    }

                    # Chamadas com 0s não são realmente atendidas
                    if disposition == "ANSWERED" and billsec == "0":
                        disposition = "NO ANSWER"

                    registros.append({
                        "calldate": calldate_br,
                        "src": row[1],
                        "dst": row[2],
                        "clid": row[4],
                        "lastapp": row[7],
                        "lastdata": row[8],
                        "duration": duration,
                        "billsec": billsec,
                        "disposition": status_map.get(disposition, disposition.capitalize()),
                        "uniqueid": uniqueid,
                        "recording": recording
                    })

        except Exception as e:
            flash(f"Erro ao processar {arquivo}: {e}", "danger")

    return registros

def gerar_paginacao(page, total_pages, delta=2):
    """
    Gera uma lista de páginas inteligente:
    - mostra primeira e última
    - mostra páginas próximas da atual
    - usa '...' quando necessário
    """
    pages = []
    for p in range(1, total_pages + 1):
        if (
            p == 1 or
            p == total_pages or
            abs(p - page) <= delta
        ):
            pages.append(p)
        else:
            # coloca None para indicar "..."
            if pages[-1] is not None:
                pages.append(None)
    return pages

@relatorios_bp.route("/relatorios")
@login_required
def relatorio_cdr():
    """Página de relatórios CDR com paginação e links de gravação."""
    page = int(request.args.get("page", 1))
    per_page = 20

    registros = parse_cdr()
    total = len(registros)
    total_pages = max((total // per_page) + (1 if total % per_page else 0), 1)

    if page < 1 or page > total_pages:
        flash("Página inexistente, mostrando primeira página.", "warning")
        page = 1

    start = (page - 1) * per_page
    end = start + per_page
    registros_paginados = registros[start:end]

    # Verifica módulo RECORD
    modulos_raw = get_modulos() or ''
    MODULOS = [m.strip().lower() for m in modulos_raw.split(',')]
    has_record = 'record' in MODULOS

    if has_record:
        for r in registros_paginados:
            uniqueid_safe = r['uniqueid'].split('.')[0]
            filename = f"{r['src']}-{r['dst']}-{uniqueid_safe}.wav"
            full_path = os.path.join(MONITOR_DIR, filename)

            if os.path.isfile(full_path) and os.path.getsize(full_path) > 44:
                r['recording'] = url_for('relatorios.recordings', filename=filename)
            else:
                r['recording'] = None

    paginas = gerar_paginacao(page, total_pages)

    return render_template(
        "relatorio_cdr.html",
        registros=registros_paginados,
        page=page,
        total_pages=total_pages,
        has_record=has_record,
        paginas=paginas,
        LICENSE_VALID=license_context(),
        LICENSE_MSG=license_message()
    )


@relatorios_bp.route("/recordings/<path:filename>")
@login_required
def recordings(filename):
    """Rota para download/reprodução de gravações."""
    path = safe_join(MONITOR_DIR, filename)
    if not os.path.isfile(path):
        flash(f"Arquivo de gravação {filename} não encontrado.", "warning")
        abort(404)
    return send_from_directory(MONITOR_DIR, filename)

