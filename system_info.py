# system_info.py
import subprocess
from blueprints.rede import carrega_config_atual
from licenca import get_modulos


def get_system_info():
    info = {}
    
    # --- Informações de Rede ---
    network = carrega_config_atual()
    info["hostname"] = network["hostname"]
    info["ip_atual"] = network["ip_atual"]
    info["netmask"] = network["netmask"]
    info["gateway"] = network["gateway"]
    info["dns"] = network["dns"]

    # --- Informações do Asterisk ---
    try:
        # CORREÇÃO: Usar uma lista de argumentos em vez de shell=True é mais seguro.
        # O comando 'asterisk -V' não precisa de sudo, pois não se comunica com o processo.
        versao_output = subprocess.check_output(["asterisk", "-V"], text=True, stderr=subprocess.PIPE)
        info["versao_asterisk"] = versao_output.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info["versao_asterisk"] = "Não foi possível obter a versão"

    try:
        # CORREÇÃO: Adicionado 'sudo' para permitir a comunicação com o Asterisk.
        # O comando foi simplificado para ser mais legível e robusto.
        command = ["asterisk", "-rx", "sip show peers"]
        peers_output = subprocess.check_output(command, text=True, stderr=subprocess.PIPE)
        # Processa a saída para contar os ramais
        # Conta linhas que não são cabeçalho/rodapé e contêm "OK" (indicando um peer registrado)
        ramais_registrados = [line for line in peers_output.splitlines() if "OK" in line]
        total_peers = len(peers_output.splitlines()) - 2 # Subtrai cabeçalho e rodapé
        
        info["ramais_cadastrados"] = f"{len(ramais_registrados)} registrados de {total_peers} configurados"

    except (subprocess.CalledProcessError, FileNotFoundError):
        info["ramais_cadastrados"] = "Não foi possível obter a lista de ramais"

    info["modulos"] = get_modulos()
        
    return info

