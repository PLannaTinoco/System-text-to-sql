#fazer a implementação nos outros codigos 
import os

def get_project_root():
    """Retorna o diretório raiz do projeto (Soliris/)"""
    # A partir de interface/utils/path_utils.py, sobe 2 níveis
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_src_path(*path_parts):
    """Retorna caminho para arquivos em src/"""
    return os.path.join(get_project_root(), "src", *path_parts)

def get_interface_path(*path_parts):
    """Retorna caminho para arquivos em interface/"""
    return os.path.join(get_project_root(), "interface", *path_parts)

def get_hist_path(*path_parts):
    """Retorna caminho para arquivos de histórico"""
    return os.path.join(get_project_root(), "interface", "auth", "hist", *path_parts)

def get_arq_path(*path_parts):
    """Retorna caminho para arquivos em src/arq/"""
    return os.path.join(get_project_root(), "src", "arq", *path_parts)

