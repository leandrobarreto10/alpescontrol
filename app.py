import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import os
import io
import json
import hashlib
import shutil
import zipfile
import base64
import mimetypes
import secrets
import html
try:
    from supabase import create_client
except Exception:
    create_client = None
try:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
except Exception:
    Request = None
    service_account = None
    Credentials = None
    build = None
    HttpError = None
    MediaFileUpload = None
    MediaIoBaseDownload = None
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
try:
    import plotly.express as px
except Exception:
    px = None

st.set_page_config(page_title="Alpes Gestão e Facilities", page_icon="▣", layout="wide")

_streamlit_dataframe = st.dataframe


def dataframe_sem_indice(*args, **kwargs):
    kwargs.setdefault("hide_index", True)
    return _streamlit_dataframe(*args, **kwargs)


st.dataframe = dataframe_sem_indice

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("ALPES_DATA_DIR", BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
_drive_service_cache = None
_drive_pastas_cache = {}
_drive_arquivos_cache = {}
_supabase_client_cache = None


def obter_config_secreta(nome, padrao=""):
    valor = os.environ.get(nome)
    if valor:
        return valor
    try:
        return st.secrets.get(nome, padrao)
    except Exception:
        return padrao


def supabase_bucket_nome():
    return obter_config_secreta("SUPABASE_BUCKET", "alpes-system")


def supabase_chave():
    return (
        obter_config_secreta("SUPABASE_SERVICE_ROLE_KEY", "")
        or obter_config_secreta("SUPABASE_ANON_KEY", "")
        or obter_config_secreta("SUPABASE_KEY", "")
    )


def supabase_configurado():
    return bool(create_client and obter_config_secreta("SUPABASE_URL", "") and supabase_chave())


def supabase_guardar_erro(erro):
    try:
        st.session_state["ultimo_erro_supabase"] = str(erro)[:700]
    except Exception:
        pass


def obter_supabase_client():
    global _supabase_client_cache
    if _supabase_client_cache is not None:
        return _supabase_client_cache
    if not supabase_configurado():
        return None
    try:
        _supabase_client_cache = create_client(obter_config_secreta("SUPABASE_URL", ""), supabase_chave())
        return _supabase_client_cache
    except Exception as erro:
        supabase_guardar_erro(erro)
        return None


SUPABASE_BUCKET_IMAGENS_PRODUTOS = "imagens-produtos"

SUPABASE_ARQUIVO_TABELA = {
    "produtos.xlsx": {
        "tabela": "produtos",
        "colunas": ["codigo", "produto", "categoria", "estoque_minimo", "localizacao", "imagem", "unidade", "valor_unitario", "fornecedor", "status"],
        "chave": "codigo",
    },
    "movimentacoes.xlsx": {
        "tabela": "movimentacoes",
        "colunas": ["produto", "tipo", "quantidade", "data", "cliente", "observacao"],
        "chave": "",
    },
    "clientes.xlsx": {
        "tabela": "clientes",
        "colunas": ["codigo", "nome_cliente", "telefone", "cidade", "estado", "tipo_contrato", "data_inicial", "data_final", "status"],
        "chave": "codigo",
    },
    "fornecedores.xlsx": {
        "tabela": "fornecedores",
        "colunas": ["codigo", "nome_fornecedor", "telefone", "cidade", "estado", "tipo_contrato", "data_inicial", "data_final", "status"],
        "chave": "codigo",
    },
    "controle_faltas.xlsx": {
        "tabela": "controle_faltas",
        "colunas": ["data", "colaborador", "funcao", "presenca", "motivo_falta", "almocou_base", "observacoes", "tipo_escala", "data_base_escala", "trabalha_data_base", "status_colaborador", "base_frequencia"],
        "chave": "",
    },
    "frotas_veiculos.xlsx": {
        "tabela": "frotas_veiculos",
        "colunas": ["placa", "modelo", "marca", "ano", "tipo", "responsavel", "cidade_local", "status", "km_atual", "periodicidade_vistoria", "ultima_vistoria", "proxima_vistoria", "status_responsabilidade"],
        "chave": "placa",
    },
    "frotas_abastecimentos.xlsx": {
        "tabela": "frotas_abastecimentos",
        "colunas": ["data", "placa", "km", "combustivel", "litros", "valor_litro", "valor_total", "posto", "responsavel_lancamento", "registrado_em", "nota_anexo", "status_conferencia", "observacao_administrativo", "observacoes"],
        "chave": "",
    },
    "frotas_manutencoes.xlsx": {
        "tabela": "frotas_manutencoes",
        "colunas": ["data", "placa", "tipo_manutencao", "km", "servico_executado", "fornecedor", "valor", "manutencao_agendada", "proxima_revisao", "status_manutencao", "responsavel_lancamento", "registrado_em", "nota_anexo", "status_conferencia", "observacao_administrativo", "observacoes"],
        "chave": "",
    },
    "frotas_documentos.xlsx": {
        "tabela": "frotas_documentos",
        "colunas": ["placa", "documento", "vencimento", "valor", "status", "observacoes"],
        "chave": "",
    },
    "frotas_entregas.xlsx": {
        "tabela": "frotas_entregas",
        "colunas": ["data", "placa", "responsavel", "km", "periodicidade", "proxima_vistoria", "pneus", "lataria", "vidros", "farois_lanternas", "documentacao", "itens_obrigatorios", "fotos", "observacoes", "registrado_em"],
        "chave": "",
    },
    "frotas_vistorias.xlsx": {
        "tabela": "frotas_vistorias",
        "colunas": ["data", "placa", "tipo_vistoria", "responsavel", "km", "periodicidade", "proxima_vistoria", "pneus", "lataria", "vidros", "farois_lanternas", "documentacao", "itens_obrigatorios", "fotos", "observacoes", "registrado_em"],
        "chave": "",
    },
    "bases_movimentacoes.xlsx": {
        "tabela": "bases_movimentacoes",
        "colunas": ["data", "base", "produto", "tipo", "quantidade", "responsavel", "origem_destino", "observacoes"],
        "chave": "",
    },
    "bases_transferencias.xlsx": {
        "tabela": "bases_transferencias",
        "colunas": ["data", "produto", "quantidade", "origem", "destino", "responsavel_envio", "responsavel_recebimento", "status", "observacoes"],
        "chave": "",
    },
}

SUPABASE_JSON_TABELA = {
    "usuarios.json": {"tabela": "usuarios", "chave": "nome"},
    "auditoria.json": {"tabela": "logs_sistema", "chave": ""},
    "categorias.json": {"tabela": "categorias", "chave": "nome"},
    "unidades.json": {"tabela": "unidades", "chave": "nome"},
}


def supabase_limpar_valor(valor):
    if pd.isna(valor) if not isinstance(valor, (list, dict, tuple)) else False:
        return None
    if isinstance(valor, (pd.Timestamp, datetime)):
        return valor.isoformat()
    if hasattr(valor, "isoformat") and not isinstance(valor, str):
        try:
            return valor.isoformat()
        except Exception:
            pass
    if isinstance(valor, (int, float, str, bool, list, dict)) or valor is None:
        return valor
    return str(valor)


def supabase_id_registro(tabela, registro, indice=0, chave=""):
    if chave and str(registro.get(chave, "")).strip():
        return str(registro.get(chave)).strip()
    if tabela == "usuarios" and str(registro.get("email", "")).strip():
        return str(registro.get("email")).strip().lower()
    base = json.dumps(registro, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(f"{tabela}|{base}".encode("utf-8")).hexdigest()


def supabase_ler_dataframe(caminho, colunas):
    client = obter_supabase_client()
    cfg = SUPABASE_ARQUIVO_TABELA.get(os.path.basename(caminho))
    if not client or not cfg:
        return None
    try:
        resposta = client.table(cfg["tabela"]).select("*").execute()
        dados = getattr(resposta, "data", None) or []
        if not dados:
            return None
        df = pd.DataFrame(dados)
        df = df.drop(columns=["id", "created_at", "updated_at"], errors="ignore")
        for coluna in colunas:
            if coluna not in df.columns:
                df[coluna] = ""
        return df[colunas]
    except Exception as erro:
        supabase_guardar_erro(erro)
        return None


def supabase_salvar_dataframe(caminho, df):
    client = obter_supabase_client()
    cfg = SUPABASE_ARQUIVO_TABELA.get(os.path.basename(str(caminho)))
    if not client or not cfg or df is None:
        return False
    try:
        dados = df.copy()
        for coluna in cfg["colunas"]:
            if coluna not in dados.columns:
                dados[coluna] = ""
        dados = dados[cfg["colunas"]]
        registros = []
        for indice, row in dados.iterrows():
            registro = {coluna: supabase_limpar_valor(row.get(coluna, "")) for coluna in cfg["colunas"]}
            registro["id"] = supabase_id_registro(cfg["tabela"], registro, indice, cfg.get("chave", ""))
            registros.append(registro)
        if registros:
            client.table(cfg["tabela"]).upsert(registros, on_conflict="id").execute()
        st.session_state.pop("ultimo_erro_supabase", None)
        return True
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def supabase_ler_json(caminho, padrao):
    client = obter_supabase_client()
    nome = os.path.basename(caminho)
    if not client:
        return None
    try:
        if nome == "configuracoes.json":
            resposta = client.table("configuracoes").select("*").execute()
            dados = getattr(resposta, "data", None) or []
            if not dados:
                return None
            config_supabase = {}
            for item in dados:
                chave = item.get("chave")
                if chave:
                    config_supabase[chave] = item.get("valor")
            return config_supabase or None
        cfg = SUPABASE_JSON_TABELA.get(nome)
        if not cfg:
            return None
        resposta = client.table(cfg["tabela"]).select("*").execute()
        dados = getattr(resposta, "data", None) or []
        if not dados:
            return None
        return [
            {k: v for k, v in item.items() if k not in ["id", "created_at", "updated_at"]}
            for item in dados
        ]
    except Exception as erro:
        supabase_guardar_erro(erro)
        return None


def supabase_salvar_json(caminho, dados):
    client = obter_supabase_client()
    nome = os.path.basename(caminho)
    if not client:
        return False
    try:
        if nome == "configuracoes.json" and isinstance(dados, dict):
            registros = [{"chave": chave, "valor": valor} for chave, valor in dados.items()]
            if registros:
                client.table("configuracoes").upsert(registros, on_conflict="chave").execute()
            st.session_state.pop("ultimo_erro_supabase", None)
            return True
        cfg = SUPABASE_JSON_TABELA.get(nome)
        if cfg and isinstance(dados, list):
            registros = []
            for indice, item in enumerate(dados):
                if not isinstance(item, dict):
                    continue
                registro = {k: supabase_limpar_valor(v) for k, v in item.items()}
                registro["id"] = supabase_id_registro(cfg["tabela"], registro, indice, cfg.get("chave", ""))
                registros.append(registro)
            if registros:
                client.table(cfg["tabela"]).upsert(registros, on_conflict="id").execute()
            st.session_state.pop("ultimo_erro_supabase", None)
            return True
    except Exception as erro:
        supabase_guardar_erro(erro)
    return False


def supabase_tabela_tem_dados(tabela):
    client = obter_supabase_client()
    if not client or not tabela:
        return False
    try:
        resposta = client.table(tabela).select("id").limit(1).execute()
        return bool(getattr(resposta, "data", None))
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def supabase_configuracoes_tem_dados():
    client = obter_supabase_client()
    if not client:
        return False
    try:
        resposta = client.table("configuracoes").select("chave").limit(1).execute()
        return bool(getattr(resposta, "data", None))
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def supabase_migracao_concluida(nome_migracao):
    client = obter_supabase_client()
    if not client:
        return False
    try:
        resposta = (
            client.table("migracoes_sistema")
            .select("id,status")
            .eq("nome_migracao", nome_migracao)
            .eq("status", "concluida")
            .limit(1)
            .execute()
        )
        return bool(getattr(resposta, "data", None))
    except Exception:
        return False


def supabase_registrar_migracao(nome_migracao, status, importados=0, ignorados=0, erros=""):
    client = obter_supabase_client()
    if not client:
        return False
    try:
        registro = {
            "id": hashlib.sha256(str(nome_migracao).encode("utf-8")).hexdigest(),
            "nome_migracao": str(nome_migracao),
            "status": str(status),
            "data_execucao": datetime.now().isoformat(),
            "registros_importados": int(importados or 0),
            "registros_ignorados": int(ignorados or 0),
            "erros": str(erros or "")[:2000],
        }
        client.table("migracoes_sistema").upsert(registro, on_conflict="id").execute()
        return True
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def migrar_arquivo_dataframe_para_supabase(nome_arquivo, caminho, colunas):
    client = obter_supabase_client()
    cfg = SUPABASE_ARQUIVO_TABELA.get(nome_arquivo)
    if not client or not cfg or not os.path.exists(caminho):
        return False
    if supabase_tabela_tem_dados(cfg["tabela"]):
        return False
    try:
        df_migracao = pd.read_excel(caminho)
        if df_migracao.empty:
            return False
        for coluna in colunas:
            if coluna not in df_migracao.columns:
                df_migracao[coluna] = ""
        return supabase_salvar_dataframe(caminho, df_migracao[colunas])
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def migrar_arquivo_json_para_supabase(nome_arquivo, caminho):
    client = obter_supabase_client()
    cfg = SUPABASE_JSON_TABELA.get(nome_arquivo)
    if not client or not cfg or not os.path.exists(caminho):
        return False
    if supabase_tabela_tem_dados(cfg["tabela"]):
        return False
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not dados:
            return False
        return supabase_salvar_json(caminho, dados)
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def migrar_configuracoes_para_supabase():
    caminho = os.path.join(DATA_DIR, "configuracoes.json")
    if not supabase_configurado() or not os.path.exists(caminho):
        return False
    if supabase_configuracoes_tem_dados():
        return False
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, dict) or not dados:
            return False
        return supabase_salvar_json(caminho, dados)
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def migrar_pastas_storage_para_supabase():
    if not supabase_configurado():
        return 0
    enviados = 0
    for pasta in pastas_permitidas_backup():
        pasta_abs = os.path.join(DATA_DIR, pasta)
        if not os.path.isdir(pasta_abs):
            continue
        for raiz, _, arquivos in os.walk(pasta_abs):
            for nome in arquivos:
                caminho_arquivo = os.path.join(raiz, nome)
                if upload_arquivo_remoto(caminho_arquivo):
                    enviados += 1
    return enviados


def migrar_dados_existentes_para_supabase():
    if not supabase_configurado() or st.session_state.get("migracao_supabase_executada"):
        return
    nome_migracao = "migracao_inicial_arquivos"
    if supabase_migracao_concluida(nome_migracao):
        st.session_state["migracao_supabase_executada"] = True
        return
    st.session_state["migracao_supabase_executada"] = True
    st.session_state["migracao_supabase_em_execucao"] = True
    migrados = []
    try:
        for nome_arquivo, cfg in SUPABASE_ARQUIVO_TABELA.items():
            caminho = os.path.join(DATA_DIR, nome_arquivo)
            if migrar_arquivo_dataframe_para_supabase(nome_arquivo, caminho, cfg["colunas"]):
                migrados.append(nome_arquivo)
        for nome_arquivo in SUPABASE_JSON_TABELA:
            caminho = os.path.join(DATA_DIR, nome_arquivo)
            if migrar_arquivo_json_para_supabase(nome_arquivo, caminho):
                migrados.append(nome_arquivo)
        if migrar_configuracoes_para_supabase():
            migrados.append("configuracoes.json")
        total_storage = migrar_pastas_storage_para_supabase()
        supabase_registrar_migracao(nome_migracao, "concluida", len(migrados), 0, "")
        if migrados or total_storage:
            st.session_state["migracao_supabase_resumo"] = (
                f"Migração Supabase concluída: {len(migrados)} arquivo(s) de dados e "
                f"{total_storage} arquivo(s) de storage enviados."
            )
    except Exception as erro:
        st.session_state["ultimo_erro_supabase"] = str(erro)[:700]
        supabase_registrar_migracao(nome_migracao, "erro", len(migrados), 0, str(erro))
    finally:
        st.session_state.pop("migracao_supabase_em_execucao", None)


def supabase_upload_imagem_produto(arquivo, nome_arquivo):
    client = obter_supabase_client()
    if not client or not arquivo or not nome_arquivo:
        return ""
    try:
        dados = arquivo.getbuffer()
        content_type = getattr(arquivo, "type", None) or mimetypes.guess_type(nome_arquivo)[0] or "application/octet-stream"
        bucket = client.storage.from_(SUPABASE_BUCKET_IMAGENS_PRODUTOS)
        try:
            bucket.upload(nome_arquivo, dados, file_options={"content-type": content_type, "x-upsert": "true"})
        except Exception:
            bucket.update(nome_arquivo, dados, file_options={"content-type": content_type, "x-upsert": "true"})
        return bucket.get_public_url(nome_arquivo)
    except Exception as erro:
        supabase_guardar_erro(erro)
        return ""


def google_drive_configurado():
    return bool(
        build
        and (service_account or Credentials)
        and MediaFileUpload
        and MediaIoBaseDownload
        and obter_config_secreta("GOOGLE_DRIVE_FOLDER_ID", "")
    )


def ambiente_streamlit_cloud():
    cwd = os.getcwd().replace("\\", "/").lower()
    return bool(
        os.environ.get("STREAMLIT_CLOUD")
        or os.environ.get("STREAMLIT_SHARING")
        or cwd.startswith("/mount/src")
        or "/mount/src/" in cwd
    )


def ambiente_execucao():
    valor = (
        obter_config_secreta("ENVIRONMENT", "")
        or obter_config_secreta("ALPES_ENVIRONMENT", "")
        or os.environ.get("ENVIRONMENT", "")
        or os.environ.get("ALPES_ENVIRONMENT", "")
    )
    valor = str(valor or "").strip().lower()
    if valor in {"production", "prod", "producao", "produção"}:
        return "production"
    if valor in {"development", "dev", "teste", "test", "staging"}:
        return "development"
    return "production" if ambiente_streamlit_cloud() else "development"


def ambiente_producao():
    return ambiente_execucao() == "production"


def armazenamento_persistente_configurado():
    if ambiente_producao():
        return bool(supabase_configurado())
    return bool(supabase_configurado() or google_drive_configurado())


def exigir_armazenamento_persistente_online():
    valor = str(obter_config_secreta("ALPES_EXIGIR_ARMAZENAMENTO_ONLINE", "")).strip().lower()
    if valor:
        return valor in {"1", "true", "sim", "yes", "on"}
    return ambiente_streamlit_cloud()


def fonte_local_permitida_para_dados():
    return not ambiente_producao() or bool(st.session_state.get("migracao_supabase_em_execucao"))


def arquivo_operacional(caminho):
    nome = os.path.basename(str(caminho or ""))
    arquivos_dados = set(SUPABASE_ARQUIVO_TABELA.keys()) | set(SUPABASE_JSON_TABELA.keys()) | {"configuracoes.json"}
    return nome in arquivos_dados


def erro_critico_supabase():
    st.error("Erro crítico: Supabase não configurado. O sistema não pode operar em produção sem banco de dados.")
    st.info("Configure SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e SUPABASE_BUCKET nos Secrets do Streamlit Cloud.")
    st.stop()


def validar_supabase_producao():
    if ambiente_producao() and not supabase_configurado():
        erro_critico_supabase()


def bloquear_gravacao_sem_armazenamento(caminho):
    if ambiente_producao() and arquivo_operacional(caminho) and not supabase_configurado():
        erro_critico_supabase()
    if not exigir_armazenamento_persistente_online() or armazenamento_persistente_configurado():
        return
    if not arquivo_operacional(caminho):
        return
    st.error(
        "Armazenamento persistente não configurado. "
        "Para usar o sistema online sem perder dados, configure SUPABASE_URL, "
        "SUPABASE_SERVICE_ROLE_KEY e SUPABASE_BUCKET nos Secrets do Streamlit."
    )
    st.stop()


def obter_google_oauth_info():
    info = {
        "client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        "refresh_token": os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", ""),
        "token_uri": os.environ.get("GOOGLE_OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    }
    try:
        if "google_oauth" in st.secrets:
            segredos = dict(st.secrets["google_oauth"])
            info.update({chave: segredos.get(chave, valor) for chave, valor in info.items()})
    except Exception:
        pass
    return info if info.get("client_id") and info.get("client_secret") and info.get("refresh_token") else None


def obter_google_service():
    global _drive_service_cache
    if _drive_service_cache is not None:
        return _drive_service_cache
    if not google_drive_configurado():
        return None

    oauth_info = obter_google_oauth_info()
    if oauth_info and Credentials and Request:
        try:
            credenciais = Credentials(
                token=None,
                refresh_token=oauth_info["refresh_token"],
                token_uri=oauth_info.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=oauth_info["client_id"],
                client_secret=oauth_info["client_secret"],
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            credenciais.refresh(Request())
            _drive_service_cache = build("drive", "v3", credentials=credenciais, cache_discovery=False)
            return _drive_service_cache
        except Exception as erro:
            drive_guardar_erro(erro)

    info_conta = None
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if service_account_json:
        info_conta = json.loads(service_account_json)
    else:
        try:
            if "google_service_account" in st.secrets:
                info_conta = dict(st.secrets["google_service_account"])
            elif "GOOGLE_SERVICE_ACCOUNT_INFO" in st.secrets:
                info_conta = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_INFO"])
        except Exception:
            info_conta = None

    if not info_conta:
        return None

    try:
        credenciais = service_account.Credentials.from_service_account_info(
            info_conta,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        _drive_service_cache = build("drive", "v3", credentials=credenciais, cache_discovery=False)
        return _drive_service_cache
    except Exception:
        return None


def drive_relativo(caminho):
    return os.path.relpath(caminho, DATA_DIR).replace("\\", "/")


def supabase_upload_arquivo(caminho_local):
    client = obter_supabase_client()
    if not client or not os.path.isfile(caminho_local):
        return False
    caminho_relativo = drive_relativo(caminho_local)
    content_type = mimetypes.guess_type(caminho_local)[0] or "application/octet-stream"
    try:
        with open(caminho_local, "rb") as arquivo:
            dados = arquivo.read()
        bucket = client.storage.from_(supabase_bucket_nome())
        try:
            bucket.upload(
                caminho_relativo,
                dados,
                file_options={"content-type": content_type, "x-upsert": "true"}
            )
        except Exception:
            bucket.update(
                caminho_relativo,
                dados,
                file_options={"content-type": content_type, "x-upsert": "true"}
            )
        return True
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def upload_arquivo_storage(caminho_relativo, dados, content_type=None, bucket_nome=None):
    client = obter_supabase_client()
    if not client or not caminho_relativo or dados is None:
        return False
    try:
        bucket = client.storage.from_(bucket_nome or supabase_bucket_nome())
        file_options = {
            "content-type": content_type or mimetypes.guess_type(str(caminho_relativo))[0] or "application/octet-stream",
            "x-upsert": "true",
        }
        try:
            bucket.upload(caminho_relativo, dados, file_options=file_options)
        except Exception:
            bucket.update(caminho_relativo, dados, file_options=file_options)
        return True
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def baixar_url_arquivo(caminho_relativo, bucket_nome=None, validade_segundos=3600):
    client = obter_supabase_client()
    if not client or not caminho_relativo:
        return ""
    try:
        resposta = client.storage.from_(bucket_nome or supabase_bucket_nome()).create_signed_url(
            caminho_relativo,
            validade_segundos
        )
        if isinstance(resposta, dict):
            return resposta.get("signedURL") or resposta.get("signedUrl") or resposta.get("signed_url") or ""
        return str(resposta or "")
    except Exception as erro:
        supabase_guardar_erro(erro)
        return ""


def excluir_arquivo_storage(caminho_relativo, bucket_nome=None):
    client = obter_supabase_client()
    if not client or not caminho_relativo:
        return False
    try:
        client.storage.from_(bucket_nome or supabase_bucket_nome()).remove([caminho_relativo])
        return True
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def listar_arquivos_storage(pasta="", bucket_nome=None):
    client = obter_supabase_client()
    if not client:
        return []
    try:
        return client.storage.from_(bucket_nome or supabase_bucket_nome()).list(pasta, {"limit": 1000, "offset": 0}) or []
    except Exception as erro:
        supabase_guardar_erro(erro)
        return []


def supabase_baixar_arquivo(caminho_local, caminho_relativo):
    client = obter_supabase_client()
    if not client:
        return False
    try:
        dados = client.storage.from_(supabase_bucket_nome()).download(caminho_relativo)
        os.makedirs(os.path.dirname(caminho_local), exist_ok=True)
        with open(caminho_local, "wb") as arquivo:
            arquivo.write(dados)
        return True
    except Exception as erro:
        supabase_guardar_erro(erro)
        return False


def sincronizar_supabase_inicio():
    client = obter_supabase_client()
    if not client:
        return
    bucket = client.storage.from_(supabase_bucket_nome())

    def percorrer(pasta=""):
        try:
            itens = bucket.list(pasta, {"limit": 1000, "offset": 0})
        except Exception as erro:
            supabase_guardar_erro(erro)
            return
        for item in itens or []:
            nome = item.get("name", "")
            if not nome:
                continue
            rel_item = f"{pasta}/{nome}".strip("/")
            if item.get("id") is None:
                os.makedirs(os.path.join(DATA_DIR, rel_item), exist_ok=True)
                percorrer(rel_item)
            else:
                supabase_baixar_arquivo(os.path.join(DATA_DIR, rel_item), rel_item)

    percorrer("")


def drive_guardar_erro(erro):
    try:
        if HttpError and isinstance(erro, HttpError):
            conteudo = erro.content.decode("utf-8", errors="ignore") if getattr(erro, "content", None) else str(erro)
            st.session_state["ultimo_erro_google_drive"] = conteudo[:700]
        else:
            st.session_state["ultimo_erro_google_drive"] = str(erro)[:700]
    except Exception:
        pass


def drive_listar_filhos(pasta_id):
    service = obter_google_service()
    if not service:
        return []
    itens = []
    token = None
    try:
        while True:
            resposta = service.files().list(
                q=f"'{pasta_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageToken=token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            itens.extend(resposta.get("files", []))
            token = resposta.get("nextPageToken")
            if not token:
                break
    except Exception as erro:
        drive_guardar_erro(erro)
    return itens


def drive_garantir_pasta(caminho_relativo):
    service = obter_google_service()
    pasta_raiz = obter_config_secreta("GOOGLE_DRIVE_FOLDER_ID", "")
    if not service or not pasta_raiz:
        return None
    if not caminho_relativo:
        return pasta_raiz
    if caminho_relativo in _drive_pastas_cache:
        return _drive_pastas_cache[caminho_relativo]

    pai = pasta_raiz
    partes = [p for p in caminho_relativo.replace("\\", "/").split("/") if p]
    caminho_atual = ""
    for parte in partes:
        caminho_atual = f"{caminho_atual}/{parte}".strip("/")
        if caminho_atual in _drive_pastas_cache:
            pai = _drive_pastas_cache[caminho_atual]
            continue
        existentes = [
            item for item in drive_listar_filhos(pai)
            if item["name"] == parte and item["mimeType"] == "application/vnd.google-apps.folder"
        ]
        if existentes:
            pai = existentes[0]["id"]
        else:
            criado = service.files().create(
                body={
                    "name": parte,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [pai]
                },
                fields="id",
                supportsAllDrives=True
            ).execute()
            pai = criado["id"]
        _drive_pastas_cache[caminho_atual] = pai
    return pai


def drive_encontrar_arquivo(caminho_relativo):
    if caminho_relativo in _drive_arquivos_cache:
        return _drive_arquivos_cache[caminho_relativo]
    pasta_rel = os.path.dirname(caminho_relativo).replace("\\", "/")
    nome = os.path.basename(caminho_relativo)
    pasta_id = drive_garantir_pasta(pasta_rel)
    if not pasta_id:
        return None
    for item in drive_listar_filhos(pasta_id):
        if item["name"] == nome and item["mimeType"] != "application/vnd.google-apps.folder":
            _drive_arquivos_cache[caminho_relativo] = item
            return item
    return None


def drive_baixar_arquivo(caminho_local, caminho_relativo):
    service = obter_google_service()
    item = drive_encontrar_arquivo(caminho_relativo)
    if not service or not item:
        return False
    os.makedirs(os.path.dirname(caminho_local), exist_ok=True)
    try:
        requisicao = service.files().get_media(fileId=item["id"], supportsAllDrives=True)
        with io.FileIO(caminho_local, "wb") as arquivo:
            downloader = MediaIoBaseDownload(arquivo, requisicao)
            concluido = False
            while not concluido:
                _, concluido = downloader.next_chunk()
        return True
    except Exception as erro:
        drive_guardar_erro(erro)
        return False


def drive_upload_arquivo(caminho_local):
    try:
        service = obter_google_service()
        if not service or not os.path.isfile(caminho_local):
            return False
        caminho_relativo = drive_relativo(caminho_local)
        pasta_rel = os.path.dirname(caminho_relativo).replace("\\", "/")
        pasta_id = drive_garantir_pasta(pasta_rel)
        if not pasta_id:
            return False
        media = MediaFileUpload(caminho_local, resumable=False)
        existente = drive_encontrar_arquivo(caminho_relativo)
        if existente:
            atualizado = service.files().update(
                fileId=existente["id"],
                media_body=media,
                fields="id, name, mimeType, modifiedTime",
                supportsAllDrives=True
            ).execute()
            _drive_arquivos_cache[caminho_relativo] = atualizado
        else:
            criado = service.files().create(
                body={"name": os.path.basename(caminho_local), "parents": [pasta_id]},
                media_body=media,
                fields="id, name, mimeType, modifiedTime",
                supportsAllDrives=True
            ).execute()
            _drive_arquivos_cache[caminho_relativo] = criado
        return True
    except Exception as erro:
        drive_guardar_erro(erro)
        return False


def sincronizar_drive_inicio():
    service = obter_google_service()
    pasta_raiz = obter_config_secreta("GOOGLE_DRIVE_FOLDER_ID", "")
    if not service or not pasta_raiz:
        return

    def percorrer(pasta_id, rel_pasta=""):
        for item in drive_listar_filhos(pasta_id):
            rel_item = f"{rel_pasta}/{item['name']}".strip("/")
            if item["mimeType"] == "application/vnd.google-apps.folder":
                _drive_pastas_cache[rel_item] = item["id"]
                os.makedirs(os.path.join(DATA_DIR, rel_item), exist_ok=True)
                percorrer(item["id"], rel_item)
            else:
                _drive_arquivos_cache[rel_item] = item
                drive_baixar_arquivo(os.path.join(DATA_DIR, rel_item), rel_item)

    percorrer(pasta_raiz)


def upload_arquivo_remoto(caminho_local):
    if supabase_configurado():
        return supabase_upload_arquivo(caminho_local)
    if ambiente_producao():
        return False
    return drive_upload_arquivo(caminho_local)


def sincronizar_armazenamento_inicio():
    if ambiente_producao():
        return
    if supabase_configurado():
        sincronizar_supabase_inicio()
    elif not ambiente_producao():
        sincronizar_drive_inicio()


if not hasattr(pd.DataFrame, "_alpes_to_excel_original"):
    pd.DataFrame._alpes_to_excel_original = pd.DataFrame.to_excel


def dataframe_to_excel_com_armazenamento(self, excel_writer, *args, **kwargs):
    if isinstance(excel_writer, (str, os.PathLike)):
        caminho_excel = os.path.abspath(os.fspath(excel_writer))
        if "bloquear_gravacao_sem_armazenamento" in globals():
            bloquear_gravacao_sem_armazenamento(caminho_excel)
        usuario_atual = st.session_state.get("usuario_logado", {})
        perfil_consulta = (
            globals().get("usuario_somente_consulta", lambda usuario: isinstance(usuario, dict) and usuario.get("nivel") == "Consulta")
        )
        if caminho_excel.startswith(os.path.abspath(DATA_DIR)) and perfil_consulta(usuario_atual):
            st.error("Perfil de consulta não pode alterar dados.")
            if "registrar_auditoria" in globals():
                registrar_auditoria("BLOQUEAR_ALTERACAO", "PERMISSÕES", os.path.basename(caminho_excel), os.path.basename(caminho_excel))
            return None
        if ambiente_producao() and arquivo_operacional(caminho_excel):
            if not supabase_salvar_dataframe(caminho_excel, self):
                erro = st.session_state.get("ultimo_erro_supabase", "")
                st.error(f"Erro ao salvar no Supabase. Nenhum dado foi gravado localmente. {erro}")
                st.stop()
            limpar_cache_dados()
            if "registrar_auditoria" in globals():
                registrar_auditoria("SALVAR_BANCO", "DADOS", os.path.basename(caminho_excel), os.path.basename(caminho_excel))
            return None
    resultado = pd.DataFrame._alpes_to_excel_original(self, excel_writer, *args, **kwargs)
    if isinstance(excel_writer, (str, os.PathLike)):
        caminho_excel = os.path.abspath(os.fspath(excel_writer))
        if caminho_excel.startswith(os.path.abspath(DATA_DIR)):
            try:
                supabase_salvar_dataframe(caminho_excel, self)
                upload_arquivo_remoto(caminho_excel)
                limpar_cache_dados()
            except Exception as erro:
                st.session_state["ultimo_erro_armazenamento"] = str(erro)[:1200]
            if "marcar_backup_pendente" in globals():
                marcar_backup_pendente(caminho_excel)
            if "registrar_auditoria" in globals():
                registrar_auditoria("SALVAR_ARQUIVO", "DADOS", os.path.basename(caminho_excel), os.path.basename(caminho_excel))
    return resultado


pd.DataFrame.to_excel = dataframe_to_excel_com_armazenamento


def caminho_dados(nome):
    destino = os.path.join(DATA_DIR, nome)
    origem = os.path.join(BASE_DIR, nome)
    if ambiente_producao():
        return destino
    if DATA_DIR != BASE_DIR and not os.path.exists(destino) and os.path.exists(origem):
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        if os.path.isdir(origem):
            shutil.copytree(origem, destino, dirs_exist_ok=True)
        else:
            shutil.copy2(origem, destino)
    return destino


PASTA_IMAGENS = caminho_dados("Imagens Produtos")
PASTA_IMAGENS_SISTEMA = caminho_dados("Imagens Sistema")
PRODUTOS_XLSX = caminho_dados("produtos.xlsx")
MOVIMENTACOES_XLSX = caminho_dados("movimentacoes.xlsx")
CLIENTES_XLSX = caminho_dados("clientes.xlsx")
FORNECEDORES_XLSX = caminho_dados("fornecedores.xlsx")
CONTROLE_FALTAS_XLSX = caminho_dados("controle_faltas.xlsx")
FROTAS_VEICULOS_XLSX = caminho_dados("frotas_veiculos.xlsx")
FROTAS_ABASTECIMENTOS_XLSX = caminho_dados("frotas_abastecimentos.xlsx")
FROTAS_MANUTENCOES_XLSX = caminho_dados("frotas_manutencoes.xlsx")
FROTAS_DOCUMENTOS_XLSX = caminho_dados("frotas_documentos.xlsx")
FROTAS_ENTREGAS_XLSX = caminho_dados("frotas_entregas.xlsx")
FROTAS_VISTORIAS_XLSX = caminho_dados("frotas_vistorias.xlsx")
BASES_MOVIMENTACOES_XLSX = caminho_dados("bases_movimentacoes.xlsx")
BASES_TRANSFERENCIAS_XLSX = caminho_dados("bases_transferencias.xlsx")
PASTA_ANEXOS_FROTAS = caminho_dados("Anexos Frotas")
USUARIOS_JSON = caminho_dados("usuarios.json")
AUDITORIA_JSON = caminho_dados("auditoria.json")
CONFIG_JSON = caminho_dados("configuracoes.json")
CATEGORIAS_JSON = caminho_dados("categorias.json")
UNIDADES_JSON = caminho_dados("unidades.json")
BACKUP_DIR = caminho_dados("backups")
HOME_IMAGE = os.path.join(PASTA_IMAGENS_SISTEMA, "inicio.jpg")
LOGIN_IMAGE = os.path.join(PASTA_IMAGENS_SISTEMA, "login.jpg")
LOGIN_LOGO_IMAGE = os.path.join(PASTA_IMAGENS_SISTEMA, "logo_alpes_horizontal_negativo.png")
HOME_IMAGE_FALLBACK = os.path.join(BASE_DIR, "Desktop 1.jpg")
BASES_FREQUENCIA = ["TMG BASE SORRISO", "TMG BASE RONDONOPOLIS"]
validar_supabase_producao()
sincronizar_armazenamento_inicio()
migrar_dados_existentes_para_supabase()


# =========================
# FUNCOES DE ARQUIVO
# =========================
def carregar_json(caminho, padrao):
    dados_supabase = supabase_ler_json(caminho, padrao)
    if dados_supabase is not None:
        return dados_supabase
    if arquivo_operacional(caminho) and not fonte_local_permitida_para_dados():
        return padrao
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                return json.load(arquivo)
        except Exception:
            return padrao
    return padrao


def salvar_json(caminho, dados):
    bloquear_gravacao_sem_armazenamento(caminho)
    if ambiente_producao() and arquivo_operacional(caminho):
        if not supabase_salvar_json(caminho, dados):
            erro = st.session_state.get("ultimo_erro_supabase", "")
            st.error(f"Erro ao salvar no Supabase. Nenhum dado foi gravado localmente. {erro}")
            st.stop()
        limpar_cache_dados()
        return
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)
    supabase_salvar_json(caminho, dados)
    limpar_cache_dados()
    upload_arquivo_remoto(caminho)
    marcar_backup_pendente(caminho)


def registrar_erro_leitura(caminho, erro):
    try:
        mensagem = f"{os.path.basename(str(caminho))}: {type(erro).__name__}: {erro}"
        erros = st.session_state.setdefault("erros_leitura_dados", [])
        if mensagem not in erros:
            erros.append(mensagem[:700])
    except Exception:
        pass


def carregar_dataframe(caminho, colunas):
    dados_supabase = supabase_ler_dataframe(caminho, colunas)
    if dados_supabase is not None:
        return dados_supabase
    if arquivo_operacional(caminho) and not fonte_local_permitida_para_dados():
        return pd.DataFrame(columns=colunas)
    if os.path.exists(caminho):
        try:
            return pd.read_excel(caminho)
        except Exception as erro:
            registrar_erro_leitura(caminho, erro)
    return pd.DataFrame(columns=colunas)


def limpar_cache_dados():
    try:
        st.cache_data.clear()
    except Exception:
        pass


def registrar_auditoria(acao, modulo="", detalhe="", registro="", antes=None, depois=None):
    try:
        usuario = st.session_state.get("usuario_logado", {})
    except Exception:
        usuario = {}
    item = {
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "usuario": usuario.get("nome", "sistema") if isinstance(usuario, dict) else "sistema",
        "nivel": usuario.get("nivel", "") if isinstance(usuario, dict) else "",
        "acao": str(acao),
        "modulo": str(modulo),
        "registro": str(registro),
        "detalhe": str(detalhe),
        "antes": json.dumps(antes, ensure_ascii=False, default=str)[:1200] if antes is not None else "",
        "depois": json.dumps(depois, ensure_ascii=False, default=str)[:1200] if depois is not None else "",
    }
    historico = carregar_json(AUDITORIA_JSON, [])
    if not isinstance(historico, list):
        historico = []
    historico.append(item)
    historico = historico[-5000:]
    if ambiente_producao():
        supabase_salvar_json(AUDITORIA_JSON, historico)
        return
    with open(AUDITORIA_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(historico, arquivo, ensure_ascii=False, indent=4)
    supabase_salvar_json(AUDITORIA_JSON, historico)
    upload_arquivo_remoto(AUDITORIA_JSON)


def salvar_config_sem_marcar_backup():
    if ambiente_producao():
        supabase_salvar_json(CONFIG_JSON, config)
        return
    with open(CONFIG_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(config, arquivo, ensure_ascii=False, indent=4)
    supabase_salvar_json(CONFIG_JSON, config)
    upload_arquivo_remoto(CONFIG_JSON)


def detectar_pasta_backup_nuvem():
    candidatos = [
        os.environ.get("BACKUP_NUVEM_PATH", ""),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Backups Sistema Alpes"),
        os.path.join(os.path.expanduser("~"), "OneDrive"),
        os.environ.get("GOOGLE_DRIVE_PATH", ""),
        os.path.join(os.path.expanduser("~"), "Google Drive"),
        os.path.join(os.path.expanduser("~"), "My Drive"),
        os.path.join(os.path.expanduser("~"), "Meu Drive"),
        os.path.join(os.path.expanduser("~"), "GoogleDrive"),
        r"G:\Meu Drive",
        r"G:\My Drive",
        r"G:\\",
    ]
    for candidato in candidatos:
        if candidato and os.path.isdir(candidato):
            if os.path.basename(candidato).lower() == "backups sistema alpes":
                return candidato
            return os.path.join(candidato, "Backups Sistema Alpes")
    return ""


def obter_pasta_backup_nuvem():
    pasta_config = str(config.get("backup_google_drive_pasta", "")).strip()
    if pasta_config:
        return pasta_config
    return detectar_pasta_backup_nuvem()


def copiar_backup_nuvem(zip_path):
    if not config.get("backup_google_drive_ativo", True):
        return ""
    pasta_drive = obter_pasta_backup_nuvem()
    if not pasta_drive:
        st.session_state["ultimo_erro_backup_google_drive"] = "OneDrive/Google Drive nao encontrado. Informe a pasta de backup em nuvem na aba Backup."
        return ""
    try:
        os.makedirs(pasta_drive, exist_ok=True)
        destino = os.path.join(pasta_drive, os.path.basename(zip_path))
        shutil.copy2(zip_path, destino)
        config["backup_google_drive_pasta"] = pasta_drive
        config["ultimo_backup_google_drive"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        st.session_state.pop("ultimo_erro_backup_google_drive", None)
        return destino
    except Exception as erro:
        st.session_state["ultimo_erro_backup_google_drive"] = str(erro)[:500]
        return ""


def backup_local_mais_recente():
    if not os.path.isdir(BACKUP_DIR):
        return ""
    arquivos = [
        os.path.join(BACKUP_DIR, nome)
        for nome in os.listdir(BACKUP_DIR)
        if nome.lower().endswith(".zip") and os.path.isfile(os.path.join(BACKUP_DIR, nome))
    ]
    if not arquivos:
        return ""
    return max(arquivos, key=os.path.getmtime)


def backup_nuvem_mais_recente():
    pasta_nuvem = obter_pasta_backup_nuvem()
    if not pasta_nuvem or not os.path.isdir(pasta_nuvem):
        return ""
    arquivos = [
        os.path.join(pasta_nuvem, nome)
        for nome in os.listdir(pasta_nuvem)
        if nome.lower().endswith(".zip") and os.path.isfile(os.path.join(pasta_nuvem, nome))
    ]
    if not arquivos:
        return ""
    return max(arquivos, key=os.path.getmtime)


def arquivos_permitidos_backup():
    return [
        "produtos.xlsx", "movimentacoes.xlsx", "clientes.xlsx", "fornecedores.xlsx",
        "controle_faltas.xlsx", "frotas_veiculos.xlsx", "frotas_abastecimentos.xlsx",
        "frotas_manutencoes.xlsx", "frotas_documentos.xlsx", "frotas_entregas.xlsx", "frotas_vistorias.xlsx",
        "bases_movimentacoes.xlsx", "bases_transferencias.xlsx",
        "usuarios.json", "auditoria.json", "configuracoes.json", "categorias.json", "unidades.json"
    ]


def pastas_permitidas_backup():
    return [
        "Imagens Produtos",
        "Imagens Sistema",
        "Anexos Frotas",
    ]


def arquivo_raiz_permitido_backup(nome):
    extensoes = {".xlsx", ".xlsm", ".json", ".png", ".jpg", ".jpeg", ".pdf"}
    return os.path.splitext(nome)[1].lower() in extensoes


def gerar_backup_incremental(caminho_alterado):
    if ambiente_producao():
        return ""
    caminho_origem = os.path.abspath(os.fspath(caminho_alterado or ""))
    data_dir_abs = os.path.abspath(DATA_DIR)
    if not caminho_origem or not os.path.exists(caminho_origem):
        return ""
    if os.path.commonpath([data_dir_abs, caminho_origem]) != data_dir_abs:
        return ""
    if os.path.abspath(caminho_origem).startswith(os.path.abspath(BACKUP_DIR)):
        return ""
    nome_arquivo = os.path.basename(caminho_origem)
    if nome_arquivo not in arquivos_permitidos_backup() and not arquivo_raiz_permitido_backup(nome_arquivo):
        return ""

    pasta_incremental = os.path.join(BACKUP_DIR, "incremental", datetime.now().strftime("%Y%m%d"))
    os.makedirs(pasta_incremental, exist_ok=True)
    nome_base, extensao = os.path.splitext(nome_arquivo)
    carimbo = datetime.now().strftime("%H%M%S_%f")[:-3]
    destino = os.path.join(pasta_incremental, f"{nome_base}_{carimbo}{extensao}")
    shutil.copy2(caminho_origem, destino)

    try:
        upload_arquivo_remoto(destino)
    except Exception as erro:
        st.session_state["erro_backup_incremental"] = str(erro)[:700]
    else:
        st.session_state.pop("erro_backup_incremental", None)

    st.session_state["ultimo_backup_incremental"] = destino
    return destino


def restaurar_backup_zip(caminho_zip):
    if ambiente_producao():
        st.error("Restauração por arquivo local não é permitida em produção. Use restauração controlada no Supabase.")
        st.stop()
    ignorar_pastas_restore = {"backups", "__pycache__", ".git", ".venv", "venv"}
    with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
        for nome in zip_ref.namelist():
            partes = [parte for parte in nome.replace("\\", "/").split("/") if parte]
            if not partes:
                continue
            if partes[0] in ignorar_pastas_restore or any(parte in {"..", ""} for parte in partes):
                continue
            destino = os.path.abspath(os.path.join(DATA_DIR, *partes))
            data_dir_abs = os.path.abspath(DATA_DIR)
            if os.path.commonpath([data_dir_abs, destino]) != data_dir_abs:
                continue
            if nome.endswith("/"):
                os.makedirs(destino, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with zip_ref.open(nome) as origem, open(destino, "wb") as arquivo_destino:
                shutil.copyfileobj(origem, arquivo_destino)


def marcar_backup_pendente(caminho=""):
    if "config" not in globals():
        return
    if ambiente_producao():
        config["alteracao_pendente_backup"] = False
        config["ultima_alteracao"] = ""
        salvar_config_sem_marcar_backup()
        return
    caminho_nome = os.path.basename(str(caminho or ""))
    if caminho_nome == os.path.basename(CONFIG_JSON) and st.session_state.get("salvando_backup"):
        return
    config["alteracao_pendente_backup"] = True
    config["ultima_alteracao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    salvar_config_sem_marcar_backup()

    if (
        config.get("backup_incremental_alteracao", True)
        and caminho
        and "gerar_backup_incremental" in globals()
        and not st.session_state.get("backup_incremental_em_execucao")
        and not st.session_state.get("salvando_backup")
    ):
        st.session_state["backup_incremental_em_execucao"] = True
        try:
            caminho_incremental = gerar_backup_incremental(caminho)
            if caminho_incremental and "registrar_auditoria" in globals():
                registrar_auditoria("BACKUP_INCREMENTAL", "BACKUP", caminho_incremental, os.path.basename(caminho_incremental))
        except Exception as erro:
            st.session_state["erro_backup_incremental"] = str(erro)[:700]
        finally:
            st.session_state.pop("backup_incremental_em_execucao", None)

    if (
        config.get("backup_completo_alteracao", False)
        and "gerar_backup" in globals()
        and not st.session_state.get("backup_automatico_em_execucao")
        and not st.session_state.get("salvando_backup")
    ):
        st.session_state["backup_automatico_em_execucao"] = True
        try:
            caminho_backup = gerar_backup()
            st.session_state["ultimo_backup_automatico_alteracao"] = caminho_backup
            st.session_state.pop("erro_backup_automatico_alteracao", None)
            if "registrar_auditoria" in globals():
                registrar_auditoria("BACKUP_ALTERACAO", "BACKUP", caminho_backup, os.path.basename(caminho_backup))
        except Exception as erro:
            st.session_state["erro_backup_automatico_alteracao"] = str(erro)[:700]
        finally:
            st.session_state.pop("backup_automatico_em_execucao", None)


def garantir_pasta_imagens_sistema():
    if ambiente_producao():
        return
    os.makedirs(PASTA_IMAGENS, exist_ok=True)
    os.makedirs(PASTA_IMAGENS_SISTEMA, exist_ok=True)
    os.makedirs(PASTA_ANEXOS_FROTAS, exist_ok=True)
    if not os.path.exists(HOME_IMAGE) and os.path.exists(HOME_IMAGE_FALLBACK):
        shutil.copy2(HOME_IMAGE_FALLBACK, HOME_IMAGE)
    if not os.path.exists(LOGIN_IMAGE) and os.path.exists(HOME_IMAGE):
        shutil.copy2(HOME_IMAGE, LOGIN_IMAGE)


def hash_senha(senha):
    salt = secrets.token_hex(16)
    iteracoes = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", str(senha).encode("utf-8"), salt.encode("utf-8"), iteracoes).hex()
    return f"pbkdf2_sha256${iteracoes}${salt}${digest}"


def verificar_senha(senha, senha_armazenada):
    senha_armazenada = str(senha_armazenada or "")
    if senha_armazenada.startswith("pbkdf2_sha256$"):
        try:
            _, iteracoes, salt, digest_salvo = senha_armazenada.split("$", 3)
            digest = hashlib.pbkdf2_hmac("sha256", str(senha).encode("utf-8"), salt.encode("utf-8"), int(iteracoes)).hex()
            return secrets.compare_digest(digest, digest_salvo)
        except Exception:
            return False
    return secrets.compare_digest(senha_armazenada, hashlib.sha256(str(senha).encode("utf-8")).hexdigest())


def imagem_base64(caminho):
    with open(caminho, "rb") as arquivo:
        return base64.b64encode(arquivo.read()).decode("utf-8")


def garantir_usuario_admin():
    usuarios = carregar_json(USUARIOS_JSON, [])
    if not usuarios:
        if ambiente_producao():
            admin_nome = obter_config_secreta("ALPES_ADMIN_USER", "").strip()
            admin_email = obter_config_secreta("ALPES_ADMIN_EMAIL", admin_nome).strip()
            admin_senha = obter_config_secreta("ALPES_ADMIN_PASSWORD", "").strip()
            if not admin_nome or not admin_senha or admin_senha == "123":
                st.error("Erro crítico: usuário administrador inicial não configurado para produção.")
                st.info("Configure ALPES_ADMIN_USER e ALPES_ADMIN_PASSWORD nos Secrets. Não use a senha padrão 123.")
                st.stop()
            usuarios = [{
                "nome": admin_nome,
                "email": admin_email or admin_nome,
                "senha": hash_senha(admin_senha),
                "nivel": "Administrador",
                "status": "Ativo",
                "trocar_senha": True,
                "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
            }]
            salvar_json(USUARIOS_JSON, usuarios)
            return usuarios
        usuarios = [{
            "nome": "admin",
            "email": "admin",
            "senha": hash_senha("123"),
            "nivel": "Administrador",
            "status": "Ativo",
            "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
        }]
        salvar_json(USUARIOS_JSON, usuarios)
    return usuarios


def configuracao_padrao():
    return {
        "empresa": "",
        "email": "",
        "telefone": "",
        "endereco": "",
        "logo": "",
        "estoque_minimo_padrao": 1,
        "alerta_estoque": True,
        "permitir_negativo": False,
        "tema": "dark",
        "cor_principal": "#6157ff",
        "fonte": "Inter",
        "ultimo_backup": "Nunca",
        "backup_automatico_diario": True,
        "backup_automatico_alteracao": True,
        "backup_incremental_alteracao": True,
        "backup_completo_alteracao": False,
        "backup_google_drive_ativo": True,
        "backup_google_drive_pasta": "",
        "ultimo_backup_google_drive": "Nunca",
        "alteracao_pendente_backup": False,
        "ultima_alteracao": "",
        "supervisores_frequencia": {
            "TMG BASE SORRISO": "",
            "TMG BASE RONDONOPOLIS": ""
        }
    }


def categorias_padrao():
    return [
        {"nome": "MANUTENÇÃO", "cor": "#facc15"},
        {"nome": "ELÉTRICA", "cor": "#fb923c"},
        {"nome": "HIDRÁULICA", "cor": "#38bdf8"},
        {"nome": "LIMPEZA", "cor": "#22c55e"},
        {"nome": "COPA", "cor": "#a78bfa"},
        {"nome": "JARDINAGEM", "cor": "#4ade80"}
    ]


def unidades_padrao():
    return [
        {"nome": "UN", "cor": "#38bdf8"},
        {"nome": "CX", "cor": "#a78bfa"},
        {"nome": "KG", "cor": "#22c55e"},
        {"nome": "LT", "cor": "#facc15"},
        {"nome": "M", "cor": "#fb923c"}
    ]


usuarios = garantir_usuario_admin()
config = carregar_json(CONFIG_JSON, configuracao_padrao())
if "supervisores_frequencia" not in config or not isinstance(config.get("supervisores_frequencia"), dict):
    config["supervisores_frequencia"] = {}
for chave_config, valor_config in configuracao_padrao().items():
    config.setdefault(chave_config, valor_config)
for base_frequencia in BASES_FREQUENCIA:
    config["supervisores_frequencia"].setdefault(base_frequencia, "")
categorias_config = carregar_json(CATEGORIAS_JSON, categorias_padrao())
unidades_config = carregar_json(UNIDADES_JSON, unidades_padrao())
garantir_pasta_imagens_sistema()


# =========================
# ESTILO VISUAL
# =========================
cor_principal = "#0B1F3A"
cor_destaque = "#F97316"
fonte = config.get("fonte", "Inter")
fundo_app = "#F3F4F6"
fundo_card = "#FFFFFF"
borda_card = "#E5E7EB"
texto_app = "#0F172A"
texto_suave = "#64748B"

st.markdown(f"""
<style>
    :root {{
        --alpes-navy: #0B1F3A;
        --alpes-orange: #F97316;
        --alpes-white: #FFFFFF;
        --alpes-bg: #F3F4F6;
        --alpes-success: #22C55E;
        --alpes-danger: #EF4444;
        --alpes-warning: #FACC15;
        --alpes-text: #0F172A;
        --alpes-muted: #64748B;
        --alpes-border: #E5E7EB;
        --alpes-shadow: 0 18px 45px rgba(11, 31, 58, .10);
    }}
    html, body, [class*="css"] {{
        font-family: '{fonte}', "Segoe UI", Arial, sans-serif;
        letter-spacing: 0 !important;
    }}
    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(249, 115, 22, .10), transparent 28rem),
            linear-gradient(180deg, #FFFFFF 0%, {fundo_app} 34%, #EEF2F7 100%);
        color: {texto_app};
    }}
    [data-testid="stMainBlockContainer"] {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1440px;
    }}
    #MainMenu,
    header,
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stAppDeployButton"],
    footer {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }}
    [data-testid="stException"],
    [data-testid="stException"] * {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: var(--alpes-navy) !important;
        letter-spacing: 0 !important;
        font-weight: 800 !important;
    }}
    h1 {{
        font-size: 2.35rem !important;
        line-height: 1.12 !important;
        margin-bottom: 1.1rem !important;
    }}
    h2, h3 {{
        margin-top: 1.2rem !important;
    }}
    p, label, legend,
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stCaptionContainer"] {{
        color: {texto_app};
    }}
    [data-testid="stCaptionContainer"] {{
        color: {texto_suave};
    }}
    .saas-card, .metric-card, div[data-testid="stExpander"] {{
        background: rgba(255, 255, 255, .94);
        border: 1px solid {borda_card};
        border-radius: 8px;
        box-shadow: var(--alpes-shadow);
        backdrop-filter: blur(10px);
    }}
    .saas-card {{
        padding: 24px;
    }}
    .metric-card {{
        position: relative;
        overflow: hidden;
        padding: 20px;
        min-height: 118px;
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }}
    .metric-card::before {{
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 4px;
        background: linear-gradient(180deg, var(--alpes-orange), var(--alpes-navy));
    }}
    .metric-card:hover {{
        transform: translateY(-3px);
        border-color: rgba(249, 115, 22, .38);
        box-shadow: 0 22px 55px rgba(11, 31, 58, .14);
    }}
    .metric-label {{
        color: {texto_suave};
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 9px;
    }}
    .metric-value {{
        color: var(--alpes-navy);
        font-size: 30px;
        line-height: 1.08;
        font-weight: 850;
        text-transform: none;
    }}
    .status-pill, .stock-pill, .category-pill {{
        border-radius: 999px;
        padding: 7px 11px;
        font-size: 12px;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        min-height: 28px;
        border: 1px solid transparent;
        white-space: nowrap;
    }}
    .status-pill {{
        width: 100%;
        color: #DCFCE7;
        background: rgba(34, 197, 94, .16);
        border-color: rgba(34, 197, 94, .34);
    }}
    .status-pill.warning {{
        color: #FEF3C7;
        background: rgba(249, 115, 22, .18);
        border-color: rgba(249, 115, 22, .34);
    }}
    .stock-ok {{
        color: #166534;
        background: #DCFCE7;
        border-color: #BBF7D0;
    }}
    .stock-low {{
        color: #991B1B;
        background: #FEE2E2;
        border-color: #FECACA;
    }}
    .stock-critical {{
        color: #7F1D1D;
        background: #FECACA;
        border-color: #FCA5A5;
    }}
    .category-pill {{
        color: var(--pill-color, var(--alpes-navy));
        background: color-mix(in srgb, var(--pill-color, var(--alpes-navy)) 13%, white);
        border-color: color-mix(in srgb, var(--pill-color, var(--alpes-navy)) 30%, white);
    }}
    .login-img {{
        width: 100%;
        max-height: 150px;
        object-fit: contain;
        object-position: center;
        display: block;
        margin: 0 auto 18px auto;
    }}
    .login-brand {{
        text-align: center;
        margin-bottom: 18px;
    }}
    .login-brand-title {{
        color: var(--alpes-navy);
        font-size: 1.65rem;
        font-weight: 900;
    }}
    .login-brand-subtitle {{
        color: var(--alpes-muted);
        font-size: .92rem;
        margin-top: 4px;
    }}
    .login-shell-marker {{
        display: none;
    }}
    .home-hero {{
        position: relative;
        overflow: hidden;
        border-radius: 8px;
        min-height: 250px;
        padding: 30px;
        background:
            linear-gradient(110deg, rgba(11, 31, 58, .92), rgba(11, 31, 58, .62)),
            var(--home-image, linear-gradient(135deg, #0B1F3A, #102F54));
        background-size: cover;
        background-position: center;
        box-shadow: 0 24px 70px rgba(11, 31, 58, .22);
        margin-bottom: 20px;
    }}
    .home-hero h1 {{
        color: #FFFFFF !important;
        margin: 0 0 10px 0 !important;
        font-size: 2.35rem !important;
    }}
    .home-hero p {{
        color: rgba(255,255,255,.82);
        max-width: 760px;
        font-size: 1rem;
    }}
    .home-hero-badges {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 22px;
    }}
    .home-hero-badges span {{
        color: #FFFFFF;
        border: 1px solid rgba(255,255,255,.22);
        background: rgba(255,255,255,.10);
        border-radius: 999px;
        padding: 7px 12px;
        font-size: 12px;
        font-weight: 800;
    }}
    .stock-table-header, .stock-row {{
        display: grid;
        grid-template-columns: .9fr 2fr 1.45fr .9fr .9fr 1.35fr 1.15fr 1.35fr;
        gap: 12px;
        align-items: center;
    }}
    .stock-table-header {{
        color: var(--alpes-muted);
        font-size: 12px;
        font-weight: 900;
        text-transform: uppercase;
        padding: 0 12px 8px 12px;
    }}
    .stock-row {{
        background: #FFFFFF;
        border: 1px solid var(--alpes-border);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 10px 28px rgba(11, 31, 58, .07);
        transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease;
    }}
    .stock-row:hover {{
        transform: translateY(-2px);
        border-color: rgba(249, 115, 22, .35);
        box-shadow: 0 16px 38px rgba(11, 31, 58, .12);
    }}
    .stock-img {{
        width: 100%;
        max-height: 86px;
        object-fit: contain;
        border-radius: 8px;
        background: #F8FAFC;
        border: 1px solid #E5E7EB;
    }}
    .muted {{
        color: var(--alpes-muted);
        font-size: 12px;
    }}
    [data-testid="stSidebar"] {{
        background:
            linear-gradient(180deg, #0B1F3A 0%, #071426 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, .08);
        box-shadow: 18px 0 42px rgba(11, 31, 58, .22);
    }}
    [data-testid="stSidebar"] * {{
        color: rgba(255,255,255,.88);
    }}
    [data-testid="stSidebar"] h1 {{
        color: #FFFFFF !important;
        font-size: 1.1rem !important;
        letter-spacing: .04em !important;
        margin-bottom: .6rem !important;
    }}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
        color: rgba(255,255,255,.60) !important;
        font-size: 12px;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        border-radius: 8px;
        padding: 10px 12px;
        margin: 5px 0;
        border: 1px solid transparent;
        background: transparent;
        transition: background .16s ease, border-color .16s ease, transform .16s ease;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(255, 255, 255, .08);
        border-color: rgba(255, 255, 255, .12);
        transform: translateX(2px);
    }}
    .stButton > button, .stDownloadButton button, button[kind="primary"], button[kind="secondary"] {{
        min-height: 42px;
        border-radius: 14px !important;
        border: 1px solid rgba(242, 140, 40, .26) !important;
        background: linear-gradient(135deg, rgba(242, 140, 40, .96), rgba(249, 115, 22, .82)) !important;
        color: #FFFFFF !important;
        box-shadow: 0 18px 42px rgba(242, 140, 40, .18), inset 0 1px 0 rgba(255,255,255,.18) !important;
        font-weight: 800 !important;
        transition: transform .14s ease, filter .14s ease, box-shadow .14s ease;
    }}
    .stButton > button:hover, .stDownloadButton button:hover, button[kind="primary"]:hover, button[kind="secondary"]:hover {{
        transform: translateY(-1px);
        filter: brightness(1.04);
        box-shadow: 0 22px 54px rgba(242, 140, 40, .24), 0 0 30px rgba(242, 140, 40, .12) !important;
    }}
    .stButton > button:active, .stDownloadButton button:active, button[kind="primary"]:active, button[kind="secondary"]:active {{
        transform: translateY(1px);
    }}
    .stButton > button p,
    .stDownloadButton button p,
    button[kind="primary"] p,
    button[kind="secondary"] p {{
        color: #FFFFFF !important;
    }}
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {{
        background: rgba(8, 21, 46, .72) !important;
        border: 1px solid rgba(148, 163, 184, .24) !important;
        border-radius: 14px !important;
        color: #F8FAFC !important;
        min-height: 42px;
        transition: border-color .15s ease, box-shadow .15s ease;
    }}
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span,
    textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {{
        color: #F8FAFC !important;
    }}
    div[data-baseweb="input"] input::placeholder,
    textarea::placeholder,
    [data-testid="stTextInput"] input::placeholder {{
        color: rgba(226,232,240,.48) !important;
    }}
    div[data-baseweb="input"]:focus-within > div,
    div[data-baseweb="select"]:focus-within > div,
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus,
    textarea:focus {{
        border-color: rgba(242, 140, 40, .72) !important;
        box-shadow: 0 0 0 3px rgba(242, 140, 40, .16), 0 16px 40px rgba(2,8,23,.22) !important;
    }}
    [data-testid="stRadio"] [role="radiogroup"] {{
        gap: 10px;
    }}
    [data-testid="stRadio"] label {{
        padding: 10px 14px !important;
        border-radius: 999px !important;
        border: 1px solid rgba(148, 163, 184, .22) !important;
        background: rgba(8, 21, 46, .62) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
        transition: all .16s ease;
    }}
    [data-testid="stRadio"] label:hover {{
        border-color: rgba(242, 140, 40, .42) !important;
        background: rgba(242, 140, 40, .12) !important;
        box-shadow: 0 14px 38px rgba(242, 140, 40, .10);
        transform: translateY(-1px);
    }}
    [data-testid="stRadio"] label p,
    [data-testid="stCheckbox"] label p {{
        color: #F8FAFC !important;
        font-weight: 800 !important;
    }}
    [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child,
    [data-testid="stCheckbox"] label > div:first-child {{
        border-color: rgba(248,250,252,.72) !important;
        background: rgba(255,255,255,.08) !important;
    }}
    [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked),
    [data-testid="stCheckbox"] label:has(input:checked) {{
        border-color: rgba(242, 140, 40, .62) !important;
        background: rgba(242, 140, 40, .16) !important;
        box-shadow: 0 0 28px rgba(242, 140, 40, .12);
    }}
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {{
        border: 1px solid var(--alpes-border);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 14px 34px rgba(11, 31, 58, .08);
        background: #FFFFFF;
    }}
    [data-testid="stAlert"] {{
        border-radius: 8px;
        border: 1px solid rgba(11, 31, 58, .10);
        box-shadow: 0 12px 28px rgba(11, 31, 58, .08);
    }}
    div[data-testid="stExpander"] {{
        overflow: hidden;
    }}
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stDownloadButton button {{
        width: 100%;
        background: rgba(255,255,255,.10) !important;
        border-color: rgba(255,255,255,.18) !important;
        box-shadow: none !important;
    }}
    .stApp {{
        background:
            radial-gradient(circle at 8% 8%, rgba(242, 140, 40, .16), transparent 24rem),
            radial-gradient(circle at 92% 14%, rgba(56, 189, 248, .14), transparent 25rem),
            linear-gradient(135deg, #061C3F 0%, #08152E 46%, #050D1F 100%) !important;
        color: rgba(248, 250, 252, .92);
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px),
            linear-gradient(0deg, rgba(255,255,255,.026) 1px, transparent 1px),
            radial-gradient(circle at 65% 38%, rgba(124, 58, 237, .12), transparent 24rem);
        background-size: 88px 88px, 88px 88px, auto;
        mask-image: linear-gradient(120deg, rgba(0,0,0,.86), transparent 78%);
        z-index: 0;
    }}
    [data-testid="stMainBlockContainer"] {{
        position: relative;
        z-index: 1;
        padding-top: 0 !important;
        max-width: 1480px;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: #F8FAFC !important;
    }}
    p, label, legend,
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stCaptionContainer"] {{
        color: rgba(226,232,240,.88);
    }}
    .saas-card, .metric-card, div[data-testid="stExpander"] {{
        background: linear-gradient(145deg, rgba(8, 21, 46, .74), rgba(5, 13, 31, .56)) !important;
        border: 1px solid rgba(148, 163, 184, .20) !important;
        border-radius: 18px !important;
        box-shadow: 0 28px 80px rgba(2, 8, 23, .35), inset 0 1px 0 rgba(255,255,255,.08) !important;
        backdrop-filter: blur(18px);
    }}
    .metric-card {{
        min-height: 132px;
        border-radius: 20px !important;
    }}
    .metric-card::before {{
        width: 3px;
        background: linear-gradient(180deg, #F28C28, #38BDF8);
        box-shadow: 0 0 26px rgba(242, 140, 40, .55);
    }}
    .metric-label {{
        color: rgba(186, 199, 217, .86) !important;
    }}
    .metric-value {{
        color: #F8FAFC !important;
    }}
    [data-testid="stSidebar"] {{
        background:
            radial-gradient(circle at top, rgba(242, 140, 40, .13), transparent 18rem),
            linear-gradient(180deg, rgba(6, 28, 63, .96) 0%, rgba(5, 13, 31, .98) 100%) !important;
        border-right: 1px solid rgba(148, 163, 184, .18);
        box-shadow: 24px 0 80px rgba(2, 8, 23, .42);
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        border-radius: 14px;
        padding: 12px 13px;
        margin: 6px 0;
        border: 1px solid rgba(255,255,255,.04);
        background: rgba(255,255,255,.035);
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(242, 140, 40, .12);
        border-color: rgba(242, 140, 40, .35);
        box-shadow: 0 10px 30px rgba(242, 140, 40, .12);
        transform: translateX(4px);
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] {{
        transition: all .18s ease;
    }}
    .status-pill {{
        background: rgba(34, 197, 94, .14);
        border-color: rgba(34, 197, 94, .34);
        box-shadow: 0 0 28px rgba(34, 197, 94, .14);
    }}
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {{
        background: rgba(5, 13, 31, .64) !important;
        border: 1px solid rgba(148, 163, 184, .18) !important;
        border-radius: 18px !important;
        box-shadow: 0 28px 80px rgba(2, 8, 23, .32) !important;
    }}
    .alpes-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        padding: 14px 18px;
        margin: 0 -1rem 22px -1rem;
        min-height: 76px;
        border-bottom: 1px solid rgba(148, 163, 184, .15);
        background: rgba(5, 13, 31, .34);
        box-shadow: 0 22px 70px rgba(2, 8, 23, .18);
        backdrop-filter: blur(18px);
    }}
    .alpes-search {{
        flex: 1;
        max-width: 520px;
        min-height: 44px;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0 14px;
        border-radius: 16px;
        background: rgba(255,255,255,.07);
        border: 1px solid rgba(148, 163, 184, .17);
        color: rgba(226,232,240,.72);
        font-weight: 700;
    }}
    .alpes-kbd {{
        margin-left: auto;
        color: rgba(255,255,255,.78);
        border: 1px solid rgba(255,255,255,.18);
        border-radius: 9px;
        padding: 3px 8px;
        background: rgba(255,255,255,.06);
        font-size: .72rem;
    }}
    .topbar-right {{
        display: flex;
        align-items: center;
        gap: 11px;
        white-space: nowrap;
    }}
    .top-icon, .user-avatar {{
        width: 38px;
        height: 38px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        background: rgba(255,255,255,.07);
        border: 1px solid rgba(255,255,255,.12);
    }}
    .user-avatar {{
        background: linear-gradient(135deg, #F28C28, #FB923C);
        color: #FFFFFF;
        font-weight: 900;
        box-shadow: 0 14px 36px rgba(242, 140, 40, .25);
    }}
    .user-meta strong {{
        display: block;
        color: #FFFFFF;
        font-size: .86rem;
        line-height: 1.1;
    }}
    .user-meta span {{
        color: rgba(226,232,240,.58);
        font-size: .72rem;
    }}
    .premium-hero {{
        position: relative;
        overflow: hidden;
        display: grid;
        grid-template-columns: 1.35fr .65fr;
        gap: 20px;
        min-height: 238px;
        padding: 34px;
        border-radius: 12px 28px 12px 12px;
        border: 1px solid rgba(96, 165, 250, .24);
        background:
            linear-gradient(120deg, rgba(6, 28, 63, .82), rgba(8, 21, 46, .52)),
            var(--home-image, linear-gradient(135deg, #061C3F, #050D1F));
        background-size: cover;
        background-position: center;
        box-shadow: 0 36px 110px rgba(2, 8, 23, .42), inset 0 1px 0 rgba(255,255,255,.10);
        backdrop-filter: blur(20px);
        margin-bottom: 18px;
    }}
    .premium-hero::after {{
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(115deg, transparent 0%, rgba(56, 189, 248, .12) 52%, transparent 53%),
            radial-gradient(circle at 84% 24%, rgba(242, 140, 40, .18), transparent 18rem);
    }}
    .premium-hero h1 {{
        position: relative;
        z-index: 1;
        color: #FFFFFF !important;
        font-size: 2.35rem !important;
        margin: 0 0 12px !important;
    }}
    .premium-hero p {{
        position: relative;
        z-index: 1;
        max-width: 760px;
        color: rgba(226,232,240,.82) !important;
        font-size: 1rem;
        line-height: 1.7;
    }}
    .premium-badges {{
        position: relative;
        z-index: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 24px;
    }}
    .premium-badges span {{
        color: #F8FAFC;
        border: 1px solid rgba(255,255,255,.16);
        background: rgba(255,255,255,.09);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: .78rem;
        font-weight: 850;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
    }}
    .hero-logo-panel {{
        position: relative;
        z-index: 1;
        align-self: stretch;
        display: grid;
        place-items: center;
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,.13);
        background: rgba(2, 8, 23, .25);
        backdrop-filter: blur(14px);
    }}
    .hero-logo-panel img {{
        width: min(330px, 90%);
        opacity: .92;
        filter: drop-shadow(0 26px 60px rgba(0,0,0,.34));
    }}
    .hero-watermark {{
        position: absolute;
        right: -20px;
        bottom: -42px;
        color: rgba(255,255,255,.045);
        font-size: 9rem;
        font-weight: 950;
        letter-spacing: .04em;
        z-index: 0;
    }}
    .premium-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 16px;
        margin: 16px 0 8px;
    }}
    .premium-kpi {{
        position: relative;
        overflow: hidden;
        min-height: 142px;
        padding: 20px 76px 18px 22px;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, .20);
        background: linear-gradient(145deg, rgba(8, 21, 46, .76), rgba(5, 13, 31, .55));
        box-shadow: 0 26px 78px rgba(2,8,23,.30), inset 0 1px 0 rgba(255,255,255,.08);
        transition: all .18s ease;
    }}
    .premium-kpi:hover {{
        transform: translateY(-4px);
        border-color: rgba(242, 140, 40, .42);
        box-shadow: 0 32px 90px rgba(2,8,23,.38), 0 0 36px rgba(242, 140, 40, .10);
    }}
    .kpi-icon {{
        position: absolute;
        right: 22px;
        top: 40px;
        width: 42px;
        height: 42px;
        display: grid;
        place-items: center;
        border-radius: 15px;
        margin-bottom: 0;
        color: #FFFFFF;
        background: rgba(242, 140, 40, .16);
        border: 1px solid rgba(242, 140, 40, .30);
    }}
    .kpi-label {{
        color: rgba(186,199,217,.85);
        font-size: .76rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: .04em;
    }}
    .kpi-value {{
        color: #FFFFFF;
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 950;
        margin-top: 7px;
    }}
    .kpi-trend {{
        color: rgba(226,232,240,.62);
        font-size: .78rem;
        margin-top: 8px;
    }}
    .dashboard-section {{
        margin-top: 20px;
    }}
    .dashboard-grid {{
        display: grid;
        grid-template-columns: .9fr 1.1fr;
        gap: 16px;
        margin-top: 20px;
    }}
    .dashboard-panel {{
        padding: 18px;
        border-radius: 12px;
        background: linear-gradient(145deg, rgba(8, 21, 46, .72), rgba(5, 13, 31, .56));
        border: 1px solid rgba(96, 165, 250, .22);
        box-shadow: 0 28px 80px rgba(2,8,23,.30), inset 0 1px 0 rgba(255,255,255,.08);
    }}
    .section-title-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 8px 0 12px;
    }}
    .section-title-row h2 {{
        margin: 0 !important;
        font-size: 1.35rem !important;
    }}
    .premium-select-pill {{
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.14);
        background: rgba(255,255,255,.08);
        color: rgba(226,232,240,.82);
        padding: 8px 12px;
        font-weight: 800;
        font-size: .78rem;
    }}
    .summary-strip {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin-top: 14px;
    }}
    .summary-mini {{
        padding: 14px 16px;
        border-radius: 18px;
        background: rgba(255,255,255,.065);
        border: 1px solid rgba(255,255,255,.10);
    }}
    .summary-mini strong {{
        display: block;
        color: #FFFFFF;
        font-size: 1.45rem;
    }}
    .summary-mini span {{
        color: rgba(226,232,240,.64);
        font-size: .78rem;
    }}
    .actions-table-wrap {{
        padding: 0;
        border-radius: 0;
        background: transparent;
        border: 0;
        box-shadow: none;
    }}
    .backup-line {{
        margin: 8px 0 0;
        color: rgba(186,199,217,.78);
        font-size: .88rem;
    }}
    .alpes-footer {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        margin-top: 24px;
        padding: 14px 28px;
        border-top: 1px solid rgba(148,163,184,.16);
        color: rgba(226,232,240,.66);
        font-size: .86rem;
    }}
    .alpes-footer strong {{
        color: #F28C28;
    }}
    .sidebar-help {{
        margin-top: 16px;
        padding: 16px;
        border-radius: 12px;
        background: rgba(255,255,255,.055);
        border: 1px solid rgba(148,163,184,.18);
        color: #FFFFFF;
        font-weight: 800;
        text-align: center;
    }}
    .sidebar-help span {{
        display: block;
        margin-top: 8px;
        color: rgba(226,232,240,.72);
        font-size: .78rem;
        font-weight: 700;
        line-height: 1.35;
    }}
    .sidebar-mini-chart {{
        height: 52px;
        margin: 10px 0 12px;
        border-radius: 8px;
        background:
            linear-gradient(135deg, transparent 0 8%, rgba(59, 130, 246, .42) 8% 11%, transparent 11% 18%, rgba(59, 130, 246, .54) 18% 21%, transparent 21% 30%, rgba(59, 130, 246, .42) 30% 33%, transparent 33% 45%, rgba(59, 130, 246, .62) 45% 48%, transparent 48% 58%, rgba(59, 130, 246, .52) 58% 61%, transparent 61% 72%, rgba(59, 130, 246, .75) 72% 75%, transparent 75% 86%, rgba(59, 130, 246, .9) 86% 89%, transparent 89%),
            rgba(59, 130, 246, .08);
    }}
    @media (max-width: 1100px) {{
        .premium-hero {{
            grid-template-columns: 1fr;
        }}
        .premium-kpi-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        .dashboard-grid {{
            grid-template-columns: 1fr;
        }}
    }}
    @media (max-width: 820px) {{
        [data-testid="stMainBlockContainer"] {{
            padding-left: 1rem;
            padding-right: 1rem;
        }}
        h1 {{
            font-size: 1.75rem !important;
        }}
        .home-hero {{
            padding: 22px;
            min-height: 230px;
        }}
        .home-hero h1 {{
            font-size: 1.75rem !important;
        }}
        .stock-table-header {{
            display: none;
        }}
        .stock-row {{
            grid-template-columns: 1fr;
        }}
        .metric-value {{
            font-size: 24px;
        }}
    }}
</style>
""", unsafe_allow_html=True)


# =========================
# LOGIN
# =========================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "modo_acesso" not in st.session_state:
    st.session_state["modo_acesso"] = "Desktop"
if "login_salvo_usuario" not in st.session_state:
    st.session_state["login_salvo_usuario"] = ""
if "login_salvo_ativo" not in st.session_state:
    st.session_state["login_salvo_ativo"] = False
if st.session_state.get("login_salvo_modo") in ["Desktop", "Mobile"]:
    st.session_state["modo_acesso"] = st.session_state["login_salvo_modo"]

if not st.session_state["autenticado"]:
    DESK_IMAGE = os.path.join(PASTA_IMAGENS_SISTEMA, "desk.jpg")
    imagem_fundo_login = DESK_IMAGE if os.path.exists(DESK_IMAGE) else HOME_IMAGE
    if not os.path.exists(imagem_fundo_login):
        imagem_fundo_login = LOGIN_IMAGE if os.path.exists(LOGIN_IMAGE) else HOME_IMAGE_FALLBACK
    css_fundo_login = "linear-gradient(135deg, #061C3F 0%, #0B1F3A 52%, #020817 100%)"
    if os.path.exists(imagem_fundo_login):
        extensao_fundo = os.path.splitext(imagem_fundo_login)[1].lower().replace(".", "")
        mime_fundo = "jpeg" if extensao_fundo in ["jpg", "jpeg"] else "png"
        css_fundo_login = (
            "linear-gradient(115deg, rgba(6, 28, 63, .96) 0%, rgba(6, 28, 63, .90) 42%, "
            "rgba(2, 8, 23, .78) 100%), "
            "radial-gradient(circle at 18% 18%, rgba(242, 140, 40, .25), transparent 28rem), "
            f"url('data:image/{mime_fundo};base64,{imagem_base64(imagem_fundo_login)}') center/cover no-repeat"
        )

    st.markdown(
        """
        <style>
        .stApp {
            background: __CSS_FUNDO_LOGIN__ !important;
            min-height: 100vh;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1320px !important;
            min-height: 100vh;
            margin: 0 auto !important;
            padding: 2.9rem 2.2rem 1rem !important;
        }
        [data-testid="stMainBlockContainer"] p,
        [data-testid="stMainBlockContainer"] label,
        [data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"],
        [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"],
        [data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] {
            color: rgba(255, 255, 255, .86) !important;
        }
        [data-testid="stMainBlockContainer"] button p {
            color: #FFFFFF !important;
        }
        .login-shell-marker {
            position: fixed;
            inset: 0;
            pointer-events: none;
            background:
                linear-gradient(90deg, rgba(255,255,255,.055) 1px, transparent 1px),
                linear-gradient(0deg, rgba(255,255,255,.04) 1px, transparent 1px);
            background-size: 84px 84px;
            mask-image: linear-gradient(120deg, rgba(0,0,0,.75), transparent 72%);
            z-index: 0;
        }
        .login-left-panel {
            position: relative;
            z-index: 1;
            min-height: calc(100vh - 5rem);
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: .5rem 1.7rem 0 0;
        }
        .login-brand-logo {
            width: min(430px, 86vw);
            height: auto;
            display: block;
            margin: 0 0 2rem;
            filter: drop-shadow(0 28px 52px rgba(0,0,0,.38));
        }
        .login-logo-premium {
            width: min(330px, 82vw);
            height: 126px;
            object-fit: contain;
            object-position: left center;
            border: 0;
            border-radius: 0;
            box-shadow: none;
            filter: drop-shadow(0 28px 52px rgba(0,0,0,.36));
            margin-bottom: 1.8rem;
            display: none;
        }
        .login-kicker {
            display: inline-flex;
            width: fit-content;
            align-items: center;
            gap: .6rem;
            padding: .56rem .9rem;
            border: 1px solid rgba(255,255,255,.16);
            border-radius: 999px;
            background: rgba(255,255,255,.08);
            color: rgba(255,255,255,.86);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            backdrop-filter: blur(18px);
        }
        .login-kicker::before {
            content: "";
            width: .5rem;
            height: .5rem;
            border-radius: 999px;
            background: #F28C28;
            box-shadow: 0 0 24px rgba(242, 140, 40, .85);
        }
        .login-left-panel h1 {
            margin: 0 0 1rem;
            max-width: 560px;
            color: #FFFFFF !important;
            font-size: 2rem;
            line-height: 1.22;
            font-weight: 900;
            letter-spacing: 0;
            text-shadow: 0 24px 80px rgba(2, 8, 23, .45);
        }
        .login-title-white {
            color: #FFFFFF !important;
        }
        .login-title-orange {
            color: #F28C28 !important;
        }
        .login-orange-line {
            width: 66px;
            height: 3px;
            border-radius: 999px;
            background: linear-gradient(90deg, #F28C28, #FDBA74);
            box-shadow: 0 0 28px rgba(242, 140, 40, .62);
            margin: 1.15rem 0 1rem;
        }
        .login-copy {
            max-width: 470px;
            color: rgba(255,255,255,.84) !important;
            font-size: .98rem;
            line-height: 1.55;
        }
        .login-proof {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .75rem;
            margin-top: 0;
            padding: .75rem;
            border-radius: 20px;
            background: rgba(3, 15, 35, .52);
            border: 1px solid rgba(96, 165, 250, .28);
            box-shadow: 0 30px 90px rgba(2,8,23,.34), inset 0 1px 0 rgba(255,255,255,.08);
            backdrop-filter: blur(20px);
        }
        .login-proof-item {
            min-height: 116px;
            padding: .78rem;
            border-right: 1px solid rgba(255,255,255,.12);
            border-radius: 15px;
            background: linear-gradient(150deg, rgba(255,255,255,.07), rgba(255,255,255,.025));
        }
        .login-proof-item:last-child {
            border-right: 0;
        }
        .login-proof-icon {
            color: #F28C28;
            font-size: .9rem;
            margin-bottom: .42rem;
        }
        .login-proof-number {
            color: #FFFFFF;
            font-size: .92rem;
            font-weight: 900;
            line-height: 1.18;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        .login-proof-label {
            margin-top: .62rem;
            color: rgba(255,255,255,.74);
            font-size: .72rem;
            font-weight: 600;
            line-height: 1.34;
            text-transform: none;
            letter-spacing: 0;
        }
        .login-card-premium {
            position: relative;
            z-index: 1;
            margin: 0;
        }
        .login-card-premium::before {
            content: none;
        }
        [data-testid="stMainBlockContainer"] > div > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) > div {
            position: relative;
            z-index: 1;
            margin-top: .4rem;
            padding: 1.8rem;
            border-radius: 24px;
            background: linear-gradient(145deg, rgba(8, 24, 52, .76), rgba(4, 12, 28, .54));
            border: 1px solid rgba(96, 165, 250, .30);
            box-shadow: 0 34px 110px rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.15);
            backdrop-filter: blur(26px);
        }
        .login-card-head {
            margin-bottom: .9rem;
        }
        .login-card-head h2 {
            color: #FFFFFF !important;
            font-size: 1.72rem;
            line-height: 1.15;
            margin: 0 0 .35rem;
            font-weight: 900;
        }
        .login-card-head p {
            color: rgba(255,255,255,.64) !important;
            margin: 0;
            font-size: .9rem;
        }
        .login-access-label {
            color: rgba(255,255,255,.64);
            font-size: .78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin: .15rem 0 .42rem;
        }
        .login-secure-footer {
            margin-top: .8rem;
            padding-top: .7rem;
            border-top: 1px solid rgba(255,255,255,.12);
            color: rgba(255,255,255,.62);
            text-align: center;
            font-size: .72rem;
            line-height: 1.45;
        }
        .login-forgot a {
            display: inline-block;
            margin: -.3rem 0 .2rem;
            color: #FDBA74 !important;
            font-size: .86rem;
            font-weight: 700;
            text-decoration: none;
        }
        .login-forgot a:hover {
            color: #FFFFFF !important;
            text-shadow: 0 0 18px rgba(242,140,40,.55);
        }
        div[data-testid="stTextInput"] input {
            min-height: 2.75rem;
            border-radius: 14px !important;
            background: rgba(3, 10, 24, .48) !important;
            border: 1px solid rgba(255,255,255,.16) !important;
            color: #FFFFFF !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: rgba(255,255,255,.42) !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: rgba(242, 140, 40, .78) !important;
            box-shadow: 0 0 0 4px rgba(242, 140, 40, .14) !important;
        }
        div[data-testid="stCheckbox"] label {
            color: rgba(255,255,255,.72) !important;
            font-weight: 700;
        }
        div[data-testid="stButton"] button {
            min-height: 2.8rem;
            border-radius: 14px !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            background: rgba(255,255,255,.08) !important;
            color: #FFFFFF !important;
            font-weight: 900 !important;
            box-shadow: 0 18px 45px rgba(2,8,23,.22);
            transition: all .22s ease;
        }
        div[data-testid="stButton"] button:hover {
            transform: translateY(-1px);
            border-color: rgba(242, 140, 40, .55) !important;
            box-shadow: 0 20px 60px rgba(242,140,40,.18);
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(135deg, #F28C28, #F97316) !important;
            border-color: rgba(253, 186, 116, .72) !important;
            box-shadow: 0 18px 54px rgba(242, 140, 40, .34), 0 0 0 1px rgba(255,255,255,.08) inset;
        }
        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] {
                padding: 2rem 1rem !important;
            }
            .login-left-panel {
                min-height: auto;
                padding: 1rem 0 1.4rem;
            }
            .login-brand-logo {
                width: min(330px, 86vw);
                margin-bottom: 1.3rem;
            }
            .login-left-panel h1 {
                font-size: 2.1rem;
            }
            .login-proof {
                grid-template-columns: 1fr;
            }
            .login-proof-item,
            .login-proof-item:nth-child(2) {
                border-right: 0;
            }
            .login-card-premium {
                border-radius: 22px;
            }
            [data-testid="stMainBlockContainer"] > div > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) > div {
                padding: 1.35rem;
                border-radius: 22px;
            }
        }
        </style>
        <div class='login-shell-marker'></div>
        """.replace("__CSS_FUNDO_LOGIN__", css_fundo_login),
        unsafe_allow_html=True
    )
    if st.session_state["modo_acesso"] == "Computador":
        st.session_state["modo_acesso"] = "Desktop"
    elif st.session_state["modo_acesso"] == "Celular":
        st.session_state["modo_acesso"] = "Mobile"
    colunas_login = [1.02, .98]
    c1, c2 = st.columns(colunas_login, gap="large")
    with c1:
        logo_login_html = ""
        if os.path.exists(LOGIN_LOGO_IMAGE):
            extensao_logo = os.path.splitext(LOGIN_LOGO_IMAGE)[1].lower().replace(".", "")
            mime_logo = "jpeg" if extensao_logo in ["jpg", "jpeg"] else "png"
            logo_login_html = (
                f"<img src='data:image/{mime_logo};base64,{imagem_base64(LOGIN_LOGO_IMAGE)}' "
                "class='login-brand-logo' alt='ALPES Gestão e Facilities'>"
            )
        st.markdown(
            f"""
            <section class='login-left-panel'>
                {logo_login_html}
                <h1>
                    <span class='login-title-white'>GESTÃO INTELIGENTE.</span><br>
                    <span class='login-title-orange'>RESULTADOS REAIS.</span>
                </h1>
                <p class='login-copy'>
                    A plataforma completa para gestão de facilities, equipes e operações,
                    centralizando tudo em um só lugar.
                </p>
                <div class='login-orange-line'></div>
                <div class='login-proof'>
                    <div class='login-proof-item'>
                        <div class='login-proof-icon'>◆</div>
                        <div class='login-proof-number'>Missão</div>
                        <div class='login-proof-label'>
                            Fornecer soluções de terceirização de serviços que impulsionam
                            as empresas parceiras a novos níveis de sucesso.
                        </div>
                    </div>
                    <div class='login-proof-item'>
                        <div class='login-proof-icon'>◆</div>
                        <div class='login-proof-number'>Visão</div>
                        <div class='login-proof-label'>
                            Ser referência na terceirização de serviços na iniciativa privada,
                            baseada em cultura central: a parceria.
                        </div>
                    </div>
                    <div class='login-proof-item'>
                        <div class='login-proof-icon'>◆</div>
                        <div class='login-proof-number'>Valores</div>
                        <div class='login-proof-label'>
                            Honestidade; Compromisso; Transparência; Sinergia; Humildade.
                        </div>
                    </div>
                </div>
            </section>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class='login-card-premium'>
                <div class='login-card-head'>
                    <h2>Bem-vindo à ALPES</h2>
                    <p>Acesse sua conta para continuar</p>
                </div>
                <div class='login-access-label'>Selecione o tipo de acesso</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        acesso_mobile, acesso_desktop = st.columns(2)
        if acesso_mobile.button(
            "Acesso Mobile",
            use_container_width=True,
            type="primary" if st.session_state["modo_acesso"] == "Mobile" else "secondary"
        ):
            st.session_state["modo_acesso"] = "Mobile"
            st.rerun()
        if acesso_desktop.button(
            "Acesso Corporativo",
            use_container_width=True,
            type="primary" if st.session_state["modo_acesso"] == "Desktop" else "secondary"
        ):
            st.session_state["modo_acesso"] = "Desktop"
            st.rerun()
        usuario_login = st.text_input(
            "Usuário ou email",
            value=st.session_state.get("login_salvo_usuario", ""),
            placeholder="Digite seu usuário ou email"
        )
        mostrar_senha = st.checkbox("Mostrar senha")
        senha_login = st.text_input(
            "Senha",
            type="default" if mostrar_senha else "password",
            placeholder="Digite sua senha"
        )
        st.markdown(
            "<div class='login-forgot'><a href='#'>Esqueceu sua senha?</a></div>",
            unsafe_allow_html=True
        )
        salvar_login = st.checkbox(
            "Salvar login",
            value=bool(st.session_state.get("login_salvo_ativo", False)),
            help="Salva o usuário/email e mantém a sessão neste navegador. A senha não fica gravada."
        )
        if st.button("ENTRAR", use_container_width=True, type="primary"):
            usuarios = garantir_usuario_admin()
            usuario_encontrado = next(
                (
                    u for u in usuarios
                    if str(u.get("nome", "")).lower() == usuario_login.lower()
                    or str(u.get("email", "")).lower() == usuario_login.lower()
                ),
                None
            )
            if usuario_encontrado and usuario_encontrado.get("status", "Ativo") == "Inativo":
                registrar_auditoria("LOGIN_BLOQUEADO", "AUTENTICAÇÃO", "Usuário inativo tentou acessar", usuario_login)
                st.error("Usuário inativo. Fale com o administrador.")
            elif usuario_encontrado and verificar_senha(senha_login, usuario_encontrado.get("senha")):
                if not str(usuario_encontrado.get("senha", "")).startswith("pbkdf2_sha256$"):
                    usuario_encontrado["senha"] = hash_senha(senha_login)
                    salvar_json(USUARIOS_JSON, usuarios)
                st.session_state["autenticado"] = True
                st.session_state["usuario_logado"] = {
                    "nome": usuario_encontrado.get("nome", ""),
                    "email": usuario_encontrado.get("email", ""),
                    "nivel": usuario_encontrado.get("nivel", ""),
                    "veiculo_frota": usuario_encontrado.get("veiculo_frota", ""),
                    "veiculos_frota": usuario_encontrado.get("veiculos_frota", []),
                    "bases_permitidas": usuario_encontrado.get("bases_permitidas", []),
                    "pode_lancar_despesa_frota": usuario_encontrado.get("pode_lancar_despesa_frota", False),
                    "modo_acesso": st.session_state["modo_acesso"]
                }
                if salvar_login:
                    st.session_state["login_salvo_usuario"] = usuario_login.strip()
                    st.session_state["login_salvo_ativo"] = True
                    st.session_state["login_salvo_modo"] = st.session_state["modo_acesso"]
                else:
                    st.session_state["login_salvo_usuario"] = ""
                    st.session_state["login_salvo_ativo"] = False
                    st.session_state.pop("login_salvo_modo", None)
                registrar_auditoria("LOGIN", "AUTENTICAÇÃO", "Login realizado com sucesso", usuario_encontrado.get("nome", ""))
                st.rerun()
            else:
                registrar_auditoria("LOGIN_INVALIDO", "AUTENTICAÇÃO", "Tentativa de login inválida", usuario_login)
                st.error("Login inválido. Verifique usuário/email e senha.")
        st.markdown(
            """
            <div class='login-secure-footer'>
                © 2026 ALPES Gestão e Facilities. Todos os direitos reservados.<br>
                Ambiente seguro e monitorado
            </div>
            """,
            unsafe_allow_html=True
        )
    st.stop()


# =========================
# CARREGAR DADOS
# =========================
COLUNAS_PRODUTOS = ["codigo", "produto", "categoria", "estoque_minimo", "localizacao", "imagem", "unidade", "valor_unitario", "fornecedor", "status"]
COLUNAS_MOVIMENTACOES = ["produto", "tipo", "quantidade", "data", "cliente", "observacao"]
COLUNAS_CLIENTES = ["codigo", "nome_cliente", "telefone", "cidade", "estado", "tipo_contrato", "data_inicial", "data_final", "status"]
COLUNAS_FORNECEDORES = ["codigo", "nome_fornecedor", "telefone", "cidade", "estado", "tipo_contrato", "data_inicial", "data_final", "status"]
COLUNAS_FALTAS = ["data", "colaborador", "funcao", "presenca", "motivo_falta", "almocou_base", "observacoes", "tipo_escala", "data_base_escala", "trabalha_data_base", "status_colaborador", "base_frequencia"]
COLUNAS_FROTAS_VEICULOS = ["placa", "modelo", "marca", "ano", "tipo", "responsavel", "cidade_local", "status", "km_atual", "periodicidade_vistoria", "ultima_vistoria", "proxima_vistoria", "status_responsabilidade"]
COLUNAS_FROTAS_ABASTECIMENTOS = ["data", "placa", "km", "combustivel", "litros", "valor_litro", "valor_total", "posto", "responsavel_lancamento", "registrado_em", "nota_anexo", "status_conferencia", "observacao_administrativo", "observacoes"]
COLUNAS_FROTAS_MANUTENCOES = ["data", "placa", "tipo_manutencao", "km", "servico_executado", "fornecedor", "valor", "manutencao_agendada", "proxima_revisao", "status_manutencao", "responsavel_lancamento", "registrado_em", "nota_anexo", "status_conferencia", "observacao_administrativo", "observacoes"]
COLUNAS_FROTAS_DOCUMENTOS = ["placa", "documento", "vencimento", "valor", "status", "observacoes"]
COLUNAS_FROTAS_ENTREGAS = ["data", "placa", "responsavel", "km", "periodicidade", "proxima_vistoria", "pneus", "lataria", "vidros", "farois_lanternas", "documentacao", "itens_obrigatorios", "fotos", "observacoes", "registrado_em"]
COLUNAS_FROTAS_VISTORIAS = ["data", "placa", "tipo_vistoria", "responsavel", "km", "periodicidade", "proxima_vistoria", "pneus", "lataria", "vidros", "farois_lanternas", "documentacao", "itens_obrigatorios", "fotos", "observacoes", "registrado_em"]
COLUNAS_BASES_MOVIMENTACOES = ["data", "base", "produto", "tipo", "quantidade", "responsavel", "origem_destino", "observacoes"]
COLUNAS_BASES_TRANSFERENCIAS = ["data", "produto", "quantidade", "origem", "destino", "responsavel_envio", "responsavel_recebimento", "status", "observacoes"]

def buscar_produtos():
    return carregar_dataframe(PRODUTOS_XLSX, COLUNAS_PRODUTOS)


def salvar_produto(dados):
    dados.to_excel(PRODUTOS_XLSX, index=False)


def atualizar_produto(dados):
    salvar_produto(dados)


def buscar_movimentacoes():
    return carregar_dataframe(MOVIMENTACOES_XLSX, COLUNAS_MOVIMENTACOES)


def salvar_movimentacao(dados):
    dados.to_excel(MOVIMENTACOES_XLSX, index=False)


def buscar_clientes():
    return carregar_dataframe(CLIENTES_XLSX, COLUNAS_CLIENTES)


def salvar_cliente(dados):
    dados.to_excel(CLIENTES_XLSX, index=False)


def buscar_fornecedores():
    return carregar_dataframe(FORNECEDORES_XLSX, COLUNAS_FORNECEDORES)


def salvar_fornecedor(dados):
    dados.to_excel(FORNECEDORES_XLSX, index=False)


def buscar_veiculos():
    return carregar_dataframe(FROTAS_VEICULOS_XLSX, COLUNAS_FROTAS_VEICULOS)


def salvar_veiculo(dados):
    dados.to_excel(FROTAS_VEICULOS_XLSX, index=False)


def buscar_abastecimentos():
    return carregar_dataframe(FROTAS_ABASTECIMENTOS_XLSX, COLUNAS_FROTAS_ABASTECIMENTOS)


def salvar_abastecimento(dados):
    dados.to_excel(FROTAS_ABASTECIMENTOS_XLSX, index=False)


def buscar_manutencoes_frota():
    return carregar_dataframe(FROTAS_MANUTENCOES_XLSX, COLUNAS_FROTAS_MANUTENCOES)


def salvar_manutencao_frota(dados):
    dados.to_excel(FROTAS_MANUTENCOES_XLSX, index=False)


def buscar_usuarios():
    return carregar_json(USUARIOS_JSON, [])


def salvar_usuario(dados):
    salvar_json(USUARIOS_JSON, dados)


def buscar_configuracoes():
    return carregar_json(CONFIG_JSON, configuracao_padrao())


def salvar_configuracao(dados):
    salvar_json(CONFIG_JSON, dados)


def registrar_log(acao, modulo="", detalhe="", registro="", antes=None, depois=None):
    registrar_auditoria(acao, modulo, detalhe, registro, antes, depois)


df_produtos = buscar_produtos()
df_mov = buscar_movimentacoes()
df_clientes = buscar_clientes()
df_fornecedores = buscar_fornecedores()
df_faltas = carregar_dataframe(CONTROLE_FALTAS_XLSX, COLUNAS_FALTAS)
df_frotas_veiculos = buscar_veiculos()
df_frotas_abastecimentos = buscar_abastecimentos()
df_frotas_manutencoes = buscar_manutencoes_frota()
df_frotas_documentos = carregar_dataframe(FROTAS_DOCUMENTOS_XLSX, COLUNAS_FROTAS_DOCUMENTOS)
df_frotas_entregas = carregar_dataframe(FROTAS_ENTREGAS_XLSX, COLUNAS_FROTAS_ENTREGAS)
df_frotas_vistorias = carregar_dataframe(FROTAS_VISTORIAS_XLSX, COLUNAS_FROTAS_VISTORIAS)
df_bases_movimentacoes = carregar_dataframe(BASES_MOVIMENTACOES_XLSX, COLUNAS_BASES_MOVIMENTACOES)
df_bases_transferencias = carregar_dataframe(BASES_TRANSFERENCIAS_XLSX, COLUNAS_BASES_TRANSFERENCIAS)

for col in ["codigo", "produto", "categoria", "estoque_minimo", "localizacao", "imagem", "unidade", "valor_unitario", "fornecedor", "status"]:
    if col not in df_produtos.columns:
        df_produtos[col] = "Ativo" if col == "status" else ""
df_produtos["status"] = df_produtos["status"].astype("object").fillna("")
df_produtos.loc[df_produtos["status"].astype(str).str.strip() == "", "status"] = "Ativo"

for col in ["produto", "tipo", "quantidade", "data", "cliente", "observacao"]:
    if col not in df_mov.columns:
        df_mov[col] = ""

for col in ["codigo", "nome_cliente", "telefone", "cidade", "estado", "tipo_contrato", "data_inicial", "data_final", "status"]:
    if col not in df_clientes.columns:
        df_clientes[col] = "Ativo" if col == "status" else ""
    df_clientes[col] = df_clientes[col].astype("object").fillna("")
df_clientes.loc[df_clientes["status"] == "", "status"] = "Ativo"

for col in ["codigo", "nome_fornecedor", "telefone", "cidade", "estado", "tipo_contrato", "data_inicial", "data_final", "status"]:
    if col not in df_fornecedores.columns:
        df_fornecedores[col] = "Ativo" if col == "status" else ""
    df_fornecedores[col] = df_fornecedores[col].astype("object").fillna("")
df_fornecedores.loc[df_fornecedores["status"] == "", "status"] = "Ativo"

for col in ["data", "colaborador", "funcao", "presenca", "motivo_falta", "almocou_base", "observacoes", "tipo_escala", "data_base_escala", "trabalha_data_base", "status_colaborador"]:
    if col not in df_faltas.columns:
        df_faltas[col] = "SEGUNDA A SEXTA" if col == "tipo_escala" else "Ativo" if col == "status_colaborador" else ""
    df_faltas[col] = df_faltas[col].astype("object").fillna("")
if "base_frequencia" not in df_faltas.columns:
    df_faltas["base_frequencia"] = "TMG BASE SORRISO"
df_faltas["base_frequencia"] = df_faltas["base_frequencia"].astype("object").fillna("")
df_faltas.loc[df_faltas["base_frequencia"].astype(str).str.strip() == "", "base_frequencia"] = "TMG BASE SORRISO"
df_faltas.loc[df_faltas["tipo_escala"] == "", "tipo_escala"] = "SEGUNDA A SEXTA"
df_faltas.loc[df_faltas["trabalha_data_base"] == "", "trabalha_data_base"] = "Sim"
df_faltas.loc[df_faltas["status_colaborador"] == "", "status_colaborador"] = "Ativo"
df_faltas["data"] = pd.to_datetime(df_faltas["data"], errors="coerce").dt.date.astype("object").fillna("")
df_faltas["presenca"] = df_faltas["presenca"].astype(str).str.upper()
df_faltas["presenca"] = df_faltas["presenca"].replace({"APRESENTAR": "PRESENTE"})
df_faltas["almocou_base"] = df_faltas["almocou_base"].astype(str).str.capitalize()

for col in ["placa", "modelo", "marca", "ano", "tipo", "responsavel", "cidade_local", "status", "km_atual", "periodicidade_vistoria", "ultima_vistoria", "proxima_vistoria", "status_responsabilidade"]:
    if col not in df_frotas_veiculos.columns:
        df_frotas_veiculos[col] = "Ativo" if col == "status" else "Mensal" if col == "periodicidade_vistoria" else "Disponível" if col == "status_responsabilidade" else ""
    df_frotas_veiculos[col] = df_frotas_veiculos[col].astype("object").fillna("")
df_frotas_veiculos.loc[df_frotas_veiculos["status"] == "", "status"] = "Ativo"
df_frotas_veiculos.loc[df_frotas_veiculos["periodicidade_vistoria"].astype(str).str.strip() == "", "periodicidade_vistoria"] = "Mensal"
df_frotas_veiculos.loc[df_frotas_veiculos["status_responsabilidade"].astype(str).str.strip() == "", "status_responsabilidade"] = "Disponível"

for col in ["data", "placa", "km", "combustivel", "litros", "valor_litro", "valor_total", "posto", "responsavel_lancamento", "registrado_em", "nota_anexo", "status_conferencia", "observacao_administrativo", "observacoes"]:
    if col not in df_frotas_abastecimentos.columns:
        df_frotas_abastecimentos[col] = 0 if col in ["km", "litros", "valor_litro", "valor_total"] else "Pendente" if col == "status_conferencia" else ""
    df_frotas_abastecimentos[col] = df_frotas_abastecimentos[col].astype("object").fillna("")
df_frotas_abastecimentos.loc[df_frotas_abastecimentos["status_conferencia"] == "", "status_conferencia"] = "Pendente"
for col in ["km", "litros", "valor_litro", "valor_total"]:
    df_frotas_abastecimentos[col] = pd.to_numeric(df_frotas_abastecimentos[col], errors="coerce").fillna(0)

for col in ["data", "placa", "tipo_manutencao", "km", "servico_executado", "fornecedor", "valor", "manutencao_agendada", "proxima_revisao", "status_manutencao", "responsavel_lancamento", "registrado_em", "nota_anexo", "status_conferencia", "observacao_administrativo", "observacoes"]:
    if col not in df_frotas_manutencoes.columns:
        df_frotas_manutencoes[col] = 0 if col in ["km", "valor"] else "Pendente" if col == "status_conferencia" else ""
    df_frotas_manutencoes[col] = df_frotas_manutencoes[col].astype("object").fillna("")
df_frotas_manutencoes.loc[df_frotas_manutencoes["status_manutencao"] == "", "status_manutencao"] = "Executada"
df_frotas_manutencoes.loc[df_frotas_manutencoes["status_conferencia"] == "", "status_conferencia"] = "Pendente"
for col in ["km", "valor"]:
    df_frotas_manutencoes[col] = pd.to_numeric(df_frotas_manutencoes[col], errors="coerce").fillna(0)

for col in ["data", "base", "produto", "tipo", "quantidade", "responsavel", "origem_destino", "observacoes"]:
    if col not in df_bases_movimentacoes.columns:
        df_bases_movimentacoes[col] = 0 if col == "quantidade" else ""
    df_bases_movimentacoes[col] = df_bases_movimentacoes[col].astype("object").fillna("")
df_bases_movimentacoes["quantidade"] = pd.to_numeric(df_bases_movimentacoes["quantidade"], errors="coerce").fillna(0)

for col in ["data", "produto", "quantidade", "origem", "destino", "responsavel_envio", "responsavel_recebimento", "status", "observacoes"]:
    if col not in df_bases_transferencias.columns:
        df_bases_transferencias[col] = 0 if col == "quantidade" else "Enviado" if col == "status" else ""
    df_bases_transferencias[col] = df_bases_transferencias[col].astype("object").fillna("")
df_bases_transferencias.loc[df_bases_transferencias["status"] == "", "status"] = "Enviado"
df_bases_transferencias["quantidade"] = pd.to_numeric(df_bases_transferencias["quantidade"], errors="coerce").fillna(0)

for col in ["data", "placa", "responsavel", "km", "periodicidade", "proxima_vistoria", "pneus", "lataria", "vidros", "farois_lanternas", "documentacao", "itens_obrigatorios", "fotos", "observacoes", "registrado_em"]:
    if col not in df_frotas_entregas.columns:
        df_frotas_entregas[col] = 0 if col == "km" else ""
    df_frotas_entregas[col] = df_frotas_entregas[col].astype("object").fillna("")
df_frotas_entregas["km"] = pd.to_numeric(df_frotas_entregas["km"], errors="coerce").fillna(0)

for col in ["data", "placa", "tipo_vistoria", "responsavel", "km", "periodicidade", "proxima_vistoria", "pneus", "lataria", "vidros", "farois_lanternas", "documentacao", "itens_obrigatorios", "fotos", "observacoes", "registrado_em"]:
    if col not in df_frotas_vistorias.columns:
        df_frotas_vistorias[col] = 0 if col == "km" else "Periódica" if col == "tipo_vistoria" else ""
    df_frotas_vistorias[col] = df_frotas_vistorias[col].astype("object").fillna("")
df_frotas_vistorias["km"] = pd.to_numeric(df_frotas_vistorias["km"], errors="coerce").fillna(0)


def alertas_manutencao_preventiva(df_manutencoes):
    colunas_alerta = ["placa", "manutencao_agendada", "dias", "status", "servico_executado"]
    if df_manutencoes.empty:
        return pd.DataFrame(columns=colunas_alerta)

    dados = df_manutencoes.copy()
    dados["tipo_normalizado"] = dados["tipo_manutencao"].astype(str).str.upper()
    dados["status_normalizado"] = dados["status_manutencao"].astype(str).str.upper()
    dados = dados[
        (dados["tipo_normalizado"] == "PREVENTIVA")
        & (dados["status_normalizado"] == "PROGRAMADA")
    ].copy()
    if dados.empty:
        return pd.DataFrame(columns=colunas_alerta)

    dados["manutencao_agendada_dt"] = pd.to_datetime(dados["manutencao_agendada"], errors="coerce").dt.date
    dados = dados.dropna(subset=["manutencao_agendada_dt"])
    hoje = datetime.now().date()
    alertas = []

    for _, revisao in dados.iterrows():
        placa = str(revisao.get("placa", "")).strip()
        vencimento = revisao["manutencao_agendada_dt"]

        dias = (vencimento - hoje).days
        if dias < 0:
            status_alerta = "Vencida"
        elif dias <= 10:
            status_alerta = "Vence Em Ate 10 Dias"
        else:
            continue

        alertas.append({
            "placa": placa,
            "manutencao_agendada": vencimento.strftime("%d/%m/%Y"),
            "dias": dias,
            "status": status_alerta,
            "servico_executado": revisao.get("servico_executado", "")
        })

    return pd.DataFrame(alertas, columns=colunas_alerta)


def assinatura_alertas_preventiva(alertas):
    if alertas.empty:
        return ""
    campos = ["placa", "manutencao_agendada", "status", "servico_executado"]
    dados = alertas[campos].astype(str).sort_values(campos).to_dict("records")
    return json.dumps(dados, ensure_ascii=False)


def dias_periodicidade_vistoria(periodicidade):
    mapa = {
        "Semanal": 7,
        "Quinzenal": 15,
        "Mensal": 30,
        "Bimestral": 60,
        "Trimestral": 90,
        "Semestral": 180,
        "Anual": 365,
    }
    return mapa.get(str(periodicidade or "").strip().title(), 30)


def calcular_proxima_vistoria(data_base, periodicidade):
    data_base = pd.to_datetime(data_base, errors="coerce")
    if pd.isna(data_base):
        data_base = pd.to_datetime(datetime.now().date())
    return (data_base.date() + timedelta(days=dias_periodicidade_vistoria(periodicidade))).isoformat()


def alertas_vistorias_veiculos(df_veiculos):
    colunas_alerta = ["placa", "responsavel", "proxima_vistoria", "dias", "status"]
    if df_veiculos.empty:
        return pd.DataFrame(columns=colunas_alerta)

    dados = df_veiculos.copy()
    dados = dados[dados["status"].astype(str) != "Inativo"].copy()
    dados["proxima_vistoria_dt"] = pd.to_datetime(dados["proxima_vistoria"], errors="coerce").dt.date
    dados = dados.dropna(subset=["proxima_vistoria_dt"])
    hoje = datetime.now().date()
    alertas = []

    for _, veiculo in dados.iterrows():
        vencimento = veiculo["proxima_vistoria_dt"]
        dias = (vencimento - hoje).days
        if dias < 0:
            status_alerta = "Vencida"
        elif dias <= 10:
            status_alerta = "Vence Em Até 10 Dias"
        else:
            continue
        alertas.append({
            "placa": veiculo.get("placa", ""),
            "responsavel": veiculo.get("responsavel", ""),
            "proxima_vistoria": vencimento.strftime("%d/%m/%Y"),
            "dias": dias,
            "status": status_alerta,
        })

    return pd.DataFrame(alertas, columns=colunas_alerta)


def assinatura_alertas_vistorias(alertas):
    if alertas.empty:
        return ""
    campos = ["placa", "proxima_vistoria", "status"]
    dados = alertas[campos].astype(str).sort_values(campos).to_dict("records")
    return json.dumps(dados, ensure_ascii=False)


def salvar_anexos_frota(arquivos, placa, tipo_lancamento):
    caminhos = []
    for arquivo in arquivos or []:
        caminho = salvar_anexo_frota(arquivo, placa, tipo_lancamento)
        if caminho:
            caminhos.append(caminho)
    return "; ".join(caminhos)


def colaboradores_ativos_para_responsavel():
    if "df_faltas" not in globals() or df_faltas.empty:
        return []
    dados = colaboradores_frequencia(df_faltas)
    if dados.empty:
        return []
    dados = dados[dados["status_colaborador"].astype(str) != "Inativo"]
    return sorted(dados["colaborador"].dropna().astype(str).str.title().unique().tolist())


def assinatura_conferencia_frotas(df_abastecimentos, df_manutencoes):
    pendentes = []
    if not df_abastecimentos.empty:
        abastecimentos = df_abastecimentos[df_abastecimentos["status_conferencia"].astype(str) == "Pendente"].copy()
        for idx, row in abastecimentos.iterrows():
            pendentes.append({
                "tipo": "Abastecimento",
                "idx": int(idx),
                "placa": str(row.get("placa", "")),
                "registrado_em": str(row.get("registrado_em", "")),
                "valor": str(row.get("valor_total", ""))
            })
    if not df_manutencoes.empty:
        manutencoes = df_manutencoes[df_manutencoes["status_conferencia"].astype(str) == "Pendente"].copy()
        for idx, row in manutencoes.iterrows():
            pendentes.append({
                "tipo": "Manutenção",
                "idx": int(idx),
                "placa": str(row.get("placa", "")),
                "registrado_em": str(row.get("registrado_em", "")),
                "valor": str(row.get("valor", ""))
            })
    if not pendentes:
        return ""
    return json.dumps(sorted(pendentes, key=lambda item: (item["tipo"], item["idx"])), ensure_ascii=False)


def baixar_manutencoes_programadas(df_manutencoes, placa, data_execucao):
    if df_manutencoes.empty:
        return df_manutencoes

    data_execucao = pd.to_datetime(data_execucao, errors="coerce")
    if pd.isna(data_execucao):
        return df_manutencoes

    datas_programadas = pd.to_datetime(df_manutencoes["manutencao_agendada"], errors="coerce")
    filtro = (
        (df_manutencoes["placa"].astype(str) == str(placa))
        & (df_manutencoes["tipo_manutencao"].astype(str).str.upper() == "PREVENTIVA")
        & (df_manutencoes["status_manutencao"].astype(str).str.upper() == "PROGRAMADA")
        & (datas_programadas <= data_execucao)
    )
    df_manutencoes.loc[filtro, "status_manutencao"] = "Executada"
    return df_manutencoes

for col in ["placa", "documento", "vencimento", "valor", "status", "observacoes"]:
    if col not in df_frotas_documentos.columns:
        df_frotas_documentos[col] = "Ativo" if col == "status" else 0 if col == "valor" else ""
    df_frotas_documentos[col] = df_frotas_documentos[col].astype("object").fillna("")
df_frotas_documentos["valor"] = pd.to_numeric(df_frotas_documentos["valor"], errors="coerce").fillna(0)

df_produtos["estoque_minimo"] = pd.to_numeric(df_produtos["estoque_minimo"], errors="coerce").fillna(0)
df_produtos["valor_unitario"] = pd.to_numeric(df_produtos["valor_unitario"], errors="coerce").fillna(0)
df_mov["quantidade"] = pd.to_numeric(df_mov["quantidade"], errors="coerce").fillna(0)
df_mov["tipo"] = df_mov["tipo"].astype(str).replace({
    "Saida": "Saída",
    "SaÃ­da": "Saída",
    "saida": "Saída",
    "saída": "Saída",
    "entrada": "Entrada"
})


# =========================
# FUNCOES DE APOIO
# =========================
def calcular_estoque():
    if df_mov.empty:
        return pd.Series(dtype=float)

    ent = df_mov[df_mov["tipo"] == "Entrada"].groupby("produto")["quantidade"].sum()
    sai = df_mov[df_mov["tipo"] == "Saída"].groupby("produto")["quantidade"].sum()

    return ent.subtract(sai, fill_value=0)


df_produtos["estoque_atual"] = df_produtos["produto"].map(calcular_estoque()).fillna(0)

df_produtos["situacao"] = df_produtos.apply(
    lambda x: "🔴 ESTOQUE BAIXO" if x["estoque_atual"] <= x["estoque_minimo"] else "🟢 OK",
    axis=1
)


def cor_categoria(cat):
    cat_upper = str(cat).upper()
    for item in categorias_config:
        if item.get("nome", "").upper() == cat_upper:
            return item.get("cor", "white")
    if cat_upper in ["HIDRAULICA", "HIDRÁULICA"]:
        return "#2563EB"
    if cat_upper in ["ELETRICA", "ELÉTRICA"]:
        return "#F97316"
    if cat_upper in ["MANUTENCAO", "MANUTENÇÃO"]:
        return "#FACC15"
    if cat_upper == "JARDINAGEM":
        return "#22C55E"
    return "white"


def escape_html(valor):
    return html.escape(str(valor if valor is not None else ""))


def badge_categoria(categoria):
    cor = cor_categoria(categoria)
    if not cor or str(cor).lower() == "white":
        cor = "#0B1F3A"
    return f"<span class='category-pill' style='--pill-color:{cor}'>{escape_html(categoria)}</span>"


def badge_estoque(estoque_atual, estoque_minimo):
    try:
        atual = float(estoque_atual)
        minimo = float(estoque_minimo)
    except Exception:
        atual, minimo = 0, 0
    if atual <= minimo:
        classe = "stock-critical" if atual <= max(minimo * 0.5, 0) else "stock-low"
        texto = "Crítico" if classe == "stock-critical" else "Baixo"
    else:
        classe = "stock-ok"
        texto = "Normal"
    return f"<span class='stock-pill {classe}'>{texto}</span>"


def plotly_layout(fig, altura=360):
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=fonte, color="#0F172A"),
        margin=dict(l=20, r=20, t=42, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(100,116,139,.16)", zeroline=False)
    return fig


def filtrar_movimentacoes(df_base, periodo="30 dias", tipo="Todos", categoria="Todas", produto="Todos", data_ini=None, data_fim=None):
    df = df_base.copy()
    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data"])
    hoje = datetime.now()

    if periodo == "7 dias":
        df = df[df["data"] >= hoje - timedelta(days=7)]
    elif periodo == "30 dias":
        df = df[df["data"] >= hoje - timedelta(days=30)]
    elif periodo == "Personalizado" and data_ini and data_fim:
        ini = pd.to_datetime(data_ini)
        fim = pd.to_datetime(data_fim) + timedelta(days=1)
        df = df[(df["data"] >= ini) & (df["data"] < fim)]

    if tipo != "Todos":
        df = df[df["tipo"] == tipo]

    if produto != "Todos":
        df = df[df["produto"] == produto]

    if categoria != "Todas" and not df_produtos.empty:
        produtos_categoria = df_produtos[df_produtos["categoria"] == categoria]["produto"].tolist()
        df = df[df["produto"].isin(produtos_categoria)]

    return df


def calcular_menos_movimentados(df_relatorio, produtos_base):
    colunas = ["codigo", "produto", "categoria", "quantidade"]
    if produtos_base.empty:
        return pd.DataFrame(columns=colunas)

    produtos = produtos_base[["codigo", "produto", "categoria"]].copy()
    if df_relatorio.empty:
        produtos["quantidade"] = 0
        return produtos[colunas].sort_values(["quantidade", "produto"], ascending=[True, True])

    mov = df_relatorio.groupby("produto")["quantidade"].sum().reset_index()
    menos_mov = produtos.merge(mov, on="produto", how="left")
    menos_mov["quantidade"] = menos_mov["quantidade"].fillna(0).astype(int)
    return menos_mov[colunas].sort_values(["quantidade", "produto"], ascending=[True, True])


def calcular_gastos_clientes(df_relatorio):
    colunas_detalhe = ["cliente", "produto", "quantidade", "valor_unitario", "total"]
    colunas_resumo = ["cliente", "quantidade", "total"]
    if df_relatorio.empty:
        return pd.DataFrame(columns=colunas_resumo), pd.DataFrame(columns=colunas_detalhe)

    saidas = df_relatorio[df_relatorio["tipo"] == "Saída"].copy()
    if saidas.empty:
        return pd.DataFrame(columns=colunas_resumo), pd.DataFrame(columns=colunas_detalhe)

    saidas["cliente"] = saidas.get("cliente", "").fillna("").astype(str)
    saidas = saidas[saidas["cliente"].str.strip() != ""]
    if saidas.empty:
        return pd.DataFrame(columns=colunas_resumo), pd.DataFrame(columns=colunas_detalhe)

    produtos_valor = df_produtos[["produto", "valor_unitario"]].copy()
    produtos_valor["valor_unitario"] = pd.to_numeric(produtos_valor["valor_unitario"], errors="coerce").fillna(0)
    detalhe = saidas.merge(produtos_valor, on="produto", how="left")
    detalhe["valor_unitario"] = detalhe["valor_unitario"].fillna(0)
    detalhe["quantidade"] = pd.to_numeric(detalhe["quantidade"], errors="coerce").fillna(0)
    detalhe["total"] = detalhe["quantidade"] * detalhe["valor_unitario"]

    detalhe = detalhe.groupby(["cliente", "produto", "valor_unitario"], as_index=False)["quantidade"].sum()
    detalhe["total"] = detalhe["quantidade"] * detalhe["valor_unitario"]
    detalhe = detalhe[colunas_detalhe].sort_values(["cliente", "total"], ascending=[True, False])

    resumo = detalhe.groupby("cliente", as_index=False).agg({
        "quantidade": "sum",
        "total": "sum"
    }).sort_values("total", ascending=False)

    return resumo[colunas_resumo], detalhe[colunas_detalhe]


def produtos_mais_saidas(df_relatorio):
    colunas = ["produto", "quantidade"]
    if df_relatorio.empty:
        return pd.DataFrame(columns=colunas)
    saidas = df_relatorio[df_relatorio["tipo"].astype(str).isin(["Saída", "Saida", "SaÃ­da", "SaÃƒÂ­da"])].copy()
    if saidas.empty:
        return pd.DataFrame(columns=colunas)
    saidas["quantidade"] = pd.to_numeric(saidas["quantidade"], errors="coerce").fillna(0)
    return saidas.groupby("produto", as_index=False)["quantidade"].sum().sort_values("quantidade", ascending=False)


def calcular_estoque_base(df_mov_base, base):
    colunas = ["produto", "entradas", "saidas", "estoque_atual"]
    if df_mov_base.empty:
        return pd.DataFrame(columns=colunas)
    dados = df_mov_base[df_mov_base["base"].astype(str) == str(base)].copy()
    if dados.empty:
        return pd.DataFrame(columns=colunas)
    dados["quantidade"] = pd.to_numeric(dados["quantidade"], errors="coerce").fillna(0)
    entradas = dados[dados["tipo"].astype(str) == "Entrada"].groupby("produto")["quantidade"].sum()
    saidas = dados[dados["tipo"].astype(str) == "Saída"].groupby("produto")["quantidade"].sum()
    produtos = sorted(set(entradas.index.tolist() + saidas.index.tolist()))
    estoque = pd.DataFrame({"produto": produtos})
    estoque["entradas"] = estoque["produto"].map(entradas).fillna(0)
    estoque["saidas"] = estoque["produto"].map(saidas).fillna(0)
    estoque["estoque_atual"] = estoque["entradas"] - estoque["saidas"]
    return estoque[colunas].sort_values("produto")


def estoque_matriz_produto(produto):
    if df_produtos.empty:
        return 0
    linha = df_produtos[df_produtos["produto"].astype(str) == str(produto)]
    if linha.empty:
        return 0
    return float(pd.to_numeric(linha.iloc[0].get("estoque_atual", 0), errors="coerce") or 0)


PERFIS_ADMIN = ["Administrador", "CEO"]
PERFIS_SUPERVISOR_BASE = ["Supervisor Base", "Supervisor Base TMG"]
PERFIS_MOTORISTA = ["Responsável Frota", "Motorista"]
PERFIS_ALMOXARIFADO = ["Administrador", "CEO", "Administrativo", "Usuário", "Almoxarife", "Consulta"]
PERFIS_RECEBIMENTO = ["Administrador", "CEO", "Administrativo", "ADM"]


def nivel_usuario(usuario):
    return usuario.get("nivel", "Usuário") if isinstance(usuario, dict) else "Usuário"


def usuario_eh_admin(usuario):
    return nivel_usuario(usuario) in PERFIS_ADMIN


def usuario_eh_supervisor_base(usuario):
    return nivel_usuario(usuario) in PERFIS_SUPERVISOR_BASE


def usuario_eh_motorista(usuario):
    return nivel_usuario(usuario) in PERFIS_MOTORISTA


def usuario_pode_acessar_base(usuario, base):
    if usuario_eh_admin(usuario):
        return True
    bases_permitidas = usuario.get("bases_permitidas", [])
    if isinstance(bases_permitidas, str):
        bases_permitidas = [bases_permitidas] if bases_permitidas.strip() else []
    return str(base) in bases_permitidas


def usuario_pode_lancar_despesa_frota(usuario):
    return (
        usuario_eh_admin(usuario)
        or usuario_eh_supervisor_base(usuario)
        or usuario_eh_motorista(usuario)
        or bool(usuario.get("pode_lancar_despesa_frota", False))
    )



PERMISSOES_PERFIL = {
    "Administrador": ["INICIO", "ALMOXARIFADO", "BASES", "FROTAS", "CONFIGURAÇÕES"],
    "CEO": ["INICIO", "ALMOXARIFADO", "BASES", "FROTAS", "CONFIGURAÇÕES"],
    "Administrativo": ["INICIO", "ALMOXARIFADO", "BASES", "FROTAS"],
    "ADM": ["INICIO", "BASES", "FROTAS"],
    "Usuário": ["INICIO", "ALMOXARIFADO", "FROTAS"],
    "Almoxarife": ["INICIO", "ALMOXARIFADO"],
    "Supervisor Base": ["INICIO", "BASES"],
    "Supervisor Base TMG": ["INICIO", "BASES"],
    "Responsável Frota": ["FROTAS"],
    "Motorista": ["FROTAS"],
    "Consulta": ["INICIO", "ALMOXARIFADO", "BASES", "FROTAS"],
}


def modulos_permitidos_usuario(usuario):
    nivel = nivel_usuario(usuario)
    return PERMISSOES_PERFIL.get(nivel, PERMISSOES_PERFIL["Usuário"])


def usuario_somente_consulta(usuario):
    return isinstance(usuario, dict) and usuario.get("nivel") == "Consulta"


def bloquear_se_consulta(usuario, mensagem="Perfil de consulta não pode alterar dados."):
    if usuario_somente_consulta(usuario):
        st.error(mensagem)
        return True
    return False


def texto_obrigatorio(valor):
    return bool(str(valor or "").strip())


def valor_duplicado(df, coluna, valor, ignorar_indice=None):
    if df.empty or coluna not in df.columns:
        return False
    serie = df[coluna].astype(str).str.strip().str.upper()
    alvo = str(valor or "").strip().upper()
    if ignorar_indice is not None and ignorar_indice in serie.index:
        serie = serie.drop(index=ignorar_indice)
    return bool((serie == alvo).any())

def formatar_colunas_tabela(df):
    df_formatado = df.copy()
    df_formatado.columns = [
        str(col).replace("_", " ").title()
        for col in df_formatado.columns
    ]
    return df_formatado



def colaboradores_frequencia(df):
    colunas = ["colaborador", "funcao", "tipo_escala", "data_base_escala", "trabalha_data_base", "status_colaborador"]
    if df.empty:
        return pd.DataFrame(columns=colunas)

    dados = df[df["colaborador"].astype(str).str.strip() != ""].copy()
    if dados.empty:
        return pd.DataFrame(columns=colunas)

    for col in colunas:
        if col not in dados.columns:
            dados[col] = ""
    dados["_data_ordem"] = pd.to_datetime(dados.get("data", ""), errors="coerce")
    dados = dados.sort_values("_data_ordem").drop_duplicates("colaborador", keep="last")
    dados = dados[colunas].fillna("")
    dados.loc[dados["tipo_escala"] == "", "tipo_escala"] = "SEGUNDA A SEXTA"
    dados.loc[dados["trabalha_data_base"] == "", "trabalha_data_base"] = "Sim"
    dados.loc[dados["status_colaborador"] == "", "status_colaborador"] = "Ativo"
    return dados.sort_values("colaborador").reset_index(drop=True)


def status_previsto_escala(data_ref, tipo_escala, data_base_escala="", trabalha_data_base="Sim", feriado=False):
    if feriado and str(tipo_escala).upper() == "SEGUNDA A SEXTA":
        return "FOLGA"
    if str(tipo_escala).upper() == "SEGUNDA A SEXTA":
        return "PRESENTE" if data_ref.weekday() < 5 else "FOLGA"

    data_base = pd.to_datetime(data_base_escala, errors="coerce")
    if pd.isna(data_base):
        return "PRESENTE"

    diferenca = (pd.to_datetime(data_ref).date() - data_base.date()).days
    paridade_trabalho = 0 if str(trabalha_data_base).lower() == "sim" else 1
    return "PRESENTE" if abs(diferenca) % 2 == paridade_trabalho else "FOLGA"


def proximo_codigo_cliente():
    if df_clientes.empty:
        return "001"

    codigos = pd.to_numeric(df_clientes["codigo"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    maior_codigo = int(codigos.max()) if codigos.notna().any() else 0
    return f"{maior_codigo + 1:03d}"


def proximo_codigo_fornecedor():
    if df_fornecedores.empty:
        return "001"

    codigos = pd.to_numeric(df_fornecedores["codigo"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    maior_codigo = int(codigos.max()) if codigos.notna().any() else 0
    return f"{maior_codigo + 1:03d}"


def proximo_codigo_produto():
    if df_produtos.empty:
        return "AL-001"

    codigos = pd.to_numeric(df_produtos["codigo"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    maior_codigo = int(codigos.max()) if codigos.notna().any() else 0
    return f"AL-{maior_codigo + 1:03d}"


def gerar_pdf_relatorios(df_rel, df_criticos, df_menos_mov, df_gastos_clientes, df_gastos_detalhe, metricas):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elementos = [
        Paragraph("Relatórios de Estoque", styles["Title"]),
        Spacer(1, 12)
    ]

    tabela_metricas = Table([
        ["Total de produtos", "Entradas", "Saídas", "Itens críticos"],
        [
            str(metricas["total_produtos"]),
            str(metricas["entradas"]),
            str(metricas["saidas"]),
            str(metricas["criticos"])
        ]
    ], colWidths=[130, 100, 100, 100])
    tabela_metricas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eef2ff")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.extend([tabela_metricas, Spacer(1, 16)])

    mais_mov = df_rel.groupby("produto")["quantidade"].sum().reset_index().sort_values("quantidade", ascending=False).head(10) if not df_rel.empty else pd.DataFrame(columns=["produto", "quantidade"])
    historico = df_rel.sort_values("data", ascending=False).head(15) if not df_rel.empty else pd.DataFrame(columns=["produto", "tipo", "quantidade", "data"])

    for titulo, dados in [
        ("Gasto por cliente", df_gastos_clientes.head(20) if not df_gastos_clientes.empty else pd.DataFrame(columns=["cliente", "quantidade", "total"])),
        ("Produtos por cliente", df_gastos_detalhe.head(20) if not df_gastos_detalhe.empty else pd.DataFrame(columns=["cliente", "produto", "quantidade", "valor_unitario", "total"])),
        ("Produtos mais movimentados", mais_mov),
        ("Produtos menos movimentados", df_menos_mov.head(15) if not df_menos_mov.empty else pd.DataFrame(columns=["codigo", "produto", "categoria", "quantidade"])),
        ("Histórico", historico[["produto", "tipo", "quantidade", "data"]] if not historico.empty else pd.DataFrame(columns=["produto", "tipo", "quantidade", "data"]))
    ]:
        elementos.append(Paragraph(titulo, styles["Heading2"]))
        linhas = [list(dados.columns)]
        for _, row in dados.iterrows():
            linhas.append([str(v) for v in row.tolist()])
        tabela = Table(linhas, repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elementos.extend([tabela, Spacer(1, 14)])

    doc.build(elementos)
    buffer.seek(0)
    return buffer


def gerar_excel_relatorios(df_rel, df_criticos, df_menos_mov, df_gastos_clientes, df_gastos_detalhe, metricas):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([metricas]).to_excel(writer, sheet_name="Resumo", index=False)
        df_rel.to_excel(writer, sheet_name="Historico", index=False)
        df_gastos_clientes.to_excel(writer, sheet_name="Gasto por Cliente", index=False)
        df_gastos_detalhe.to_excel(writer, sheet_name="Produtos por Cliente", index=False)
        df_criticos.to_excel(writer, sheet_name="Produtos Criticos", index=False)
        df_menos_mov.to_excel(writer, sheet_name="Menos Movimentados", index=False)
        if not df_rel.empty:
            df_rel.groupby(["produto", "tipo"])["quantidade"].sum().reset_index().to_excel(writer, sheet_name="Mais Movimentados", index=False)
    buffer.seek(0)
    return buffer


def gerar_pdf_relatorio_frequencia(base, data_inicio, data_fim, rel_filtrado, resumo_presenca, resumo_funcao, resumo_dia, resumo_colaborador, resumo_almoco_funcao, metricas, tipo_relatorio="Completo"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    styles = getSampleStyleSheet()
    titulo_style = styles["Title"]
    titulo_style.fontSize = 15
    heading_style = styles["Heading2"]
    heading_style.fontSize = 10
    cell_style = styles["BodyText"]
    cell_style.fontSize = 6.5
    cell_style.leading = 7.5

    def texto_pdf(valor):
        if pd.isna(valor):
            return ""
        texto = str(valor).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return texto

    def tabela_pdf(df, col_widths=None, limite_linhas=None):
        dados = df.copy()
        if limite_linhas:
            dados = dados.head(limite_linhas)
        if dados.empty:
            dados = pd.DataFrame([["Sem registros"]], columns=["informacao"])
        linhas = [[Paragraph(texto_pdf(col).upper(), cell_style) for col in dados.columns]]
        for _, row in dados.iterrows():
            linhas.append([Paragraph(texto_pdf(valor), cell_style) for valor in row.tolist()])
        tabela = Table(linhas, colWidths=col_widths, repeatRows=1, splitByRow=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tabela

    elementos = [
        Paragraph(f"Relatorio De Frequencia - {texto_pdf(tipo_relatorio)}", titulo_style),
        Paragraph(f"Base: {texto_pdf(base)} | Periodo: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", styles["Normal"]),
        Spacer(1, 10)
    ]

    metricas_df = pd.DataFrame([{
        "Lancamentos": metricas["lancamentos"],
        "Presentes": metricas["presentes"],
        "Faltas": metricas["faltas"],
        "Atestados": metricas["atestados"],
        "Almocos": metricas["almocos"]
    }])
    elementos.extend([tabela_pdf(metricas_df, [110, 110, 110, 110, 110]), Spacer(1, 10)])

    secoes_pdf = [
        ("Por Presenca", "Resumo Por Presenca", resumo_presenca, [220, 80]),
        ("Por Funcao", "Resumo Por Funcao", resumo_funcao, [260, 80]),
        ("Por Dia", "Resumo Por Dia", resumo_dia, [90, 90, 90, 90, 90]),
        ("Por Colaborador", "Resumo Por Colaborador", resumo_colaborador, [200, 70, 70, 70, 70, 70]),
        ("Almoco Por Funcao", "Quantidade De Almoco Por Funcao", resumo_almoco_funcao, [260, 100]),
    ]
    for chave, titulo, dados, larguras in secoes_pdf:
        if tipo_relatorio in ["Completo", chave]:
            elementos.extend([Paragraph(titulo, heading_style), tabela_pdf(dados, larguras), Spacer(1, 10)])

    if tipo_relatorio in ["Completo", "Lancamentos Detalhados"]:
        colunas_detalhe = ["data", "colaborador", "funcao", "presenca", "motivo_falta", "almocou_base", "observacoes"]
        detalhe = rel_filtrado[colunas_detalhe].copy() if not rel_filtrado.empty else pd.DataFrame(columns=colunas_detalhe)
        elementos.extend([
            Paragraph("Lancamentos Do Periodo", heading_style),
            tabela_pdf(detalhe, [58, 145, 120, 80, 130, 62, 170])
        ])

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()


def gerar_pdf_etiquetas(itens):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    estilos = getSampleStyleSheet()
    elementos = [Paragraph("Etiquetas De Entrada", estilos["Title"]), Spacer(1, 12)]
    linhas = []
    linha = []
    for item in itens:
        etiqueta = [
            Paragraph(f"<b>{item.get('produto', '')}</b>", estilos["Normal"]),
            Paragraph(f"Código: {item.get('codigo', '')}", estilos["Normal"]),
            Paragraph(f"Quantidade: {item.get('quantidade', '')}", estilos["Normal"]),
            Paragraph(f"Data: {item.get('data', '')}", estilos["Normal"]),
        ]
        linha.append(etiqueta)
        if len(linha) == 2:
            linhas.append(linha)
            linha = []
    if linha:
        linha.append("")
        linhas.append(linha)

    tabela = Table(linhas, colWidths=[260, 260], rowHeights=92)
    tabela.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#111827")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer


def gerar_backup():
    if ambiente_producao():
        registrar_auditoria("EXPORTAR", "BACKUP", "Backup administrativo solicitado em produção", "backup_producao")
        st.warning("Em produção, o backup oficial é o PostgreSQL/Supabase. Use as exportações administrativas ou snapshots do Supabase.")
        return ""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    nome = f"backup_estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pasta_temp = os.path.join(BACKUP_DIR, nome)
    os.makedirs(pasta_temp, exist_ok=True)
    ignorar_pastas = {"backups", "__pycache__", ".git", ".venv", "venv"}
    ignorar_extensoes = {".pyc", ".tmp", ".log"}
    data_dir_abs = os.path.abspath(DATA_DIR)
    for raiz, dirs, arquivos in os.walk(DATA_DIR):
        dirs[:] = [
            pasta for pasta in dirs
            if pasta not in ignorar_pastas
        ]
        rel_raiz = os.path.relpath(raiz, data_dir_abs)
        destino_raiz = pasta_temp if rel_raiz == "." else os.path.join(pasta_temp, rel_raiz)
        os.makedirs(destino_raiz, exist_ok=True)
        for arquivo in arquivos:
            if arquivo.startswith("~$") or os.path.splitext(arquivo)[1].lower() in ignorar_extensoes:
                continue
            origem = os.path.join(raiz, arquivo)
            if os.path.abspath(origem).startswith(os.path.abspath(BACKUP_DIR)):
                continue
            shutil.copy2(origem, os.path.join(destino_raiz, arquivo))
    zip_path = shutil.make_archive(pasta_temp, "zip", pasta_temp)
    shutil.rmtree(pasta_temp, ignore_errors=True)
    destino_google_drive = copiar_backup_nuvem(zip_path)
    config["ultimo_backup"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    config["alteracao_pendente_backup"] = False
    config["ultima_alteracao"] = ""
    if destino_google_drive:
        config["ultimo_backup_google_drive"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.session_state["salvando_backup"] = True
    salvar_config_sem_marcar_backup()
    st.session_state.pop("salvando_backup", None)
    return zip_path


def solicitar_saida_com_backup():
    if ambiente_producao():
        concluir_saida()
        return
    if config.get("alteracao_pendente_backup", False):
        st.session_state["confirmar_saida_backup"] = True
        st.rerun()
    else:
        concluir_saida()


def concluir_saida():
    registrar_auditoria("LOGOUT", "AUTENTICAÇÃO", "Logout realizado", st.session_state.get("usuario_logado", {}).get("nome", ""))
    st.session_state["autenticado"] = False
    st.session_state.pop("usuario_logado", None)
    st.session_state.pop("confirmar_saida_backup", None)
    st.session_state.pop("backup_saida_gerado", None)
    if not st.session_state.get("login_salvo_ativo", False):
        st.session_state["login_salvo_usuario"] = ""
        st.session_state.pop("login_salvo_modo", None)
    st.rerun()


def tela_backup_obrigatorio_saida():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_esq, col_centro, col_dir = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown("<div class='saas-card'>", unsafe_allow_html=True)
        st.title("Backup Pendente")
        st.warning("Existem alteracoes sem backup. Gere um backup antes de sair do sistema.")
        st.caption(f"Ultimo backup registrado: {config.get('ultimo_backup', 'Nunca')}")
        if config.get("ultima_alteracao"):
            st.caption(f"Ultima alteracao: {config.get('ultima_alteracao')}")

        if st.button("Gerar Backup Agora", type="primary", use_container_width=True):
            zip_path = gerar_backup()
            st.session_state["backup_saida_gerado"] = zip_path
            st.success(f"Backup gerado com sucesso: {zip_path}")

        if st.session_state.get("backup_saida_gerado"):
            st.info("Backup concluido. Agora voce pode sair do sistema.")
            if st.button("Sair Do Sistema", use_container_width=True):
                concluir_saida()
        else:
            st.button("Sair Do Sistema", disabled=True, use_container_width=True)

        if st.button("Voltar Ao Sistema", use_container_width=True):
            st.session_state.pop("confirmar_saida_backup", None)
            st.session_state.pop("backup_saida_gerado", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def executar_backup_automatico_diario():
    if ambiente_producao():
        return
    if st.session_state.get("backup_automatico_verificado"):
        return
    st.session_state["backup_automatico_verificado"] = True
    if not config.get("backup_automatico_diario", True):
        return
    ultimo = pd.to_datetime(config.get("ultimo_backup", ""), dayfirst=True, errors="coerce")
    hoje = datetime.now().date()
    if pd.isna(ultimo) or ultimo.date() < hoje:
        try:
            caminho_backup = gerar_backup()
            registrar_auditoria("BACKUP_AUTOMATICO", "BACKUP", caminho_backup, os.path.basename(caminho_backup))
        except Exception as erro:
            st.session_state["erro_backup_automatico"] = str(erro)[:500]


executar_backup_automatico_diario()


def nomes_responsaveis_frota(valor):
    nomes = []
    texto = str(valor or "")
    for separador in [";", "/", "|"]:
        texto = texto.replace(separador, ",")
    for nome in texto.split(","):
        nome_limpo = nome.strip().title()
        if nome_limpo:
            nomes.append(nome_limpo)
    return nomes


def salvar_anexo_frota(arquivo, placa, tipo_lancamento):
    if not arquivo:
        return ""
    nome_original = os.path.basename(arquivo.name)
    nome_limpo = "".join(caractere for caractere in nome_original if caractere.isalnum() or caractere in "._- ").strip()
    placa_limpa = "".join(caractere for caractere in str(placa) if caractere.isalnum() or caractere in "-_").strip()
    prefixo = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_storage = f"Anexos Frotas/{prefixo}_{placa_limpa}_{tipo_lancamento}_{nome_limpo}"
    if ambiente_producao():
        dados = arquivo.getbuffer()
        content_type = getattr(arquivo, "type", None) or mimetypes.guess_type(nome_limpo)[0] or "application/octet-stream"
        if not upload_arquivo_storage(caminho_storage, dados, content_type):
            erro = st.session_state.get("ultimo_erro_supabase", "")
            st.error(f"Erro ao enviar anexo para o Supabase Storage. {erro}")
            st.stop()
        registrar_auditoria("UPLOAD", "STORAGE", "Anexo de frota enviado ao Supabase Storage", caminho_storage)
        return caminho_storage
    os.makedirs(PASTA_ANEXOS_FROTAS, exist_ok=True)
    caminho = os.path.join(PASTA_ANEXOS_FROTAS, os.path.basename(caminho_storage))
    with open(caminho, "wb") as destino:
        destino.write(arquivo.getbuffer())
    upload_arquivo_remoto(caminho)
    marcar_backup_pendente(caminho)
    registrar_auditoria("UPLOAD", "STORAGE", "Anexo de frota salvo", drive_relativo(caminho))
    return drive_relativo(caminho)


def resolver_caminho_anexo(valor):
    caminho = str(valor or "").strip()
    if not caminho:
        return ""
    if caminho.lower().startswith(("http://", "https://")):
        return caminho
    if os.path.isabs(caminho) and os.path.exists(caminho):
        return caminho
    caminho_relativo = caminho.replace("\\", os.sep).replace("/", os.sep)
    candidatos = [
        os.path.join(DATA_DIR, caminho_relativo),
        os.path.join(PASTA_ANEXOS_FROTAS, os.path.basename(caminho_relativo)),
    ]
    for candidato in candidatos:
        if os.path.exists(candidato):
            return candidato
    return candidatos[0]


def salvar_imagem_produto(arquivo, codigo, produto):
    if not arquivo:
        return ""
    extensao = os.path.splitext(arquivo.name)[1].lower()
    nome_base = f"{codigo}_{produto}".strip()
    nome_base = "".join(caractere for caractere in nome_base if caractere.isalnum() or caractere in "._- ").strip()
    nome_base = nome_base.replace(" ", "_") or datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{nome_base}{extensao}"
    if ambiente_producao():
        url_supabase = supabase_upload_imagem_produto(arquivo, nome_arquivo)
        if not url_supabase:
            erro = st.session_state.get("ultimo_erro_supabase", "")
            st.error(f"Erro ao enviar imagem para o Supabase Storage. {erro}")
            st.stop()
        registrar_auditoria("UPLOAD", "STORAGE", "Imagem de produto enviada ao Supabase Storage", nome_arquivo)
        return url_supabase
    os.makedirs(PASTA_IMAGENS, exist_ok=True)
    caminho = os.path.join(PASTA_IMAGENS, nome_arquivo)
    contador = 1
    while os.path.exists(caminho):
        nome_arquivo = f"{nome_base}_{contador}{extensao}"
        caminho = os.path.join(PASTA_IMAGENS, nome_arquivo)
        contador += 1
    with open(caminho, "wb") as destino:
        destino.write(arquivo.getbuffer())
    url_supabase = supabase_upload_imagem_produto(arquivo, nome_arquivo) if supabase_configurado() else ""
    if url_supabase:
        st.success("Imagem enviada para o Supabase.")
    elif supabase_configurado():
        erro_supabase = st.session_state.get("ultimo_erro_supabase", "")
        detalhe = f" Detalhe: {erro_supabase}" if erro_supabase else ""
        st.warning(f"Produto salvo sem imagem online. A imagem ficou salva apenas localmente.{detalhe}")
    if not url_supabase and not upload_arquivo_remoto(caminho):
        erro_remoto = st.session_state.get("ultimo_erro_supabase", "") or st.session_state.get("ultimo_erro_google_drive", "")
        detalhe = f" Detalhe: {erro_remoto}" if erro_remoto else ""
        st.warning(f"Imagem salva, mas não foi enviada ao armazenamento online.{detalhe}")
    marcar_backup_pendente(caminho)
    return url_supabase or nome_arquivo


def origem_imagem_produto(valor):
    imagem = str(valor or "").strip()
    if not imagem:
        return ""
    if imagem.lower().startswith(("http://", "https://")):
        return imagem
    caminho = os.path.join(PASTA_IMAGENS, imagem)
    return caminho if os.path.exists(caminho) else ""


def exibir_anexo_nota(caminho, chave):
    caminho_original = str(caminho or "").strip()
    if not caminho_original:
        st.caption("Sem nota anexada.")
        return
    if caminho_original.lower().startswith(("http://", "https://")):
        st.link_button("Abrir Anexo", caminho_original, use_container_width=True)
        return
    if ambiente_producao() and supabase_configurado():
        url = baixar_url_arquivo(caminho_original)
        if url:
            st.link_button("Abrir Anexo", url, use_container_width=True)
            return
    caminho = resolver_caminho_anexo(caminho_original)
    if not os.path.exists(caminho):
        st.warning("Nota anexada não encontrada no computador.")
        st.caption(caminho_original)
        return

    nome = os.path.basename(caminho)
    extensao = os.path.splitext(caminho)[1].lower()
    with open(caminho, "rb") as arquivo:
        dados = arquivo.read()

    st.download_button(
        "Abrir / Baixar Nota",
        data=dados,
        file_name=nome,
        mime="application/pdf" if extensao == ".pdf" else "image/*",
        key=chave,
        use_container_width=True
    )
    if extensao in [".png", ".jpg", ".jpeg", ".webp"]:
        st.image(caminho, caption=nome, use_container_width=True)


def exibir_consulta_abastecimentos(df_abastecimentos, titulo="Histórico De Abastecimentos"):
    st.subheader(titulo)
    if df_abastecimentos.empty:
        st.info("Nenhum abastecimento registrado.")
        return

    for idx, row in df_abastecimentos.reset_index(drop=True).iterrows():
        data = row.get("data", "")
        placa = row.get("placa", "")
        valor = pd.to_numeric(row.get("valor_total", 0), errors="coerce")
        valor = 0 if pd.isna(valor) else float(valor)
        with st.expander(f"{data} | {placa} | R$ {valor:,.2f}", expanded=False):
            dados = pd.DataFrame([row.to_dict()])
            if "nota_anexo" in dados.columns:
                dados = dados.drop(columns=["nota_anexo"])
            st.dataframe(formatar_colunas_tabela(dados), use_container_width=True, hide_index=True)
            exibir_anexo_nota(row.get("nota_anexo", ""), f"nota_abastecimento_{idx}_{placa}_{data}")


def exibir_conferencia_lancamentos(tipo, df_lancamentos, arquivo_destino):
    global df_frotas_abastecimentos, df_frotas_manutencoes

    if df_lancamentos.empty:
        st.info(f"Nenhum lançamento de {tipo.lower()} encontrado.")
        return

    status_filtro = st.selectbox(
        f"Status De Conferência - {tipo}",
        ["Pendentes", "Todos", "Aprovados", "Reprovados"],
        key=f"filtro_conferencia_{tipo}"
    )
    dados = df_lancamentos.copy()
    if status_filtro == "Pendentes":
        dados = dados[dados["status_conferencia"].astype(str) == "Pendente"]
    elif status_filtro == "Aprovados":
        dados = dados[dados["status_conferencia"].astype(str) == "Aprovado"]
    elif status_filtro == "Reprovados":
        dados = dados[dados["status_conferencia"].astype(str) == "Reprovado"]

    if dados.empty:
        st.info("Nenhum lançamento neste filtro.")
        return

    for idx, row in dados.iterrows():
        valor_coluna = "valor_total" if tipo == "Abastecimento" else "valor"
        valor = pd.to_numeric(row.get(valor_coluna, 0), errors="coerce")
        valor = 0 if pd.isna(valor) else float(valor)
        titulo = f"{row.get('status_conferencia', 'Pendente')} | {row.get('data', '')} | {row.get('placa', '')} | R$ {valor:,.2f}"
        with st.expander(titulo, expanded=str(row.get("status_conferencia", "")) == "Pendente"):
            tabela = pd.DataFrame([row.to_dict()])
            if "nota_anexo" in tabela.columns:
                tabela = tabela.drop(columns=["nota_anexo"])
            st.dataframe(formatar_colunas_tabela(tabela), use_container_width=True, hide_index=True)
            exibir_anexo_nota(row.get("nota_anexo", ""), f"nota_conferencia_{tipo}_{idx}")

            status_atual = str(row.get("status_conferencia", "Pendente"))
            status_opcoes = ["Pendente", "Aprovado", "Reprovado"]
            status_novo = st.selectbox(
                "Status",
                status_opcoes,
                index=status_opcoes.index(status_atual) if status_atual in status_opcoes else 0,
                key=f"status_conf_{tipo}_{idx}"
            )
            observacao_admin = st.text_area(
                "Observação Do Administrativo",
                value=str(row.get("observacao_administrativo", "")),
                key=f"obs_conf_{tipo}_{idx}"
            ).strip()

            if st.button("SALVAR CONFERÊNCIA", type="primary", use_container_width=True, key=f"salvar_conf_{tipo}_{idx}"):
                df_lancamentos.loc[idx, "status_conferencia"] = status_novo
                df_lancamentos.loc[idx, "observacao_administrativo"] = observacao_admin
                df_lancamentos.to_excel(arquivo_destino, index=False)
                if tipo == "Abastecimento":
                    df_frotas_abastecimentos = df_lancamentos
                else:
                    df_frotas_manutencoes = df_lancamentos
                st.success("Conferência salva.")
                st.rerun()


def tela_responsavel_frota():
    global df_frotas_abastecimentos, df_frotas_manutencoes, df_frotas_veiculos

    usuario = st.session_state.get("usuario_logado", {})
    veiculos_permitidos_usuario = usuario.get("veiculos_frota", [])
    if isinstance(veiculos_permitidos_usuario, str):
        veiculos_permitidos_usuario = [veiculos_permitidos_usuario] if veiculos_permitidos_usuario.strip() else []
    veiculo_permitido_antigo = str(usuario.get("veiculo_frota", "")).strip()
    if veiculo_permitido_antigo and veiculo_permitido_antigo not in veiculos_permitidos_usuario:
        veiculos_permitidos_usuario.append(veiculo_permitido_antigo)
    placas_ativas_responsavel = df_frotas_veiculos[df_frotas_veiculos["status"] != "Inativo"]["placa"].dropna().astype(str).tolist()
    placas_ativas_responsavel = [p for p in placas_ativas_responsavel if p.strip()]

    if veiculos_permitidos_usuario:
        placas_permitidas = [p for p in veiculos_permitidos_usuario if p in placas_ativas_responsavel]
    else:
        placas_permitidas = placas_ativas_responsavel

    st.title("Lançamento De Despesa")
    st.caption(f"Usuário: {usuario.get('nome', '')}")
    feedback_lancamento = st.session_state.get("feedback_lancamento")
    if feedback_lancamento:
        if feedback_lancamento.get("tipo") == "sucesso":
            st.success(feedback_lancamento.get("mensagem", "Lançamento salvo com sucesso."))
            if st.button("OK", type="primary", use_container_width=True, key="ok_feedback_lancamento"):
                st.session_state.pop("feedback_lancamento", None)
                st.rerun()
        else:
            st.error(feedback_lancamento.get("mensagem", "Não foi possível salvar o lançamento."))
            if st.button("OK", type="primary", use_container_width=True, key="ok_erro_lancamento"):
                st.session_state.pop("feedback_lancamento", None)
                st.rerun()

    if not placas_permitidas:
        st.error("Nenhum veículo ativo foi liberado para este usuário. Fale com o administrador.")
        return

    tipo_lancamento = st.radio("Tipo De Lançamento", ["Abastecimento", "Manutenção"], horizontal=True)
    placa = st.selectbox("Veículo", placas_permitidas)
    veiculo_lancamento = df_frotas_veiculos[df_frotas_veiculos["placa"].astype(str) == str(placa)]
    responsavel_padrao = str(veiculo_lancamento.iloc[0].get("responsavel", "")).strip().title() if not veiculo_lancamento.empty else ""
    responsavel_lancamento = st.text_input(
        "Responsável Pelo Lançamento",
        value=responsavel_padrao or str(usuario.get("nome", "")).strip().title()
    ).strip().title()

    if tipo_lancamento == "Abastecimento":
        data = st.date_input("Data", value=datetime.now().date(), key="resp_abast_data")
        km = st.number_input("Km", min_value=0, value=0, key="resp_abast_km")
        combustivel = st.selectbox("Combustível", ["Gasolina", "Etanol", "Diesel", "GNV", "Outro"], key="resp_abast_combustivel")
        litros = st.number_input("Litros", min_value=0.0, step=0.01, format="%.2f", key="resp_abast_litros")
        valor_litro = st.number_input("Valor Por Litro", min_value=0.0, step=0.01, format="%.2f", key="resp_abast_valor_litro")
        valor_total = float(litros) * float(valor_litro)
        posto = st.text_input("Posto", key="resp_abast_posto").strip().title()
        observacoes = st.text_area("Observações", key="resp_abast_obs").strip()
        nota_anexo = st.file_uploader(
            "Foto Do Hodômetro",
            type=["png", "jpg", "jpeg", "webp"],
            key="resp_abast_nota"
        )
        st.metric("Valor Total", f"R$ {valor_total:,.2f}")

        if st.button("SALVAR ABASTECIMENTO", type="primary", use_container_width=True):
            if not responsavel_lancamento:
                st.error("Informe o responsável pelo lançamento.")
            elif not placa:
                st.error("Selecione o veículo.")
            elif km <= 0:
                st.error("Informe o km.")
            elif not combustivel:
                st.error("Informe o combustível.")
            elif litros <= 0:
                st.error("Informe a quantidade de litros.")
            elif valor_litro <= 0:
                st.error("Informe o valor por litro.")
            elif not posto:
                st.error("Informe o posto.")
            elif not observacoes:
                st.error("Informe as observações.")
            elif not nota_anexo:
                st.error("Anexe a foto do hodômetro para salvar o abastecimento.")
            else:
                caminho_nota = salvar_anexo_frota(nota_anexo, placa, "hodometro_abastecimento")
                novo = pd.DataFrame([{
                    "data": data.isoformat(),
                    "placa": placa,
                    "km": int(km),
                    "combustivel": combustivel,
                    "litros": float(litros),
                    "valor_litro": float(valor_litro),
                    "valor_total": float(valor_total),
                    "posto": posto,
                    "responsavel_lancamento": responsavel_lancamento,
                    "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "nota_anexo": caminho_nota,
                    "status_conferencia": "Pendente",
                    "observacao_administrativo": "",
                    "observacoes": observacoes
                }])
                df_frotas_abastecimentos = pd.concat([df_frotas_abastecimentos, novo], ignore_index=True)
                df_frotas_abastecimentos.to_excel(FROTAS_ABASTECIMENTOS_XLSX, index=False)
                df_frotas_veiculos.loc[df_frotas_veiculos["placa"].astype(str) == placa, "km_atual"] = int(km)
                df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                st.session_state["feedback_lancamento"] = {
                    "tipo": "sucesso",
                    "mensagem": "Abastecimento salvo com sucesso."
                }
                st.rerun()
    else:
        data = st.date_input("Data", value=datetime.now().date(), key="resp_manut_data")
        tipo_manutencao = st.selectbox("Tipo De Manutenção", ["Preventiva", "Corretiva"], key="resp_manut_tipo")
        km = st.number_input("Km", min_value=0, value=0, key="resp_manut_km")
        servico_executado = st.text_input("Serviço Executado", key="resp_manut_servico").strip().title()
        fornecedor = st.text_input("Fornecedor/Oficina", key="resp_manut_fornecedor").strip().title()
        valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f", key="resp_manut_valor")
        observacoes = st.text_area("Observações", key="resp_manut_obs").strip()
        nota_anexo = st.file_uploader(
            "Anexar Nota",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key="resp_manut_nota"
        )

        if st.button("SALVAR MANUTENÇÃO", type="primary", use_container_width=True):
            if not responsavel_lancamento:
                st.error("Informe o responsável pelo lançamento.")
            elif not placa:
                st.error("Selecione o veículo.")
            elif not tipo_manutencao:
                st.error("Informe o tipo de manutenção.")
            elif km <= 0:
                st.error("Informe o km.")
            elif not servico_executado:
                st.error("Informe o serviço executado.")
            elif not fornecedor:
                st.error("Informe o fornecedor/oficina.")
            elif valor <= 0:
                st.error("Informe o valor.")
            elif not observacoes:
                st.error("Informe as observações.")
            elif not nota_anexo:
                st.error("Anexe a nota.")
            else:
                if tipo_manutencao == "Preventiva":
                    df_frotas_manutencoes = baixar_manutencoes_programadas(df_frotas_manutencoes, placa, data)
                caminho_nota = salvar_anexo_frota(nota_anexo, placa, "manutencao")
                novo = pd.DataFrame([{
                    "data": data.isoformat(),
                    "placa": placa,
                    "tipo_manutencao": tipo_manutencao,
                    "km": int(km),
                    "servico_executado": servico_executado,
                    "fornecedor": fornecedor,
                    "valor": float(valor),
                    "manutencao_agendada": "",
                    "proxima_revisao": "",
                    "status_manutencao": "Executada",
                    "responsavel_lancamento": responsavel_lancamento,
                    "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "nota_anexo": caminho_nota,
                    "status_conferencia": "Pendente",
                    "observacao_administrativo": "",
                    "observacoes": observacoes
                }])
                df_frotas_manutencoes = pd.concat([df_frotas_manutencoes, novo], ignore_index=True)
                df_frotas_manutencoes.to_excel(FROTAS_MANUTENCOES_XLSX, index=False)
                st.session_state["feedback_lancamento"] = {
                    "tipo": "sucesso",
                    "mensagem": "Manutenção salva com sucesso."
                }
                st.rerun()


# =========================
# MENU
# =========================
ICONES_MENU = {
    "INICIO": "🏠",
    "ALMOXARIFADO": "📦",
    "BASES": "🏢",
    "FROTAS": "🚚",
    "CONFIGURAÇÕES": "⚙️",
    "ESTOQUE": "📊",
    "COMPRAS": "🛒",
    "MOVIMENTAÇÃO": "🔁",
    "PRODUTOS": "🏷️",
    "CLIENTES": "👥",
    "FORNECEDOR": "🤝",
    "RELATÓRIOS": "📈",
    "PAINEL": "📍",
    "VEÍCULOS": "🚘",
    "ENTREGA DE VEÍCULO": "📝",
    "VISTORIAS": "✅",
    "ABASTECIMENTOS": "⛽",
    "MANUTENÇÕES": "🛠️",
    "CONFERÊNCIA": "🔎",
    "DOCUMENTOS": "📄",
    "MINHA BASE": "🏢",
    "LISTA DE FREQUÊNCIA": "📋",
    "DESPESAS FROTAS": "💳",
}


def rotulo_menu(item):
    return f"{ICONES_MENU.get(item, '•')} {item.title()}"


if os.path.exists(LOGIN_LOGO_IMAGE):
    st.sidebar.image(LOGIN_LOGO_IMAGE, use_container_width=True)
else:
    st.sidebar.title("ALPES")
usuario_logado = st.session_state.get("usuario_logado", {})
st.sidebar.caption(f"{usuario_logado.get('nome', '')} | {usuario_logado.get('nivel', '')}")

if st.session_state.get("confirmar_saida_backup"):
    tela_backup_obrigatorio_saida()

if usuario_eh_motorista(usuario_logado):
    st.sidebar.divider()
    st.sidebar.markdown("<span class='status-pill'>Acesso restrito</span>", unsafe_allow_html=True)
    if st.sidebar.button("Sair", use_container_width=True):
        solicitar_saida_com_backup()
    tela_responsavel_frota()
    st.stop()

supervisor_base_mode = usuario_eh_supervisor_base(usuario_logado)

if supervisor_base_mode:
    bases_supervisor = usuario_logado.get("bases_permitidas", [])
    if isinstance(bases_supervisor, str):
        bases_supervisor = [bases_supervisor] if bases_supervisor.strip() else []
    bases_supervisor = [base for base in bases_supervisor if base in BASES_FREQUENCIA]
    base_supervisor = bases_supervisor[0] if bases_supervisor else ""

    st.session_state["menu"] = "BASES"
    st.session_state["base_faltas_selecionada"] = base_supervisor
    opcoes_supervisor = ["MINHA BASE", "LISTA DE FREQUÊNCIA", "ESTOQUE", "DESPESAS FROTAS"]

    escolha_supervisor = st.sidebar.radio(
        "Menu Supervisor",
        opcoes_supervisor,
        label_visibility="collapsed",
        key="menu_supervisor_base",
        format_func=rotulo_menu
    )
    subtela_supervisor_atual = st.session_state.get("subtela_faltas", "")
    if escolha_supervisor == "MINHA BASE":
        st.session_state["subtela_faltas"] = ""
    elif escolha_supervisor == "LISTA DE FREQUÊNCIA" and subtela_supervisor_atual in ["COLABORADORES", "RELATORIOS_FREQUENCIA"]:
        st.session_state["subtela_faltas"] = subtela_supervisor_atual
    else:
        st.session_state["subtela_faltas"] = escolha_supervisor
    menu = "BASES"
else:
    if "menu" not in st.session_state:
        st.session_state["menu"] = "INICIO"
    if st.session_state["menu"] == "CADASTRO DE PRODUTOS":
        st.session_state["menu"] = "PRODUTOS"

    modulos_menu = ["INICIO", "ALMOXARIFADO", "BASES", "FROTAS", "CONFIGURAÇÕES"]
    permissoes_modulos = modulos_permitidos_usuario(usuario_logado)
    modulos_menu = [modulo_item for modulo_item in modulos_menu if modulo_item in permissoes_modulos] or ["INICIO"]
    opcoes_almoxarifado = [
        "ESTOQUE",
        "COMPRAS",
        "MOVIMENTAÇÃO",
        "PRODUTOS",
        "CLIENTES",
        "FORNECEDOR",
        "RELATÓRIOS"
    ]
    opcoes_frotas = [
        "PAINEL",
        "VEÍCULOS",
        "ENTREGA DE VEÍCULO",
        "VISTORIAS",
        "ABASTECIMENTOS",
        "MANUTENÇÕES",
        "CONFERÊNCIA",
        "DOCUMENTOS",
        "RELATÓRIOS"
    ]
    if nivel_usuario(usuario_logado) == "ADM":
        opcoes_frotas = ["CONFERÊNCIA", "RELATÓRIOS"]

    if "modulo_menu" not in st.session_state:
        if st.session_state["menu"] in opcoes_almoxarifado:
            st.session_state["modulo_menu"] = "ALMOXARIFADO"
        elif st.session_state["menu"] in ["CONTROLE DE FALTAS", "BASES"]:
            st.session_state["modulo_menu"] = "BASES"
        elif st.session_state["menu"] == "FROTAS":
            st.session_state["modulo_menu"] = "FROTAS"
        elif st.session_state["menu"] == "CONFIGURAÇÕES":
            st.session_state["modulo_menu"] = "CONFIGURAÇÕES"
        else:
            st.session_state["modulo_menu"] = "INICIO"

    modulo = st.sidebar.radio(
        "Menu principal",
        modulos_menu,
        index=modulos_menu.index(st.session_state["modulo_menu"]) if st.session_state["modulo_menu"] in modulos_menu else 0,
        label_visibility="collapsed",
        format_func=rotulo_menu
    )
    st.session_state["modulo_menu"] = modulo

    if modulo == "ALMOXARIFADO":
        st.sidebar.caption("Almoxarifado - Estoque Matriz")
        menu_atual = st.session_state["menu"] if st.session_state["menu"] in opcoes_almoxarifado else "ESTOQUE"
        menu = st.sidebar.radio(
            "Opções do almoxarifado",
            opcoes_almoxarifado,
            index=opcoes_almoxarifado.index(menu_atual),
            label_visibility="collapsed",
            format_func=rotulo_menu
        )
    elif modulo == "BASES":
        menu = "BASES"
    elif modulo == "FROTAS":
        st.sidebar.caption("Frotas")
        subtela_frotas_atual = st.session_state.get("subtela_frotas", "PAINEL")
        if subtela_frotas_atual not in opcoes_frotas:
            subtela_frotas_atual = opcoes_frotas[0]
        st.session_state["subtela_frotas"] = st.sidebar.radio(
            "Opções de frotas",
            opcoes_frotas,
            index=opcoes_frotas.index(subtela_frotas_atual),
            label_visibility="collapsed",
            format_func=rotulo_menu
        )
        menu = "FROTAS"
    elif modulo == "CONFIGURAÇÕES":
        menu = "CONFIGURAÇÕES"
    else:
        menu = "INICIO"

    st.session_state["menu"] = menu

menus_validos = set(["INICIO", "ESTOQUE", "COMPRAS", "MOVIMENTAÇÃO", "PRODUTOS", "CLIENTES", "FORNECEDOR", "RELATÓRIOS", "BASES", "FROTAS", "CONFIGURAÇÕES"])
if menu not in menus_validos:
    st.session_state["menu"] = "INICIO"
    menu = "INICIO"

st.sidebar.divider()
total_criticos_sidebar = int((df_produtos["estoque_atual"] <= df_produtos["estoque_minimo"]).sum()) if not df_produtos.empty else 0
st.sidebar.markdown("<span class='status-pill'>Sistema online</span>", unsafe_allow_html=True)
backup_pendente = bool(config.get("alteracao_pendente_backup", False))
status_backup = "Pendente" if backup_pendente else "Atualizado"
st.sidebar.caption(f"Último backup: {config.get('ultimo_backup', 'Nunca')}")
st.sidebar.caption(f"Status do backup: {status_backup}")
st.sidebar.caption(f"Itens críticos: {total_criticos_sidebar}")
st.sidebar.markdown("<div class='sidebar-mini-chart'></div>", unsafe_allow_html=True)
st.sidebar.markdown(
    """
    <div class='sidebar-help'>
        ? &nbsp; Central de Ajuda<br>
        <span>Suporte WhatsApp: (66) 99643-5753</span>
    </div>
    """,
    unsafe_allow_html=True
)

if st.sidebar.button("Sair", use_container_width=True):
    solicitar_saida_com_backup()

erros_leitura_dados = st.session_state.get("erros_leitura_dados", [])
if erros_leitura_dados:
    with st.expander("Atenção: Falha Ao Ler Algum Arquivo De Dados", expanded=False):
        st.warning("O sistema manteve a tela funcionando, mas encontrou erro ao abrir um arquivo. Verifique antes de continuar lançamentos importantes.")
        for erro_dado in erros_leitura_dados[-8:]:
            st.code(erro_dado)

if supabase_configurado() and st.session_state.get("ultimo_erro_supabase"):
    with st.expander("Atenção: Supabase Não Sincronizou Algum Item", expanded=False):
        st.warning(st.session_state.get("ultimo_erro_supabase"))


# =========================
# INICIO
# =========================
if menu == "INICIO":
    imagem_inicio = HOME_IMAGE if os.path.exists(HOME_IMAGE) else HOME_IMAGE_FALLBACK
    if os.path.exists(imagem_inicio):
        extensao_inicio = os.path.splitext(imagem_inicio)[1].lower().replace(".", "") or "jpg"
        mime_inicio = "jpeg" if extensao_inicio in {"jpg", "jpeg"} else extensao_inicio
        st.markdown(
            f"""
            <style>
            .home-hero {{
                --home-image: url("data:image/{mime_inicio};base64,{imagem_base64(imagem_inicio)}");
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"Imagem não encontrada: {HOME_IMAGE}. Verifique se o caminho está correto e a imagem existe.")

    alertas_inicio_preventiva = alertas_manutencao_preventiva(df_frotas_manutencoes)
    assinatura_alerta_inicio = assinatura_alertas_preventiva(alertas_inicio_preventiva)
    alerta_inicio_oculto = (
        assinatura_alerta_inicio
        and st.session_state.get("alerta_preventiva_ok") == assinatura_alerta_inicio
    )
    alertas_inicio_vistorias = alertas_vistorias_veiculos(df_frotas_veiculos)
    assinatura_alerta_vistorias_inicio = assinatura_alertas_vistorias(alertas_inicio_vistorias)
    alerta_vistorias_inicio_oculto = (
        assinatura_alerta_vistorias_inicio
        and st.session_state.get("alerta_vistorias_ok") == assinatura_alerta_vistorias_inicio
    )
    assinatura_lancamentos_inicio = assinatura_conferencia_frotas(df_frotas_abastecimentos, df_frotas_manutencoes)
    alerta_lancamentos_oculto = (
        assinatura_lancamentos_inicio
        and st.session_state.get("alerta_lancamentos_frota_ok") == assinatura_lancamentos_inicio
    )

    if assinatura_alerta_inicio and not alerta_inicio_oculto:
        vencidas_inicio = alertas_inicio_preventiva[alertas_inicio_preventiva["status"] == "Vencida"]
        vencendo_inicio = alertas_inicio_preventiva[alertas_inicio_preventiva["status"] != "Vencida"]
        if not vencidas_inicio.empty:
            placas_vencidas = ", ".join(vencidas_inicio["placa"].astype(str).tolist())
            st.error(f"Manutenção preventiva vencida: {placas_vencidas}. Registrar execução da preventiva para encerrar o alerta.")
        if not vencendo_inicio.empty:
            placas_vencendo = ", ".join(vencendo_inicio["placa"].astype(str).tolist())
            st.warning(f"Manutenção preventiva vencendo em até 10 dias: {placas_vencendo}.")
        st.dataframe(formatar_colunas_tabela(alertas_inicio_preventiva), use_container_width=True, hide_index=True)
        if st.button("OK", type="primary", key="ok_alerta_preventiva_inicio"):
            st.session_state["alerta_preventiva_ok"] = assinatura_alerta_inicio
            st.rerun()

    if assinatura_alerta_vistorias_inicio and not alerta_vistorias_inicio_oculto:
        vistorias_vencidas_inicio = alertas_inicio_vistorias[alertas_inicio_vistorias["status"] == "Vencida"]
        vistorias_vencendo_inicio = alertas_inicio_vistorias[alertas_inicio_vistorias["status"] != "Vencida"]
        if not vistorias_vencidas_inicio.empty:
            placas_vencidas = ", ".join(vistorias_vencidas_inicio["placa"].astype(str).tolist())
            st.error(f"Vistoria de veículo vencida: {placas_vencidas}. Registre a vistoria para encerrar o alerta.")
        if not vistorias_vencendo_inicio.empty:
            placas_vencendo = ", ".join(vistorias_vencendo_inicio["placa"].astype(str).tolist())
            st.warning(f"Vistoria de veículo vencendo em até 10 dias: {placas_vencendo}.")
        st.dataframe(formatar_colunas_tabela(alertas_inicio_vistorias), use_container_width=True, hide_index=True)
        if st.button("OK", type="primary", key="ok_alerta_vistoria_inicio"):
            st.session_state["alerta_vistorias_ok"] = assinatura_alerta_vistorias_inicio
            st.rerun()

    if assinatura_lancamentos_inicio and not alerta_lancamentos_oculto:
        pend_abast_inicio = int((df_frotas_abastecimentos["status_conferencia"].astype(str) == "Pendente").sum()) if not df_frotas_abastecimentos.empty else 0
        pend_manut_inicio = int((df_frotas_manutencoes["status_conferencia"].astype(str) == "Pendente").sum()) if not df_frotas_manutencoes.empty else 0
        st.warning(
            f"Novos lançamentos de frota aguardando conferência: "
            f"{pend_abast_inicio} abastecimento(s) e {pend_manut_inicio} manutenção(ões)."
        )

        resumo_lancamentos_inicio = []
        if pend_abast_inicio:
            abast_pend = df_frotas_abastecimentos[df_frotas_abastecimentos["status_conferencia"].astype(str) == "Pendente"].copy()
            abast_pend["tipo"] = "Abastecimento"
            abast_pend["valor"] = abast_pend["valor_total"]
            resumo_lancamentos_inicio.append(abast_pend[["tipo", "placa", "responsavel_lancamento", "registrado_em", "valor"]])
        if pend_manut_inicio:
            manut_pend = df_frotas_manutencoes[df_frotas_manutencoes["status_conferencia"].astype(str) == "Pendente"].copy()
            manut_pend["tipo"] = "Manutenção"
            resumo_lancamentos_inicio.append(manut_pend[["tipo", "placa", "responsavel_lancamento", "registrado_em", "valor"]])
        if resumo_lancamentos_inicio:
            resumo_lancamentos_inicio = pd.concat(resumo_lancamentos_inicio, ignore_index=True)
            st.dataframe(formatar_colunas_tabela(resumo_lancamentos_inicio), use_container_width=True, hide_index=True)

        if st.button("OK", type="primary", key="ok_alerta_lancamentos_frota_inicio"):
            st.session_state["alerta_lancamentos_frota_ok"] = assinatura_lancamentos_inicio
            st.rerun()

    faltas_mes = 0
    if not df_faltas.empty:
        datas_faltas_inicio = pd.to_datetime(df_faltas["data"], errors="coerce")
        mes_atual = datetime.now().month
        ano_atual = datetime.now().year
        faltas_mes = int(((datas_faltas_inicio.dt.month == mes_atual) & (datas_faltas_inicio.dt.year == ano_atual) & (df_faltas["presenca"].astype(str).str.upper() == "FALTA")).sum())
    produtos_criticos_inicio = int((df_produtos["estoque_atual"] <= df_produtos["estoque_minimo"]).sum()) if not df_produtos.empty else 0
    despesas_pendentes_inicio = int((df_frotas_abastecimentos["status_conferencia"].astype(str) == "Pendente").sum()) + int((df_frotas_manutencoes["status_conferencia"].astype(str) == "Pendente").sum())
    frequencias_hoje = 0
    if not df_faltas.empty:
        frequencias_hoje = int((pd.to_datetime(df_faltas["data"], errors="coerce").dt.date == datetime.now().date()).sum())
    status_backup_inicio = "Pendente" if config.get("alteracao_pendente_backup", False) else "Atualizado"
    auditoria_inicio = carregar_json(AUDITORIA_JSON, [])
    logo_home_html = ""
    if os.path.exists(LOGIN_LOGO_IMAGE):
        extensao_logo_home = os.path.splitext(LOGIN_LOGO_IMAGE)[1].lower().replace(".", "") or "png"
        mime_logo_home = "jpeg" if extensao_logo_home in {"jpg", "jpeg"} else extensao_logo_home
        logo_home_html = (
            f"<img src='data:image/{mime_logo_home};base64,{imagem_base64(LOGIN_LOGO_IMAGE)}' "
            "alt='ALPES Gestão e Facilities'>"
        )
    nome_usuario_topbar = escape_html(usuario_logado.get("nome", "Mestre") or "Mestre")
    nivel_usuario_topbar = escape_html(usuario_logado.get("nivel", "Administrador") or "Administrador")
    agora_topbar = datetime.now()

    st.markdown(
        f"""
        <div class='alpes-topbar'>
            <div class='top-icon'>☰</div>
            <div class='alpes-search'>⌕ Buscar módulos, registros, ações... <span class='alpes-kbd'>CTRL + K</span></div>
            <div class='topbar-right'>
                <div class='top-icon'>♢</div>
                <div class='top-icon'>▣</div>
                <div class='user-avatar'>{escape_html(nome_usuario_topbar[:1].upper())}</div>
                <div class='user-meta'><strong>{nome_usuario_topbar}</strong><span>{nivel_usuario_topbar}</span></div>
                <div class='premium-select-pill'>{agora_topbar.strftime('%d/%m/%Y')} &nbsp; ◷ {agora_topbar.strftime('%H:%M')}</div>
            </div>
        </div>
        <section class='premium-hero'>
            <div>
                <h1>Alpes Gestão e Instalações</h1>
                <p>Central corporativa para almoxarifado, bases operacionais, frotas, auditorias e indicadores de gestão.</p>
                <div class='premium-badges'>
                    <span>● Sistema online</span>
                    <span>Backup: {escape_html(status_backup_inicio)}</span>
                    <span>Itens críticos: {produtos_criticos_inicio}</span>
                    <span>{nivel_usuario_topbar}</span>
                </div>
            </div>
            <div class='hero-logo-panel'>
                {logo_home_html}
                <div class='hero-watermark'>ALPES</div>
            </div>
        </section>
        <div class='premium-kpi-grid'>
            <div class='premium-kpi'>
                <div class='kpi-icon'>↘</div>
                <div class='kpi-label'>Faltas no mês</div>
                <div class='kpi-value'>{faltas_mes}</div>
                <div class='kpi-trend'>↘ -100% vs mês anterior</div>
            </div>
            <div class='premium-kpi'>
                <div class='kpi-icon'>□</div>
                <div class='kpi-label'>Produtos críticos</div>
                <div class='kpi-value'>{produtos_criticos_inicio}</div>
                <div class='kpi-trend'>♧ Sem alterações críticas</div>
            </div>
            <div class='premium-kpi'>
                <div class='kpi-icon'>♟</div>
                <div class='kpi-label'>Frequência hoje</div>
                <div class='kpi-value'>{'OK' if frequencias_hoje else 'Pendente'}</div>
                <div class='kpi-trend'>♧ Atualização pendente</div>
            </div>
            <div class='premium-kpi'>
                <div class='kpi-icon'>▰</div>
                <div class='kpi-label'>Despesas frota</div>
                <div class='kpi-value'>{despesas_pendentes_inicio}</div>
                <div class='kpi-trend'>↘ -100% vs mês anterior</div>
            </div>
        </div>
        <div class='backup-line'>Backup: {escape_html(status_backup_inicio)} | Último backup: {escape_html(str(config.get('ultimo_backup', 'Nunca')))}</div>
        """,
        unsafe_allow_html=True
    )

    dias_resumo = [(datetime.now().date() - timedelta(days=i)) for i in range(6, -1, -1)]
    auditoria_df_inicio = pd.DataFrame(auditoria_inicio) if auditoria_inicio else pd.DataFrame()
    if not auditoria_df_inicio.empty and "data_hora" in auditoria_df_inicio.columns:
        auditoria_datas_inicio = pd.to_datetime(auditoria_df_inicio["data_hora"], dayfirst=True, errors="coerce").dt.date
    else:
        auditoria_datas_inicio = pd.Series([], dtype="object")
    datas_faltas_resumo = pd.to_datetime(df_faltas["data"], errors="coerce").dt.date if not df_faltas.empty else pd.Series([], dtype="object")
    datas_frota_resumo = []
    if not df_frotas_abastecimentos.empty and "data" in df_frotas_abastecimentos.columns:
        datas_frota_resumo.extend(pd.to_datetime(df_frotas_abastecimentos["data"], errors="coerce").dt.date.dropna().tolist())
    if not df_frotas_manutencoes.empty and "data" in df_frotas_manutencoes.columns:
        datas_frota_resumo.extend(pd.to_datetime(df_frotas_manutencoes["data"], errors="coerce").dt.date.dropna().tolist())

    linhas_resumo = []
    for dia in dias_resumo:
        chamados = int((auditoria_datas_inicio == dia).sum()) if len(auditoria_datas_inicio) else 0
        ordens = int((datas_faltas_resumo == dia).sum()) if len(datas_faltas_resumo) else 0
        concluidos = int(sum(1 for data_frota in datas_frota_resumo if data_frota == dia))
        linhas_resumo.extend([
            {"Dia": dia.strftime("%d/%m"), "Indicador": "Chamados", "Total": chamados},
            {"Dia": dia.strftime("%d/%m"), "Indicador": "Ordens de serviço", "Total": ordens},
            {"Dia": dia.strftime("%d/%m"), "Indicador": "Concluídos", "Total": concluidos},
        ])
    df_resumo_operacional = pd.DataFrame(linhas_resumo)

    st.markdown("<div class='dashboard-grid'><div class='dashboard-panel'><div class='section-title-row'><h2>Resumo Operacional</h2><span class='premium-select-pill'>Últimos 7 dias⌄</span></div>", unsafe_allow_html=True)
    if px:
        fig_resumo = px.line(
            df_resumo_operacional,
            x="Dia",
            y="Total",
            color="Indicador",
            markers=True,
            color_discrete_map={
                "Chamados": "#38BDF8",
                "Ordens de serviço": "#A78BFA",
                "Concluídos": "#F28C28",
            },
        )
        fig_resumo.update_layout(
            template="plotly_dark",
            height=300,
            margin=dict(l=18, r=18, t=22, b=18),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(5, 13, 31, .34)",
            font=dict(color="#E2E8F0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(148,163,184,.12)"),
            yaxis=dict(gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(148,163,184,.12)"),
        )
        fig_resumo.update_traces(line=dict(width=3), marker=dict(size=8))
        st.plotly_chart(fig_resumo, use_container_width=True, config={"displayModeBar": False})
    else:
        st.dataframe(df_resumo_operacional, use_container_width=True, hide_index=True)

    total_chamados_resumo = int(df_resumo_operacional[df_resumo_operacional["Indicador"] == "Chamados"]["Total"].sum())
    total_ordens_resumo = int(df_resumo_operacional[df_resumo_operacional["Indicador"] == "Ordens de serviço"]["Total"].sum())
    total_concluidos_resumo = int(df_resumo_operacional[df_resumo_operacional["Indicador"] == "Concluídos"]["Total"].sum())
    st.markdown(
        f"""
        <div class='summary-strip'>
            <div class='summary-mini'><strong>{total_chamados_resumo}</strong><span>Total chamados</span></div>
            <div class='summary-mini'><strong>{total_concluidos_resumo}</strong><span>Concluídos</span></div>
            <div class='summary-mini'><strong>{total_ordens_resumo}</strong><span>Em andamento</span></div>
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class='dashboard-panel'>
            <div class='section-title-row'>
                <h2>Últimas Ações</h2>
                <span class='premium-select-pill'>Ver todas</span>
            </div>
            <div class='actions-table-wrap'>
        """,
        unsafe_allow_html=True
    )
    if auditoria_inicio:
        colunas_acoes = ["data_hora", "usuario", "nivel", "acao", "modulo", "registro", "detalhe"]
        acoes_inicio = pd.DataFrame(auditoria_inicio[-8:])
        for coluna_acao in colunas_acoes:
            if coluna_acao not in acoes_inicio.columns:
                acoes_inicio[coluna_acao] = ""
        st.dataframe(formatar_colunas_tabela(acoes_inicio[colunas_acoes]), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma ação registrada ainda.")
    st.markdown("</div></div></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='alpes-footer'>
            <span>© 2026 <strong>ALPES Gestão e Instalações.</strong> Todos os direitos reservados.</span>
            <span>🛡 Ambiente seguro e monitorado</span>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# ABA ESTOQUE
# =========================
elif menu == "ESTOQUE":
    st.title("ESTOQUE")

    total_cadastrados = len(df_produtos)
    total_ok = len(df_produtos[df_produtos["situacao"] == "🟢 OK"])
    total_baixo = len(df_produtos[df_produtos["situacao"] == "🔴 ESTOQUE BAIXO"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total de Produtos Cadastrados</div><div class='metric-value'>{total_cadastrados}</div><div class='metric-label'>Todos os itens cadastrados</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Estoque OK</div><div class='metric-value' style='color:#22c55e'>{total_ok}</div><div class='metric-label'>Acima do estoque mínimo</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Estoque Baixo</div><div class='metric-value' style='color:#ef4444'>{total_baixo}</div><div class='metric-label'>Produtos abaixo do mínimo</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    busca = st.text_input("Busca", placeholder="BUSCAR POR CÓDIGO, PRODUTO OU CATEGORIA", label_visibility="collapsed")

    with st.expander("Filtros Avançados"):
        f_col1, f_col2, f_col3 = st.columns(3)

        if "limpar_filtros" in st.session_state and st.session_state["limpar_filtros"]:
            st.session_state["f_cat"] = "Todas"
            st.session_state["f_sit"] = "Todas"
            st.session_state["f_data"] = "Todas"
            st.session_state["limpar_filtros"] = False

        categorias_cadastradas = [item.get("nome", "") for item in categorias_config if item.get("nome", "")]
        categorias_em_produtos = list(df_produtos["categoria"].dropna().unique())
        categorias_lista = ["Todas"] + list(dict.fromkeys(categorias_cadastradas + categorias_em_produtos))
        f_cat = f_col1.selectbox("Categoria", categorias_lista, key="f_cat")
        f_sit = f_col2.selectbox("Situação", ["Todas", "Estoque OK", "Estoque Baixo"], key="f_sit")
        f_data = f_col3.selectbox("Data de Movimentação", ["Todas", "Últimos 7 dias", "Últimos 30 dias", "Personalizado"], key="f_data")

        f_data_ini, f_data_fim = None, None
        if f_data == "Personalizado":
            c_d1, c_d2 = st.columns(2)
            f_data_ini = c_d1.date_input("Data Início")
            f_data_fim = c_d2.date_input("Data Fim")

        c_ap, c_lim, _ = st.columns([2, 2, 6])
        if c_ap.button("Aplicar filtro"):
            st.session_state["aplicar_filtros"] = True
        if c_lim.button("Limpar tudo"):
            st.session_state["limpar_filtros"] = True
            st.session_state["aplicar_filtros"] = False
            st.rerun()

    df_filtrado = df_produtos.copy()

    if busca:
        termo = str(busca).lower()
        df_filtrado = df_filtrado[
            df_filtrado["codigo"].astype(str).str.lower().str.contains(termo) |
            df_filtrado["produto"].astype(str).str.lower().str.contains(termo) |
            df_filtrado["categoria"].astype(str).str.lower().str.contains(termo)
        ]

    if f_cat != "Todas":
        df_filtrado = df_filtrado[df_filtrado["categoria"] == f_cat]

    if f_sit == "Estoque OK":
        df_filtrado = df_filtrado[df_filtrado["situacao"] == "🟢 OK"]
    elif f_sit == "Estoque Baixo":
        df_filtrado = df_filtrado[df_filtrado["situacao"] == "🔴 ESTOQUE BAIXO"]

    if f_data != "Todas" and not df_mov.empty:
        df_mov_temp = df_mov.copy()
        df_mov_temp["data"] = pd.to_datetime(df_mov_temp["data"], errors="coerce")
        hoje = datetime.now()
        prods_com_mov = []

        if f_data == "Últimos 7 dias":
            limite = hoje - timedelta(days=7)
            prods_com_mov = df_mov_temp[df_mov_temp["data"] >= limite]["produto"].unique()
        elif f_data == "Últimos 30 dias":
            limite = hoje - timedelta(days=30)
            prods_com_mov = df_mov_temp[df_mov_temp["data"] >= limite]["produto"].unique()
        elif f_data == "Personalizado" and f_data_ini and f_data_fim:
            ini = pd.to_datetime(f_data_ini)
            fim = pd.to_datetime(f_data_fim) + timedelta(days=1)
            prods_com_mov = df_mov_temp[(df_mov_temp["data"] >= ini) & (df_mov_temp["data"] < fim)]["produto"].unique()

        df_filtrado = df_filtrado[df_filtrado["produto"].isin(prods_com_mov)]

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class='stock-table-header'>
            <div>Código</div>
            <div>Produto</div>
            <div>Categoria</div>
            <div>Atual</div>
            <div>Mínimo</div>
            <div>Localização</div>
            <div>Situação</div>
            <div>Imagem</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for i, row in df_filtrado.iterrows():
        col = st.columns([1, 2, 2, 1, 1, 2, 2, 3])

        col[0].write(row["codigo"])

        if col[1].button(row["produto"], key=f"prod_{i}"):
            st.session_state["produto"] = row["produto"]

        col[2].markdown(badge_categoria(row["categoria"]), unsafe_allow_html=True)
        col[3].write(int(row["estoque_atual"]))
        col[4].markdown(f"<span style='color:#facc15'><b>{row['estoque_minimo']}</b></span>", unsafe_allow_html=True)
        col[5].write(row["localizacao"])
        col[6].markdown(badge_estoque(row["estoque_atual"], row["estoque_minimo"]), unsafe_allow_html=True)

        img = origem_imagem_produto(row["imagem"])
        if img:
            col[7].image(img, use_container_width=True)

    if "produto" in st.session_state:
        produto = st.session_state["produto"]
        st.divider()
        st.subheader(f"📊 Histórico - {produto}")

        hist = df_mov[df_mov["produto"] == produto].copy()
        if not hist.empty:
            hist["data"] = pd.to_datetime(hist["data"]).dt.strftime("%d/%m/%Y %H:%M")
            st.dataframe(hist, use_container_width=True)
        else:
            st.info("Sem movimentações")

        if st.button("Fechar Histórico"):
            del st.session_state["produto"]
            st.rerun()


# =========================
# COMPRAS
# =========================
elif menu == "COMPRAS":
    st.title("COMPRAS")

    df = df_produtos.copy()
    df["necessita"] = (df["estoque_minimo"] + 5) - df["estoque_atual"]
    df = df[df["necessita"] > 0]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Gerar PDF"):
            pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            caminho_pdf = os.path.join(pasta_downloads, "compras_relatorio.pdf")

            data_pdf = [["Código", "Produto", "Atual", "Mínimo", "Necessita", "Imagem"]]

            for _, r in df.iterrows():
                img_path = origem_imagem_produto(r["imagem"])
                img_rl = ""
                if img_path and os.path.exists(img_path):
                    try:
                        img_rl = RLImage(img_path, width=1 * inch, height=1 * inch)
                    except Exception:
                        pass

                data_pdf.append([
                    r["codigo"],
                    r["produto"],
                    str(int(r["estoque_atual"])),
                    str(int(r["estoque_minimo"])),
                    str(int(r["necessita"])),
                    img_rl
                ])

            pdf = SimpleDocTemplate(caminho_pdf, pagesize=letter)
            tabela = Table(data_pdf, colWidths=[60, 150, 50, 60, 60, 100])

            estilo = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                ("TEXTCOLOR", (3, 1), (3, -1), colors.orange),
                ("TEXTCOLOR", (4, 1), (4, -1), colors.red),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ])
            tabela.setStyle(estilo)

            elementos = [tabela]
            pdf.build(elementos)

            st.success(f"PDF profissional salvo com sucesso em: {caminho_pdf}")

    with col2:
        if st.button("📂 Selecionar Categoria"):
            st.session_state["mostrar_categoria"] = True

    if "mostrar_categoria" not in st.session_state:
        st.session_state["mostrar_categoria"] = False

    if "categoria_sel" not in st.session_state:
        st.session_state["categoria_sel"] = "GERAL"

    if st.session_state["mostrar_categoria"]:
        categorias = ["GERAL"] + list(df_produtos["categoria"].dropna().unique())
        cols = st.columns(max(len(categorias), 1))

        for i, cat in enumerate(categorias):
            if cols[i].button(cat):
                st.session_state["categoria_sel"] = cat

    if st.session_state["categoria_sel"] != "GERAL":
        df = df[df["categoria"] == st.session_state["categoria_sel"]]

    st.markdown("<br><br>", unsafe_allow_html=True)

    headers = st.columns([1, 2, 1, 1, 1, 3])
    headers[0].write("Código")
    headers[1].write("Produto")
    headers[2].write("Estoque Atual")
    headers[3].write("Estoque Mínimo")
    headers[4].write("Necessita")
    headers[5].write("Imagem")

    for i, row in df.iterrows():
        col = st.columns([1, 2, 1, 1, 1, 3])

        col[0].write(row["codigo"])
        col[1].write(row["produto"])
        col[2].write(int(row["estoque_atual"]))
        col[3].markdown(f"<span style='color:#facc15'><b>{row['estoque_minimo']}</b></span>", unsafe_allow_html=True)
        col[4].markdown(f"<span style='color:#ef4444'><b>{int(row['necessita'])}</b></span>", unsafe_allow_html=True)

        img = origem_imagem_produto(row["imagem"])
        if img:
            col[5].image(img, use_container_width=True)


# =========================
# MOVIMENTACAO
# =========================
elif menu == "MOVIMENTAÇÃO":
    st.title("MOVIMENTAÇÃO")

    if "lista_mov" not in st.session_state:
        st.session_state["lista_mov"] = []

    if "tipo_movimentacao" not in st.session_state:
        st.session_state["tipo_movimentacao"] = "Entrada"
    if "etiquetas_entrada" not in st.session_state:
        st.session_state["etiquetas_entrada"] = []

    st.write("Tipo de Movimentação")
    tipo_col1, tipo_col2, _ = st.columns([1, 1, 6])
    if tipo_col1.button(
        "ENTRADA",
        use_container_width=True,
        type="primary" if st.session_state["tipo_movimentacao"] == "Entrada" else "secondary"
    ):
        st.session_state["tipo_movimentacao"] = "Entrada"
    if tipo_col2.button(
        "SAIDA",
        use_container_width=True,
        type="primary" if st.session_state["tipo_movimentacao"] == "Saída" else "secondary"
    ):
        st.session_state["tipo_movimentacao"] = "Saída"
    tipo = st.session_state["tipo_movimentacao"]
    tipo_e_saida = str(tipo).lower().startswith("sa")
    st.caption(f"Selecionado: {tipo}")
    produtos_opcoes = df_produtos["produto"].dropna().tolist() if not df_produtos.empty else ["Nenhum produto cadastrado"]
    produto_index = 0
    if tipo_e_saida:
        codigo_bipado = st.text_input("Bipar Produto", key="mov_codigo_bipado").strip()
        if codigo_bipado and not df_produtos.empty:
            produto_encontrado = df_produtos[df_produtos["codigo"].astype(str).str.upper() == codigo_bipado.upper()]
            if not produto_encontrado.empty:
                produto_bipado = str(produto_encontrado.iloc[0]["produto"])
                if produto_bipado in produtos_opcoes:
                    produto_index = produtos_opcoes.index(produto_bipado)
                st.success(f"Produto bipado: {produto_bipado}")
            else:
                st.error("Produto não encontrado para o código bipado.")
    produto = st.selectbox("Produto", produtos_opcoes, index=produto_index)
    cliente_destino = ""
    observacao_saida = ""
    if tipo_e_saida:
        clientes_ativos = df_clientes[df_clientes["status"] != "Inativo"]["nome_cliente"].dropna().tolist()
        if clientes_ativos:
            cliente_destino = st.selectbox("Cliente de destino", clientes_ativos)
        else:
            st.warning("Cadastre ou ative um cliente antes de registrar uma saída.")
        observacao_saida = st.text_area("Observação", key="mov_saida_observacao").strip()
    qtd = st.number_input("Quantidade", 1)

    col1, col2 = st.columns(2)

    if col1.button("➕ Adicionar"):
        if produto != "Nenhum produto cadastrado":
            if tipo_e_saida and not cliente_destino:
                st.error("Selecione um cliente para registrar a saída.")
            else:
                st.session_state["lista_mov"].append({
                    "produto": produto,
                    "tipo": tipo,
                    "quantidade": qtd,
                    "cliente": cliente_destino,
                    "observacao": observacao_saida,
                    "codigo": str(df_produtos.loc[df_produtos["produto"] == produto, "codigo"].iloc[0]) if not df_produtos[df_produtos["produto"] == produto].empty else ""
                })

    if col2.button("💾 Salvar"):
        if not st.session_state["lista_mov"]:
            st.warning("Adicione pelo menos uma movimentação antes de salvar.")
        else:
            for item in st.session_state["lista_mov"]:
                tipo_salvo = "Saída" if str(item["tipo"]).lower().startswith("sa") else "Entrada"
                nova = pd.DataFrame([{
                    "produto": item["produto"],
                    "tipo": tipo_salvo,
                    "quantidade": item["quantidade"],
                    "data": datetime.now(),
                    "cliente": item.get("cliente", ""),
                    "observacao": item.get("observacao", "")
                }])
                df_mov = pd.concat([df_mov, nova], ignore_index=True)
                if tipo_salvo == "Entrada":
                    st.session_state["etiquetas_entrada"].append({
                        "produto": item["produto"],
                        "codigo": item.get("codigo", ""),
                        "quantidade": item["quantidade"],
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })

            df_mov["tipo"] = df_mov["tipo"].astype(str).replace({
                "Saida": "Saída",
                "SaÃ­da": "Saída",
                "saida": "Saída",
                "saída": "Saída",
                "entrada": "Entrada"
            })
            df_mov.to_excel(MOVIMENTACOES_XLSX, index=False)
            st.session_state["lista_mov"] = []
            if supabase_configurado() and st.session_state.get("ultimo_erro_supabase"):
                st.error(f"Movimentações salvas localmente, mas houve erro ao salvar no Supabase: {st.session_state.get('ultimo_erro_supabase')}")
            else:
                st.success("Movimentações salvas. Estoque e histórico atualizados.")
            st.rerun()

    st.divider()
    if st.session_state.get("etiquetas_entrada"):
        st.download_button(
            "Gerar Etiquetas Das Entradas",
            data=gerar_pdf_etiquetas(st.session_state["etiquetas_entrada"]),
            file_name="etiquetas_entrada.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        if st.button("Limpar Etiquetas Geradas"):
            st.session_state["etiquetas_entrada"] = []
            st.rerun()

    for item in st.session_state["lista_mov"]:
        destino = f" | Cliente: {item.get('cliente', '')}" if item.get("cliente") else ""
        observacao = f" | Observação: {item.get('observacao', '')}" if item.get("observacao") else ""
        st.write(f"{item['produto']} | {item['tipo']} | {item['quantidade']}{destino}{observacao}")


# =========================
# CADASTRO
# =========================
elif menu == "PRODUTOS":
    st.title("PRODUTOS")

    categorias = [item.get("nome", "") for item in categorias_config if item.get("status", "Ativo") != "Inativo"] or ["MANUTENÇÃO", "ELÉTRICA", "HIDRÁULICA", "LIMPEZA", "COPA", "JARDINAGEM"]
    unidades = [item.get("nome", "") for item in unidades_config if item.get("nome", "") and item.get("status", "Ativo") != "Inativo"] or ["UN"]
    fornecedores = df_fornecedores[df_fornecedores["status"] != "Inativo"]["nome_fornecedor"].dropna().tolist()
    fornecedores_opcoes = ["Não informado"] + fornecedores

    if "acao" not in st.session_state:
        st.session_state["acao"] = "Adicionar"
    if st.session_state["acao"] == "Excluir":
        st.session_state["acao"] = "Inativar"

    col1, col2, col3 = st.columns(3)

    if col1.button("➕ Adicionar", type="primary" if st.session_state["acao"] == "Adicionar" else "secondary"):
        st.session_state["acao"] = "Adicionar"

    if col2.button("✏️ Editar", type="primary" if st.session_state["acao"] == "Editar" else "secondary"):
        st.session_state["acao"] = "Editar"

    if col3.button("Inativar", type="primary" if st.session_state["acao"] == "Inativar" else "secondary"):
        st.session_state["acao"] = "Inativar"

    acao = st.session_state["acao"]

    if acao == "Adicionar":
        codigo = proximo_codigo_produto()
        st.text_input("Código", value=codigo, disabled=True)
        produto = st.text_input("Produto")
        categoria = st.selectbox("Categoria", categorias)
        estoque_min = st.number_input("Estoque mínimo", 0, value=int(config.get("estoque_minimo_padrao", 1)))
        unidade = st.selectbox("Unidade", unidades)
        valor_unitario = st.number_input("Valor unitário", min_value=0.0, step=0.01, format="%.2f")
        fornecedor = st.selectbox("FORNECEDOR", fornecedores_opcoes, key="produto_fornecedor_add")
        local = st.text_input("Localização")
        imagem_upload = st.file_uploader("Anexar Imagem Do Produto", type=["png", "jpg", "jpeg", "webp"], key="produto_imagem_add")
        imagem_manual = st.text_input("Imagem Atual / Nome Do Arquivo", help="Opcional. Use somente se a imagem já estiver na pasta Imagens Produtos.")

        if st.button("Salvar"):
            if bloquear_se_consulta(usuario_logado):
                st.stop()
            elif not texto_obrigatorio(produto):
                st.error("Informe o nome do produto.")
                st.stop()
            elif valor_duplicado(df_produtos[df_produtos["status"].astype(str) != "Inativo"], "produto", produto):
                st.error("Já existe um produto ativo com esse nome.")
                st.stop()
            imagem = salvar_imagem_produto(imagem_upload, codigo, produto) if imagem_upload else imagem_manual.strip()
            novo = pd.DataFrame([{
                "codigo": codigo,
                "produto": produto,
                "categoria": categoria,
                "estoque_minimo": estoque_min,
                "unidade": unidade,
                "valor_unitario": valor_unitario,
                "fornecedor": "" if fornecedor == "Não informado" else fornecedor,
                "localizacao": local,
                "imagem": imagem,
                "status": "Ativo"
            }])

            df_produtos = pd.concat([df_produtos, novo], ignore_index=True)
            df_produtos.to_excel(PRODUTOS_XLSX, index=False)
            registrar_auditoria("CRIAR", "PRODUTOS", "Produto cadastrado", produto)
            if supabase_configurado() and st.session_state.get("ultimo_erro_supabase"):
                st.error(f"Produto salvo localmente, mas houve erro ao salvar no Supabase: {st.session_state.get('ultimo_erro_supabase')}")
            else:
                st.success("Produto salvo com sucesso.")
            st.rerun()

    elif acao == "Editar":
        if df_produtos.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            prod = st.selectbox("Produto", df_produtos["produto"])
            dados = df_produtos[df_produtos["produto"] == prod].iloc[0]

            codigo = st.text_input("Código", dados["codigo"])
            categoria = st.selectbox("Categoria", categorias, index=categorias.index(dados["categoria"]) if dados["categoria"] in categorias else 0)
            estoque_min = st.number_input("Estoque mínimo", 0, value=int(dados["estoque_minimo"]))
            unidade_atual = dados["unidade"] if dados["unidade"] in unidades else unidades[0]
            unidade = st.selectbox("Unidade", unidades, index=unidades.index(unidade_atual))
            valor_unitario = st.number_input("Valor unitário", min_value=0.0, step=0.01, format="%.2f", value=float(dados["valor_unitario"]) if pd.notna(dados["valor_unitario"]) else 0.0)
            fornecedor_atual = dados["fornecedor"] if dados["fornecedor"] in fornecedores_opcoes else "Não informado"
            fornecedor = st.selectbox("FORNECEDOR", fornecedores_opcoes, index=fornecedores_opcoes.index(fornecedor_atual), key="produto_fornecedor_edit")
            local = st.text_input("Localização", dados["localizacao"])
            imagem_atual = str(dados["imagem"])
            if imagem_atual:
                caminho_imagem_atual = origem_imagem_produto(imagem_atual)
                if caminho_imagem_atual:
                    st.image(caminho_imagem_atual, caption="Imagem atual", width=180)
            imagem_upload = st.file_uploader("Trocar Imagem Do Produto", type=["png", "jpg", "jpeg", "webp"], key="produto_imagem_edit")
            imagem_manual = st.text_input("Imagem Atual / Nome Do Arquivo", imagem_atual)

            if st.button("Salvar Alteração"):
                if bloquear_se_consulta(usuario_logado):
                    st.stop()
                elif not texto_obrigatorio(codigo):
                    st.error("Informe o codigo do produto.")
                    st.stop()
                antes_produto = dados.to_dict()
                imagem = salvar_imagem_produto(imagem_upload, codigo, prod) if imagem_upload else imagem_manual.strip()
                df_produtos.loc[df_produtos["produto"] == prod, "codigo"] = codigo
                df_produtos.loc[df_produtos["produto"] == prod, "categoria"] = categoria
                df_produtos.loc[df_produtos["produto"] == prod, "estoque_minimo"] = estoque_min
                df_produtos.loc[df_produtos["produto"] == prod, "unidade"] = unidade
                df_produtos.loc[df_produtos["produto"] == prod, "valor_unitario"] = valor_unitario
                df_produtos.loc[df_produtos["produto"] == prod, "fornecedor"] = "" if fornecedor == "Não informado" else fornecedor
                df_produtos.loc[df_produtos["produto"] == prod, "localizacao"] = local
                df_produtos.loc[df_produtos["produto"] == prod, "imagem"] = imagem

                df_produtos.to_excel(PRODUTOS_XLSX, index=False)
                depois_produto = df_produtos[df_produtos["produto"] == prod].iloc[0].to_dict()
                registrar_auditoria("EDITAR", "PRODUTOS", "Produto alterado", prod, antes_produto, depois_produto)
                if supabase_configurado() and st.session_state.get("ultimo_erro_supabase"):
                    st.error(f"Produto atualizado localmente, mas houve erro ao salvar no Supabase: {st.session_state.get('ultimo_erro_supabase')}")
                else:
                    st.success("Produto atualizado com sucesso.")

    elif acao == "Inativar":
        if df_produtos.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            produtos_ativos = df_produtos[df_produtos["status"].astype(str) != "Inativo"]
            if produtos_ativos.empty:
                st.info("Nenhum produto ativo para inativar.")
            else:
                prod = st.selectbox("Produto", produtos_ativos["produto"])

                if st.button("Inativar"):
                    if bloquear_se_consulta(usuario_logado):
                        st.stop()
                    antes_produto = df_produtos[df_produtos["produto"] == prod].iloc[0].to_dict()
                    df_produtos.loc[df_produtos["produto"] == prod, "status"] = "Inativo"
                    df_produtos.to_excel(PRODUTOS_XLSX, index=False)
                    registrar_auditoria("INATIVAR", "PRODUTOS", "Produto inativado", prod, antes_produto, {"status": "Inativo"})
                    st.success("Produto inativado.")
                    st.rerun()


# =========================
# CLIENTES
# =========================
elif menu == "CLIENTES":
    st.title("CLIENTES")

    if "acao_cliente" not in st.session_state:
        st.session_state["acao_cliente"] = "Adicionar"
    if st.session_state["acao_cliente"] == "Excluir":
        st.session_state["acao_cliente"] = "Inativar"
    if "cliente_selecionado_codigo" not in st.session_state:
        st.session_state["cliente_selecionado_codigo"] = ""

    col1, col2, col3 = st.columns(3)

    if col1.button("➕ Adicionar", key="cliente_adicionar", type="primary" if st.session_state["acao_cliente"] == "Adicionar" else "secondary"):
        st.session_state["acao_cliente"] = "Adicionar"

    if col2.button("✏️ Editar", key="cliente_editar", type="primary" if st.session_state["acao_cliente"] == "Editar" else "secondary"):
        st.session_state["acao_cliente"] = "Editar"

    if col3.button("⛔ Inativar", key="cliente_inativar", type="primary" if st.session_state["acao_cliente"] == "Inativar" else "secondary"):
        st.session_state["acao_cliente"] = "Inativar"

    acao_cliente = st.session_state["acao_cliente"]

    if acao_cliente == "Adicionar":
        codigo = proximo_codigo_cliente()
        st.text_input("CÓDIGO", value=codigo, disabled=True)
        nome_cliente = st.text_input("NOME DO CLIENTE")
        telefone = st.text_input("TELEFONE")
        cidade = st.text_input("CIDADE")
        estado = st.text_input("ESTADO")
        tipo_contrato = st.radio("TEMPO DE CONTRATO", ["Período definido", "Prazo indeterminado"], horizontal=True)

        data_inicial, data_final = "", ""
        if tipo_contrato == "Período definido":
            c_data1, c_data2 = st.columns(2)
            data_inicial = c_data1.date_input("DATA INICIAL")
            data_final = c_data2.date_input("DATA FINAL")

        if st.button("Salvar cliente"):
            if bloquear_se_consulta(usuario_logado):
                st.stop()
            elif not texto_obrigatorio(nome_cliente):
                st.error("Informe o nome do cliente.")
                st.stop()
            elif valor_duplicado(df_clientes[df_clientes["status"].astype(str) != "Inativo"], "nome_cliente", nome_cliente):
                st.error("Já existe um cliente ativo com esse nome.")
                st.stop()
            novo = pd.DataFrame([{
                "codigo": codigo,
                "nome_cliente": nome_cliente,
                "telefone": telefone,
                "cidade": cidade,
                "estado": estado,
                "tipo_contrato": tipo_contrato,
                "data_inicial": data_inicial,
                "data_final": data_final,
                "status": "Ativo"
            }])

            df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
            df_clientes.to_excel(CLIENTES_XLSX, index=False)
            registrar_auditoria("CRIAR", "CLIENTES", "Cliente cadastrado", nome_cliente)
            st.success("Cliente adicionado")

    elif acao_cliente == "Editar":
        if df_clientes.empty:
            st.info("Nenhum cliente cadastrado.")
        else:
            codigos_clientes = df_clientes["codigo"].astype(str).tolist()
            nomes_por_codigo = dict(zip(codigos_clientes, df_clientes["nome_cliente"].astype(str)))
            codigo_preselecionado = str(st.session_state.get("cliente_selecionado_codigo", ""))
            indice_preselecionado = codigos_clientes.index(codigo_preselecionado) if codigo_preselecionado in codigos_clientes else 0
            cliente_codigo = st.selectbox(
                "Cliente",
                codigos_clientes,
                index=indice_preselecionado,
                format_func=lambda cod: f"{cod} - {nomes_por_codigo.get(cod, '')}",
                key="cliente_editar_codigo"
            )
            dados = df_clientes[df_clientes["codigo"].astype(str) == str(cliente_codigo)].iloc[0]

            codigo = st.text_input("CÓDIGO", dados["codigo"], disabled=True)
            nome_cliente = st.text_input("NOME DO CLIENTE", dados["nome_cliente"])
            telefone = st.text_input("TELEFONE", dados["telefone"])
            cidade = st.text_input("CIDADE", dados["cidade"])
            estado = st.text_input("ESTADO", dados["estado"])
            status = st.selectbox("STATUS", ["Ativo", "Inativo"], index=0 if dados["status"] == "Ativo" else 1)
            tipo_padrao = dados["tipo_contrato"] if dados["tipo_contrato"] in ["Período definido", "Prazo indeterminado"] else "Período definido"
            tipo_contrato = st.radio("TEMPO DE CONTRATO", ["Período definido", "Prazo indeterminado"], index=0 if tipo_padrao == "Período definido" else 1, horizontal=True)

            data_inicial, data_final = "", ""
            if tipo_contrato == "Período definido":
                c_data1, c_data2 = st.columns(2)
                data_inicial_padrao = pd.to_datetime(dados["data_inicial"], errors="coerce")
                data_final_padrao = pd.to_datetime(dados["data_final"], errors="coerce")
                data_inicial = c_data1.date_input("DATA INICIAL", value=data_inicial_padrao.date() if pd.notna(data_inicial_padrao) else datetime.now().date())
                data_final = c_data2.date_input("DATA FINAL", value=data_final_padrao.date() if pd.notna(data_final_padrao) else datetime.now().date())

            if st.button("Salvar alteração do cliente"):
                if bloquear_se_consulta(usuario_logado):
                    st.stop()
                elif not texto_obrigatorio(nome_cliente):
                    st.error("Informe o nome do cliente.")
                    st.stop()
                linha_cliente = df_clientes["codigo"].astype(str) == str(cliente_codigo)
                antes_cliente = df_clientes[linha_cliente].iloc[0].to_dict()
                df_clientes.loc[linha_cliente, "codigo"] = str(codigo)
                df_clientes.loc[linha_cliente, "nome_cliente"] = str(nome_cliente)
                df_clientes.loc[linha_cliente, "telefone"] = str(telefone)
                df_clientes.loc[linha_cliente, "cidade"] = str(cidade)
                df_clientes.loc[linha_cliente, "estado"] = str(estado)
                df_clientes.loc[linha_cliente, "tipo_contrato"] = str(tipo_contrato)
                df_clientes.loc[linha_cliente, "data_inicial"] = str(data_inicial)
                df_clientes.loc[linha_cliente, "data_final"] = str(data_final)
                df_clientes.loc[linha_cliente, "status"] = str(status)
                df_clientes.to_excel(CLIENTES_XLSX, index=False)
                depois_cliente = df_clientes[linha_cliente].iloc[0].to_dict()
                registrar_auditoria("EDITAR", "CLIENTES", "Cliente alterado", str(cliente_codigo), antes_cliente, depois_cliente)
                st.success("Cliente atualizado")

    elif acao_cliente == "Inativar":
        clientes_ativos = df_clientes[df_clientes["status"] != "Inativo"].copy()
        if clientes_ativos.empty:
            st.info("Nenhum cliente ativo para inativar.")
        else:
            codigos_ativos = clientes_ativos["codigo"].astype(str).tolist()
            nomes_ativos_por_codigo = dict(zip(codigos_ativos, clientes_ativos["nome_cliente"].astype(str)))
            codigo_preselecionado = str(st.session_state.get("cliente_selecionado_codigo", ""))
            indice_preselecionado = codigos_ativos.index(codigo_preselecionado) if codigo_preselecionado in codigos_ativos else 0
            cliente_codigo = st.selectbox(
                "Cliente",
                codigos_ativos,
                index=indice_preselecionado,
                format_func=lambda cod: f"{cod} - {nomes_ativos_por_codigo.get(cod, '')}",
                key="cliente_inativar_codigo"
            )

            if st.button("Inativar cliente"):
                if bloquear_se_consulta(usuario_logado):
                    st.stop()
                linha_cliente = df_clientes["codigo"].astype(str) == str(cliente_codigo)
                antes_cliente = df_clientes[linha_cliente].iloc[0].to_dict()
                df_clientes.loc[df_clientes["codigo"].astype(str) == str(cliente_codigo), "status"] = "Inativo"
                df_clientes.to_excel(CLIENTES_XLSX, index=False)
                registrar_auditoria("INATIVAR", "CLIENTES", "Cliente inativado", str(cliente_codigo), antes_cliente, {"status": "Inativo"})
                st.success("Cliente inativado")

    st.divider()
    st.subheader("Clientes cadastrados")
    st.dataframe(df_clientes, use_container_width=True)

    if not df_clientes.empty:
        st.caption("Selecione um cliente cadastrado para editar ou inativar.")
        codigos_lista = df_clientes["codigo"].astype(str).tolist()
        nomes_lista_por_codigo = dict(zip(codigos_lista, df_clientes["nome_cliente"].astype(str)))
        codigo_preselecionado = str(st.session_state.get("cliente_selecionado_codigo", ""))
        indice_preselecionado = codigos_lista.index(codigo_preselecionado) if codigo_preselecionado in codigos_lista else 0
        cliente_lista_codigo = st.selectbox(
            "Cliente selecionado",
            codigos_lista,
            index=indice_preselecionado,
            format_func=lambda cod: f"{cod} - {nomes_lista_por_codigo.get(cod, '')}",
            key="cliente_lista_codigo"
        )
        col_editar_cliente, col_inativar_cliente = st.columns(2)
        if col_editar_cliente.button("Editar cliente", key="cliente_lista_editar", use_container_width=True):
            st.session_state["cliente_selecionado_codigo"] = str(cliente_lista_codigo)
            st.session_state["acao_cliente"] = "Editar"
            st.rerun()
        if col_inativar_cliente.button("Inativar cliente", key="cliente_lista_inativar", use_container_width=True):
            st.session_state["cliente_selecionado_codigo"] = str(cliente_lista_codigo)
            st.session_state["acao_cliente"] = "Inativar"
            st.rerun()


# =========================
# FORNECEDOR
# =========================
elif menu == "FORNECEDOR":
    st.title("FORNECEDOR")

    if "acao_fornecedor" not in st.session_state:
        st.session_state["acao_fornecedor"] = "Adicionar"
    if st.session_state["acao_fornecedor"] == "Excluir":
        st.session_state["acao_fornecedor"] = "Inativar"

    col1, col2, col3 = st.columns(3)

    if col1.button("➕ Adicionar", key="fornecedor_adicionar", type="primary" if st.session_state["acao_fornecedor"] == "Adicionar" else "secondary"):
        st.session_state["acao_fornecedor"] = "Adicionar"

    if col2.button("✏️ Editar", key="fornecedor_editar", type="primary" if st.session_state["acao_fornecedor"] == "Editar" else "secondary"):
        st.session_state["acao_fornecedor"] = "Editar"

    if col3.button("⛔ Inativar", key="fornecedor_inativar", type="primary" if st.session_state["acao_fornecedor"] == "Inativar" else "secondary"):
        st.session_state["acao_fornecedor"] = "Inativar"

    acao_fornecedor = st.session_state["acao_fornecedor"]

    if acao_fornecedor == "Adicionar":
        codigo = proximo_codigo_fornecedor()
        st.text_input("CÓDIGO", value=codigo, disabled=True)
        nome_fornecedor = st.text_input("NOME DO FORNECEDOR")
        telefone = st.text_input("TELEFONE")
        cidade = st.text_input("CIDADE")
        estado = st.text_input("ESTADO")

        if st.button("Salvar fornecedor"):
            if bloquear_se_consulta(usuario_logado):
                st.stop()
            elif not texto_obrigatorio(nome_fornecedor):
                st.error("Informe o nome do fornecedor.")
                st.stop()
            elif valor_duplicado(df_fornecedores[df_fornecedores["status"].astype(str) != "Inativo"], "nome_fornecedor", nome_fornecedor):
                st.error("Já existe um fornecedor ativo com esse nome.")
                st.stop()
            novo = pd.DataFrame([{
                "codigo": codigo,
                "nome_fornecedor": nome_fornecedor,
                "telefone": telefone,
                "cidade": cidade,
                "estado": estado,
                "tipo_contrato": "",
                "data_inicial": "",
                "data_final": "",
                "status": "Ativo"
            }])

            df_fornecedores = pd.concat([df_fornecedores, novo], ignore_index=True)
            df_fornecedores.to_excel(FORNECEDORES_XLSX, index=False)
            registrar_auditoria("CRIAR", "FORNECEDORES", "Fornecedor cadastrado", nome_fornecedor)
            st.success("Fornecedor adicionado")

    elif acao_fornecedor == "Editar":
        if df_fornecedores.empty:
            st.info("Nenhum fornecedor cadastrado.")
        else:
            fornecedor_sel = st.selectbox("Fornecedor", df_fornecedores["nome_fornecedor"])
            dados = df_fornecedores[df_fornecedores["nome_fornecedor"] == fornecedor_sel].iloc[0]

            codigo = st.text_input("CÓDIGO", dados["codigo"], disabled=True)
            nome_fornecedor = st.text_input("NOME DO FORNECEDOR", dados["nome_fornecedor"])
            telefone = st.text_input("TELEFONE", dados["telefone"])
            cidade = st.text_input("CIDADE", dados["cidade"])
            estado = st.text_input("ESTADO", dados["estado"])
            status = st.selectbox("STATUS", ["Ativo", "Inativo"], index=0 if dados["status"] == "Ativo" else 1)

            if st.button("Salvar alteração do fornecedor"):
                if bloquear_se_consulta(usuario_logado):
                    st.stop()
                elif not texto_obrigatorio(nome_fornecedor):
                    st.error("Informe o nome do fornecedor.")
                    st.stop()
                linha_fornecedor = df_fornecedores["nome_fornecedor"] == fornecedor_sel
                antes_fornecedor = df_fornecedores[linha_fornecedor].iloc[0].to_dict()
                df_fornecedores.loc[linha_fornecedor, "codigo"] = str(codigo)
                df_fornecedores.loc[linha_fornecedor, "nome_fornecedor"] = str(nome_fornecedor)
                df_fornecedores.loc[linha_fornecedor, "telefone"] = str(telefone)
                df_fornecedores.loc[linha_fornecedor, "cidade"] = str(cidade)
                df_fornecedores.loc[linha_fornecedor, "estado"] = str(estado)
                df_fornecedores.loc[linha_fornecedor, "status"] = str(status)
                df_fornecedores.to_excel(FORNECEDORES_XLSX, index=False)
                depois_fornecedor = df_fornecedores[df_fornecedores["nome_fornecedor"] == str(nome_fornecedor)].iloc[0].to_dict()
                registrar_auditoria("EDITAR", "FORNECEDORES", "Fornecedor alterado", fornecedor_sel, antes_fornecedor, depois_fornecedor)
                st.success("Fornecedor atualizado")

    elif acao_fornecedor == "Inativar":
        fornecedores_ativos = df_fornecedores[df_fornecedores["status"] != "Inativo"].copy()
        if fornecedores_ativos.empty:
            st.info("Nenhum fornecedor ativo para inativar.")
        else:
            fornecedor_sel = st.selectbox("Fornecedor", fornecedores_ativos["nome_fornecedor"])

            if st.button("Inativar fornecedor"):
                if bloquear_se_consulta(usuario_logado):
                    st.stop()
                antes_fornecedor = df_fornecedores[df_fornecedores["nome_fornecedor"] == fornecedor_sel].iloc[0].to_dict()
                df_fornecedores.loc[df_fornecedores["nome_fornecedor"] == fornecedor_sel, "status"] = "Inativo"
                df_fornecedores.to_excel(FORNECEDORES_XLSX, index=False)
                registrar_auditoria("INATIVAR", "FORNECEDORES", "Fornecedor inativado", fornecedor_sel, antes_fornecedor, {"status": "Inativo"})
                st.success("Fornecedor inativado")

    st.divider()
    st.subheader("Fornecedores cadastrados")
    st.dataframe(df_fornecedores, use_container_width=True)


# =========================
# BASES
# =========================
elif menu in ["CONTROLE DE FALTAS", "BASES"]:
    st.title("BASES")

    presenca_opcoes = ["PRESENTE", "FALTOU", "FALTA MEIO PERIODO", "ATESTADO", "FOLGA", "FÉRIAS", "FERIADO"]
    almoco_opcoes = ["Sim", "Não"]
    escala_opcoes = ["SEGUNDA A SEXTA", "12X36"]
    funcao_opcoes = [
        "JARDINEIRO FIXO",
        "JARDINEIRO TEMPORARIO",
        "SUPERVISOR OPERACIONAL",
        "PORTARIA",
        "OFICIAL DE MANUTENÇÃO",
        "ELETRICISTA BAIXA TENSÃO",
        "SERVENTE DE LIMPEZA"
    ]
    if "base_faltas_selecionada" not in st.session_state:
        st.session_state["base_faltas_selecionada"] = ""

    if supervisor_base_mode and not st.session_state["base_faltas_selecionada"]:
        st.error("Nenhuma base foi liberada para este supervisor. Ajuste em Configurações > Usuários.")
        st.stop()

    if not supervisor_base_mode and not st.session_state["base_faltas_selecionada"]:
        st.subheader("Selecione A Base")
        portal_cols = st.columns(2)
        nomes_botoes_base = {
            "TMG BASE SORRISO": "BASE TMG SORRISO",
            "TMG BASE RONDONOPOLIS": "BASE TMG RONDONOPOLIS"
        }
        for idx_base, nome_base in enumerate(BASES_FREQUENCIA):
            if portal_cols[idx_base].button(nomes_botoes_base.get(nome_base, nome_base), use_container_width=True, key=f"portal_base_{nome_base}"):
                if usuario_pode_acessar_base(usuario_logado, nome_base):
                    st.session_state["base_faltas_selecionada"] = nome_base
                    st.session_state["subtela_faltas"] = ""
                    st.rerun()
                else:
                    st.session_state["erro_permissao_base"] = nome_base
                    st.rerun()
        if st.session_state.get("erro_permissao_base"):
            st.error(f"Você não tem permissão para acessar {st.session_state['erro_permissao_base']}.")
        st.stop()

    base_faltas_atual = st.session_state["base_faltas_selecionada"]
    if not usuario_pode_acessar_base(usuario_logado, base_faltas_atual):
        st.session_state["base_faltas_selecionada"] = ""
        st.error("Você não tem permissão para acessar esta base.")
        st.stop()

    topo_base, topo_voltar = st.columns([4, 1])
    topo_base.subheader(base_faltas_atual)
    if not supervisor_base_mode:
        if topo_voltar.button("Trocar Base", use_container_width=True, key="trocar_base_portal"):
            st.session_state["base_faltas_selecionada"] = ""
            st.rerun()

    supervisor_atual = config.get("supervisores_frequencia", {}).get(base_faltas_atual, "")

    faltas_base = df_faltas[df_faltas["base_frequencia"] == base_faltas_atual].copy()
    faltas_base["data_dt"] = pd.to_datetime(faltas_base["data"], errors="coerce")
    df_colaboradores_base = colaboradores_frequencia(faltas_base)
    df_colaboradores_ativos = df_colaboradores_base[df_colaboradores_base["status_colaborador"] != "Inativo"].copy()
    colaboradores = df_colaboradores_ativos["colaborador"].tolist()
    todos_colaboradores = df_colaboradores_base["colaborador"].tolist()
    funcoes_por_colaborador = df_colaboradores_ativos.set_index("colaborador")["funcao"].to_dict() if not df_colaboradores_ativos.empty else {}
    colunas_escala_ocultas = ["tipo_escala", "data_base_escala", "trabalha_data_base", "base_frequencia"]

    if "subtela_faltas" not in st.session_state:
        st.session_state["subtela_faltas"] = ""
    subtelas_antigas_bases = {
        "PAINEL": "LISTA DE FREQUÊNCIA",
        "LANÇAR PRESENÇA": "LISTA DE FREQUÊNCIA",
        "EDITAR LANÇAMENTO": "LISTA DE FREQUÊNCIA",
        "ESTOQUE DA BASE": "ESTOQUE",
        "RELATORIOS FREQUENCIA": "RELATORIOS_FREQUENCIA",
        "RELATÓRIOS FREQUÊNCIA": "RELATORIOS_FREQUENCIA",
        "RELATÓRIOS": "RELATORIOS_FREQUENCIA",
        "DESPESAS DE FROTA": "DESPESAS FROTAS",
        "DESPESAS FROTA": "DESPESAS FROTAS"
    }
    if st.session_state["subtela_faltas"] in subtelas_antigas_bases:
        st.session_state["subtela_faltas"] = subtelas_antigas_bases[st.session_state["subtela_faltas"]]

    subtela_faltas = st.session_state["subtela_faltas"]

    if not subtela_faltas and supervisor_base_mode:
        hoje_base = datetime.now().date()
        faltas_mes_base = faltas_base[
            (faltas_base["data_dt"].notna()) &
            (faltas_base["data_dt"].dt.month == hoje_base.month) &
            (faltas_base["data_dt"].dt.year == hoje_base.year) &
            (faltas_base["presenca"].astype(str).str.upper().isin(["FALTOU", "FALTA MEIO PERIODO"]))
        ].copy()
        total_faltas_mes = int(len(faltas_mes_base))
        total_registros = int(len(faltas_base))
        total_presentes = int((faltas_base["presenca"].astype(str).str.upper() == "PRESENTE").sum()) if not faltas_base.empty else 0
        estoque_base_resumo = calcular_estoque_base(df_bases_movimentacoes, base_faltas_atual)
        produtos_base_info_alerta = df_produtos[["produto", "estoque_minimo"]].copy() if not df_produtos.empty else pd.DataFrame(columns=["produto", "estoque_minimo"])
        estoque_base_alerta = estoque_base_resumo.merge(produtos_base_info_alerta, on="produto", how="left") if not estoque_base_resumo.empty else pd.DataFrame(columns=["produto", "estoque_atual", "estoque_minimo"])
        estoque_base_alerta["estoque_minimo"] = pd.to_numeric(estoque_base_alerta.get("estoque_minimo", 0), errors="coerce").fillna(0)
        estoque_base_alerta["estoque_atual"] = pd.to_numeric(estoque_base_alerta.get("estoque_atual", 0), errors="coerce").fillna(0)
        total_produtos_criticos = int((estoque_base_alerta["estoque_atual"] <= estoque_base_alerta["estoque_minimo"]).sum()) if not estoque_base_alerta.empty else 0

        data_hoje_texto = hoje_base.isoformat()
        registros_hoje = faltas_base[faltas_base["data"].astype(str) == data_hoje_texto]["colaborador"].astype(str).str.upper().nunique()
        total_colaboradores_ativos_base = len(df_colaboradores_ativos)
        frequencia_ok = total_colaboradores_ativos_base > 0 and registros_hoje >= total_colaboradores_ativos_base
        status_frequencia = "OK" if frequencia_ok else "Pendente"
        cor_frequencia = "#22c55e" if frequencia_ok else "#f59e0b"
        detalhe_frequencia = f"{registros_hoje}/{total_colaboradores_ativos_base} lançados hoje"

        pend_abastecimentos_base = int((df_frotas_abastecimentos["status_conferencia"].astype(str) == "Pendente").sum()) if not df_frotas_abastecimentos.empty else 0
        pend_manutencoes_base = int((df_frotas_manutencoes["status_conferencia"].astype(str) == "Pendente").sum()) if not df_frotas_manutencoes.empty else 0
        total_despesas_veiculo_pendentes = pend_abastecimentos_base + pend_manutencoes_base

        r1, r2, r3, r4 = st.columns(4)
        r1.markdown(f"<div class='metric-card'><div class='metric-label'>Alerta De Faltas No Mês</div><div class='metric-value' style='color:#ef4444'>{total_faltas_mes}</div><div class='metric-label'>Faltas registradas</div></div>", unsafe_allow_html=True)
        r2.markdown(f"<div class='metric-card'><div class='metric-label'>Produtos Críticos</div><div class='metric-value' style='color:#f59e0b'>{total_produtos_criticos}</div><div class='metric-label'>Abaixo ou igual ao mínimo</div></div>", unsafe_allow_html=True)
        r3.markdown(f"<div class='metric-card'><div class='metric-label'>Lançamento De Frequência</div><div class='metric-value' style='color:{cor_frequencia}'>{status_frequencia}</div><div class='metric-label'>{detalhe_frequencia}</div></div>", unsafe_allow_html=True)
        r4.markdown(f"<div class='metric-card'><div class='metric-label'>Despesas Com Veículo Pendentes</div><div class='metric-value' style='color:#f59e0b'>{total_despesas_veiculo_pendentes}</div><div class='metric-label'>Abast. {pend_abastecimentos_base} | Manut. {pend_manutencoes_base}</div></div>", unsafe_allow_html=True)
        st.info("Use o menu lateral para acessar Lista De Frequência, Estoque ou Despesas Frota.")

    elif not subtela_faltas and not supervisor_base_mode:
        abas_faltas = ["LISTA DE FREQUÊNCIA", "ESTOQUE", "DESPESAS FROTAS"]
        if nivel_usuario(usuario_logado) == "ADM":
            abas_faltas = ["LISTA DE FREQUÊNCIA"]
        nav_cols = st.columns(len(abas_faltas))
        for idx_nav, nome_aba in enumerate(abas_faltas):
            if nav_cols[idx_nav].button(
                nome_aba,
                type="primary",
                use_container_width=True,
                key=f"faltas_nav_{nome_aba}"
            ):
                st.session_state["subtela_faltas"] = nome_aba
                st.rerun()

    elif subtela_faltas == "PAINEL":
        st.subheader("Painel")
        resumo_status = pd.DataFrame(columns=["presenca", "quantidade"])
        if not faltas_base.empty:
            resumo_status = faltas_base["presenca"].replace("", "NÃO LANÇADO").value_counts().reset_index()
            resumo_status.columns = ["presenca", "quantidade"]

        col_painel1, col_painel2 = st.columns(2)
        with col_painel1:
            st.write("Resumo por presença")
            st.dataframe(formatar_colunas_tabela(resumo_status), use_container_width=True)
        with col_painel2:
            resumo_funcao = pd.DataFrame(columns=["funcao", "almocos"])
            if not faltas_base.empty:
                resumo_funcao = faltas_base[faltas_base["almocou_base"].astype(str).str.upper() == "SIM"].groupby("funcao").size().reset_index(name="almocos")
            st.write("Almoços por função")
            st.dataframe(formatar_colunas_tabela(resumo_funcao), use_container_width=True)

        st.subheader("Últimos lançamentos")
        ultimos = faltas_base.drop(columns=["data_dt"] + colunas_escala_ocultas, errors="ignore").tail(50)
        st.dataframe(formatar_colunas_tabela(ultimos), use_container_width=True)

    elif subtela_faltas == "LISTA DE FREQUÊNCIA":
        if not supervisor_base_mode and st.button("Voltar", use_container_width=True, key="voltar_base_lista"):
            st.session_state["subtela_faltas"] = ""
            st.rerun()
        acao_lista_cols = st.columns(3)
        if acao_lista_cols[0].button("Lançar Presença", type="primary", use_container_width=True, key="acao_lancar_presenca_base"):
            st.session_state["subtela_faltas"] = "LISTA DE FREQUÊNCIA"
            st.rerun()
        if acao_lista_cols[1].button("Cadastrar / Editar / Inativar Colaboradores", use_container_width=True, key="acao_colaboradores_base"):
            st.session_state["subtela_faltas"] = "COLABORADORES"
            st.rerun()
        if acao_lista_cols[2].button("Painel De Relatórios", use_container_width=True, key="acao_relatorios_frequencia_base"):
            st.session_state["subtela_faltas"] = "RELATORIOS_FREQUENCIA"
            st.rerun()
        st.divider()
        meses_pt = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        hoje_calendario = datetime.now().date()
        cal_mes_col, cal_ano_col = st.columns([2, 1])
        mes_calendario = cal_mes_col.selectbox(
            "Mês do calendário",
            list(range(1, 13)),
            index=hoje_calendario.month - 1,
            format_func=lambda mes: meses_pt[mes - 1],
            key=f"calendario_frequencia_mes_{base_faltas_atual}"
        )
        ano_calendario = int(cal_ano_col.number_input(
            "Ano",
            min_value=2020,
            max_value=2100,
            value=hoje_calendario.year,
            step=1,
            key=f"calendario_frequencia_ano_{base_faltas_atual}"
        ))
        total_colaboradores_ativos = len(df_colaboradores_ativos)
        faltas_mes = faltas_base[
            (faltas_base["data_dt"].notna()) &
            (faltas_base["data_dt"].dt.month == mes_calendario) &
            (faltas_base["data_dt"].dt.year == ano_calendario)
        ].copy()
        lancamentos_por_dia = {}
        if not faltas_mes.empty:
            lancamentos_por_dia = faltas_mes.groupby(faltas_mes["data_dt"].dt.day)["colaborador"].nunique().to_dict()

        semanas_mes = calendar.monthcalendar(ano_calendario, mes_calendario)
        dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
        linhas_calendario = ""
        for semana in semanas_mes:
            celulas_semana = ""
            for dia in semana:
                if dia == 0:
                    celulas_semana += "<div class='cal-dia cal-vazio'></div>"
                    continue
                qtd_lancada = int(lancamentos_por_dia.get(dia, 0))
                if qtd_lancada <= 0:
                    classe_status = "cal-sem-lancamento"
                    texto_status = "Sem lançamento"
                elif total_colaboradores_ativos > 0 and qtd_lancada >= total_colaboradores_ativos:
                    classe_status = "cal-completo"
                    texto_status = "Completo"
                else:
                    classe_status = "cal-parcial"
                    texto_status = "Parcial"
                celulas_semana += (
                    f"<div class='cal-dia {classe_status}'>"
                    f"<strong>{dia}</strong>"
                    f"<span>{texto_status}</span>"
                    f"<small>{qtd_lancada}/{total_colaboradores_ativos}</small>"
                    "</div>"
                )
            linhas_calendario += f"<div class='cal-linha'>{celulas_semana}</div>"

        cabecalho_calendario = "".join([f"<div class='cal-semana'>{dia}</div>" for dia in dias_semana])
        st.markdown(
            f"""
            <style>
                .calendario-frequencia {{
                    background: linear-gradient(180deg, rgba(15,23,42,.96), rgba(17,24,39,.96));
                    border: 1px solid rgba(148,163,184,.22);
                    border-radius: 8px;
                    padding: 14px;
                    margin: 8px 0 18px 0;
                }}
                .cal-titulo {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    color: #f8fafc;
                    font-weight: 800;
                    margin-bottom: 12px;
                }}
                .cal-legenda {{
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    color: #cbd5e1;
                    font-size: 12px;
                    font-weight: 700;
                }}
                .cal-legenda span {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }}
                .cal-bolinha {{
                    width: 10px;
                    height: 10px;
                    border-radius: 999px;
                    display: inline-block;
                }}
                .cal-grid, .cal-linha {{
                    display: grid;
                    grid-template-columns: repeat(7, minmax(0, 1fr));
                    gap: 7px;
                }}
                .cal-grid {{
                    margin-bottom: 7px;
                }}
                .cal-semana {{
                    color: #94a3b8;
                    font-size: 12px;
                    font-weight: 800;
                    text-align: center;
                }}
                .cal-linha {{
                    margin-bottom: 7px;
                }}
                .cal-dia {{
                    min-height: 76px;
                    border-radius: 8px;
                    padding: 9px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    border: 1px solid rgba(255,255,255,.12);
                    box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 8px 14px rgba(0,0,0,.18);
                    overflow: hidden;
                }}
                .cal-dia strong {{
                    color: #fff;
                    font-size: 18px;
                    line-height: 1;
                }}
                .cal-dia span, .cal-dia small {{
                    color: rgba(255,255,255,.92);
                    font-size: 11px;
                    font-weight: 800;
                    line-height: 1.15;
                }}
                .cal-vazio {{
                    background: transparent;
                    border-color: transparent;
                    box-shadow: none;
                }}
                .cal-sem-lancamento {{
                    background: #1f2937;
                }}
                .cal-parcial {{
                    background: linear-gradient(180deg, #f59e0b, #b45309);
                }}
                .cal-completo {{
                    background: linear-gradient(180deg, #22c55e, #15803d);
                }}
                @media (max-width: 700px) {{
                    .calendario-frequencia {{
                        padding: 10px;
                    }}
                    .cal-grid, .cal-linha {{
                        gap: 4px;
                    }}
                    .cal-dia {{
                        min-height: 58px;
                        padding: 6px;
                    }}
                    .cal-dia strong {{
                        font-size: 15px;
                    }}
                    .cal-dia span {{
                        display: none;
                    }}
                    .cal-dia small {{
                        font-size: 10px;
                    }}
                }}
            </style>
            <div class="calendario-frequencia">
                <div class="cal-titulo">
                    <div>{meses_pt[mes_calendario - 1]} / {ano_calendario}</div>
                    <div class="cal-legenda">
                        <span><i class="cal-bolinha" style="background:#22c55e"></i>Completo</span>
                        <span><i class="cal-bolinha" style="background:#f59e0b"></i>Parcial</span>
                        <span><i class="cal-bolinha" style="background:#1f2937;border:1px solid rgba(255,255,255,.28)"></i>Sem lançamento</span>
                    </div>
                </div>
                <div class="cal-grid">{cabecalho_calendario}</div>
                {linhas_calendario}
            </div>
            """,
            unsafe_allow_html=True
        )
        data_registro = st.date_input("DATA", value=datetime.now().date())
        feriado_lancamento = st.checkbox("Feriado", value=False)

        if df_colaboradores_ativos.empty:
            st.info("Cadastre colaboradores ativos antes de lançar presença.")
        else:
            data_texto = data_registro.isoformat()
            estado_lancamento = f"{data_texto}_{int(feriado_lancamento)}"
            registros_existentes = faltas_base[faltas_base["data"].astype(str) == data_texto]["colaborador"].astype(str).str.upper().tolist()
            linhas_lancamento = []
            df_colaboradores_lancamento = df_colaboradores_ativos.sort_values("colaborador", kind="stable").reset_index(drop=True)
            for _, colaborador_row in df_colaboradores_lancamento.iterrows():
                colaborador_nome = str(colaborador_row["colaborador"]).strip().upper()
                presenca_prevista = status_previsto_escala(
                    data_registro,
                    colaborador_row.get("tipo_escala", "SEGUNDA A SEXTA"),
                    colaborador_row.get("data_base_escala", ""),
                    colaborador_row.get("trabalha_data_base", "Sim"),
                    feriado_lancamento
                )
                almoco_previsto = "Sim" if presenca_prevista == "PRESENTE" else "Não"
                linhas_lancamento.append({
                    "lançar": colaborador_nome not in registros_existentes,
                    "colaborador": colaborador_nome,
                    "funcao": str(colaborador_row.get("funcao", "")).strip().upper(),
                    "presenca": presenca_prevista,
                    "motivo_falta": "",
                    "almocou_base": almoco_previsto,
                    "observacoes": ""
                })

            presenca_todos = st.selectbox(
                "APLICAR PRESENÇA PARA TODOS",
                ["Manter sugestão"] + presenca_opcoes,
                key=f"presenca_todos_{estado_lancamento}"
            )
            df_lancamento_base = pd.DataFrame(linhas_lancamento).sort_values("colaborador", kind="stable").reset_index(drop=True)
            if presenca_todos != "Manter sugestão":
                df_lancamento_base["presenca"] = presenca_todos
                df_lancamento_base["almocou_base"] = "Sim" if presenca_todos == "PRESENTE" else "Não"

            st.caption("Use os campos de seleção para escolher a presença. Não é necessário digitar o status.")
            headers = st.columns([0.7, 2.2, 1.7, 1.7, 2.2, 1.3, 2.2])
            headers[0].write("Lançar")
            headers[1].write("Colaborador")
            headers[2].write("Função")
            headers[3].write("Presença")
            headers[4].write("Motivo da falta")
            headers[5].write("Almoço")
            headers[6].write("Observações")

            linhas_editadas = []
            for idx_lanc, row in df_lancamento_base.iterrows():
                row_cols = st.columns([0.7, 2.2, 1.7, 1.7, 2.2, 1.3, 2.2])
                colaborador_nome = str(row["colaborador"])
                presenca_atual = str(row["presenca"]).upper()
                almoco_atual = str(row["almocou_base"]).capitalize()
                lancar = row_cols[0].checkbox(
                    "Lançar",
                    value=bool(row["lançar"]),
                    key=f"faltas_lancar_{estado_lancamento}_{idx_lanc}",
                    label_visibility="collapsed"
                )
                row_cols[1].write(colaborador_nome)
                row_cols[2].write(str(row["funcao"]))
                presenca_linha = row_cols[3].selectbox(
                    "Presença",
                    presenca_opcoes,
                    index=presenca_opcoes.index(presenca_atual) if presenca_atual in presenca_opcoes else 0,
                    key=f"faltas_presenca_{estado_lancamento}_{idx_lanc}",
                    label_visibility="collapsed"
                )
                motivo_linha = row_cols[4].text_input(
                    "Motivo da falta",
                    value=str(row.get("motivo_falta", "")),
                    key=f"faltas_motivo_{estado_lancamento}_{idx_lanc}",
                    label_visibility="collapsed"
                )
                almoco_default = "Sim" if presenca_linha == "PRESENTE" else "Não"
                almoco_linha = row_cols[5].selectbox(
                    "Almoço",
                    almoco_opcoes,
                    index=almoco_opcoes.index(almoco_default),
                    key=f"faltas_almoco_{estado_lancamento}_{idx_lanc}",
                    label_visibility="collapsed"
                )
                observacoes_linha = row_cols[6].text_input(
                    "Observações",
                    value=str(row.get("observacoes", "")),
                    key=f"faltas_obs_{estado_lancamento}_{idx_lanc}",
                    label_visibility="collapsed"
                )
                linhas_editadas.append({
                    "lançar": lancar,
                    "colaborador": colaborador_nome,
                    "funcao": str(row["funcao"]),
                    "presenca": presenca_linha,
                    "motivo_falta": motivo_linha,
                    "almocou_base": almoco_linha,
                    "observacoes": observacoes_linha
                })

            df_lancamento = pd.DataFrame(linhas_editadas)

            if registros_existentes:
                st.warning("Alguns colaboradores já possuem lançamento nesta data. Eles vieram desmarcados para evitar duplicidade.")

            if st.button("Salvar todos os lançamentos", type="primary", use_container_width=True):
                selecionados = df_lancamento[df_lancamento["lançar"] == True].copy()
                erros = []
                for posicao, row in selecionados.iterrows():
                    if not str(row.get("colaborador", "")).strip():
                        erros.append(f"linha {posicao + 1}: colaborador")
                    if not str(row.get("funcao", "")).strip():
                        erros.append(f"linha {posicao + 1}: função")
                    if str(row.get("presenca", "")).upper() in ["FALTOU", "FALTA MEIO PERIODO"] and not str(row.get("motivo_falta", "")).strip():
                        erros.append(f"linha {posicao + 1}: motivo da falta")

                if selecionados.empty:
                    st.error("Selecione pelo menos um colaborador para salvar.")
                elif erros:
                    st.error("Preencha os campos obrigatórios: " + "; ".join(erros) + ".")
                else:
                    novos = selecionados.drop(columns=["lançar"], errors="ignore").copy()
                    novos.insert(0, "data", data_texto)
                    novos["tipo_escala"] = novos["colaborador"].map(df_colaboradores_lancamento.set_index("colaborador")["tipo_escala"]).fillna("SEGUNDA A SEXTA")
                    novos["data_base_escala"] = novos["colaborador"].map(df_colaboradores_lancamento.set_index("colaborador")["data_base_escala"]).fillna("")
                    novos["trabalha_data_base"] = novos["colaborador"].map(df_colaboradores_lancamento.set_index("colaborador")["trabalha_data_base"]).fillna("Sim")
                    novos["status_colaborador"] = "Ativo"
                    novos["base_frequencia"] = base_faltas_atual
                    df_faltas = pd.concat([df_faltas.drop(columns=["data_dt"], errors="ignore"), novos], ignore_index=True)
                    df_faltas.to_excel(CONTROLE_FALTAS_XLSX, index=False)
                    st.success("Lançamentos salvos com sucesso.")
                    st.rerun()

    elif subtela_faltas == "EDITAR LANÇAMENTO":
        if faltas_base.empty:
            st.info("Nenhum registro de frequência cadastrado.")
        else:
            opcoes_registros = {
                f"{idx} - {row['data']} - {row['colaborador']} - {row['presenca']}": idx
                for idx, row in faltas_base.iterrows()
            }
            registro_label = st.selectbox("Registro", list(opcoes_registros.keys()))
            idx = opcoes_registros[registro_label]
            dados = df_faltas.loc[idx]
            data_atual = pd.to_datetime(dados.get("data", ""), errors="coerce")
            data_edit = st.date_input("DATA", value=data_atual.date() if pd.notna(data_atual) else datetime.now().date(), key="faltas_data_edit")
            colaborador_edit = st.text_input("COLABORADOR", str(dados.get("colaborador", ""))).strip().upper()
            funcao_edit = st.text_input("FUNÇÃO", str(dados.get("funcao", ""))).strip().upper()
            presenca_atual = str(dados.get("presenca", "PRESENTE")).upper()
            presenca_edit = st.selectbox("PRESENÇA", presenca_opcoes, index=presenca_opcoes.index(presenca_atual) if presenca_atual in presenca_opcoes else 0, key="faltas_presenca_edit")
            motivo_edit = st.text_input("MOTIVO DA FALTA", str(dados.get("motivo_falta", "")))
            almoco_atual = str(dados.get("almocou_base", "Sim")).capitalize()
            almoco_edit = st.selectbox("ALMOÇOU NA BASE?", almoco_opcoes, index=almoco_opcoes.index(almoco_atual) if almoco_atual in almoco_opcoes else 0, key="faltas_almoco_edit")
            obs_edit = st.text_area("OBSERVAÇÕES", str(dados.get("observacoes", "")))

            if st.button("Salvar alteração de frequência"):
                if not colaborador_edit or not funcao_edit:
                    st.error("Preencha colaborador e função antes de salvar.")
                elif presenca_edit in ["FALTOU", "FALTA MEIO PERIODO"] and not motivo_edit.strip():
                    st.error("Informe o motivo da falta antes de salvar.")
                else:
                    df_faltas.loc[idx, "data"] = data_edit.isoformat()
                    df_faltas.loc[idx, "colaborador"] = colaborador_edit
                    df_faltas.loc[idx, "funcao"] = funcao_edit
                    df_faltas.loc[idx, "presenca"] = presenca_edit
                    df_faltas.loc[idx, "motivo_falta"] = motivo_edit.strip()
                    df_faltas.loc[idx, "almocou_base"] = almoco_edit
                    df_faltas.loc[idx, "observacoes"] = obs_edit.strip()
                    df_faltas.drop(columns=["data_dt"], errors="ignore").to_excel(CONTROLE_FALTAS_XLSX, index=False)
                    st.success("Registro atualizado.")
                    st.rerun()

            st.divider()
            st.subheader("Cancelar lançamento")
            registro_excluir = st.selectbox("Registro para cancelar", list(opcoes_registros.keys()), key="faltas_excluir")
            idx_excluir = opcoes_registros[registro_excluir]
            if st.button("Cancelar registro de frequência"):
                registro_cancelado = df_faltas.loc[idx_excluir].to_dict()
                df_faltas = df_faltas.drop(index=idx_excluir).reset_index(drop=True)
                df_faltas.drop(columns=["data_dt"], errors="ignore").to_excel(CONTROLE_FALTAS_XLSX, index=False)
                registrar_auditoria("CANCELAR", "FREQUÊNCIA", "Registro de frequência cancelado", registro_excluir, registro_cancelado, None)
                st.success("Registro cancelado.")
                st.rerun()

    elif subtela_faltas == "COLABORADORES":
        if st.button("Voltar Para Lançamentos", use_container_width=True, key="voltar_colaboradores_lancamentos"):
            st.session_state["subtela_faltas"] = "LISTA DE FREQUÊNCIA"
            st.rerun()
        st.subheader("Colaboradores")
        df_colaboradores = df_colaboradores_base.copy()
        if not df_colaboradores.empty:
            contagem_registros = faltas_base[faltas_base["data"].astype(str).str.strip() != ""].groupby("colaborador").size()
            df_colaboradores["registros"] = df_colaboradores["colaborador"].map(contagem_registros).fillna(0).astype(int)
        else:
            df_colaboradores = pd.DataFrame(columns=["colaborador", "funcao", "tipo_escala", "data_base_escala", "trabalha_data_base", "status_colaborador", "registros"])

        colab1, colab2 = st.columns(2)
        with colab1:
            st.write("Adicionar colaborador")
            novo_colaborador = st.text_input("NOME DO COLABORADOR", key="novo_colaborador_faltas").strip().upper()
            nova_funcao = st.selectbox("FUNÇÃO", funcao_opcoes, key="nova_funcao_faltas")
            novo_tipo_escala = st.selectbox("TIPO DE ESCALA", escala_opcoes, key="novo_tipo_escala_faltas")
            nova_data_base = ""
            novo_trabalha_base = "Sim"
            if novo_tipo_escala == "12X36":
                nova_data_base = st.date_input("DATA BASE DA ESCALA", value=datetime.now().date(), key="nova_data_base_escala").isoformat()
                novo_trabalha_base = st.selectbox("TRABALHA NA DATA BASE?", ["Sim", "Não"], key="novo_trabalha_data_base")
            if st.button("ADICIONAR COLABORADOR"):
                if not novo_colaborador or not nova_funcao:
                    st.error("Preencha colaborador e função.")
                elif novo_colaborador in todos_colaboradores:
                    st.error("Este colaborador já existe nos registros.")
                else:
                    novo = pd.DataFrame([{
                        "data": "",
                        "colaborador": novo_colaborador,
                        "funcao": nova_funcao,
                        "presenca": "",
                        "motivo_falta": "",
                        "almocou_base": "",
                        "observacoes": "Cadastro de colaborador",
                        "tipo_escala": novo_tipo_escala,
                        "data_base_escala": nova_data_base,
                        "trabalha_data_base": novo_trabalha_base,
                        "status_colaborador": "Ativo",
                        "base_frequencia": base_faltas_atual
                    }])
                    df_faltas = pd.concat([df_faltas.drop(columns=["data_dt"], errors="ignore"), novo], ignore_index=True)
                    df_faltas.to_excel(CONTROLE_FALTAS_XLSX, index=False)
                    st.success("Colaborador adicionado.")
                    st.rerun()

        with colab2:
            st.write("Editar colaborador")
            if todos_colaboradores:
                colaborador_alterar = st.selectbox("COLABORADOR", todos_colaboradores, key="colaborador_funcao_edit")
                dados_colaborador = df_colaboradores_base[df_colaboradores_base["colaborador"] == colaborador_alterar].iloc[0]
                nome_alterar = st.text_input("NOME DO COLABORADOR", value=colaborador_alterar, key="nome_colaborador_edit").strip().upper()
                funcao_atual = str(dados_colaborador.get("funcao", ""))
                funcao_alterar = st.selectbox(
                    "FUNÇÃO",
                    funcao_opcoes,
                    index=funcao_opcoes.index(funcao_atual) if funcao_atual in funcao_opcoes else 0,
                    key="funcao_colaborador_edit"
                )
                escala_atual = str(dados_colaborador.get("tipo_escala", "SEGUNDA A SEXTA")).upper()
                tipo_escala_alterar = st.selectbox(
                    "TIPO DE ESCALA",
                    escala_opcoes,
                    index=escala_opcoes.index(escala_atual) if escala_atual in escala_opcoes else 0,
                    key="tipo_escala_colaborador_edit"
                )
                data_base_atual = pd.to_datetime(dados_colaborador.get("data_base_escala", ""), errors="coerce")
                data_base_alterar = ""
                trabalha_base_alterar = "Sim"
                if tipo_escala_alterar == "12X36":
                    data_base_alterar = st.date_input(
                        "DATA BASE DA ESCALA",
                        value=data_base_atual.date() if pd.notna(data_base_atual) else datetime.now().date(),
                        key="data_base_colaborador_edit"
                    ).isoformat()
                    trabalha_atual = str(dados_colaborador.get("trabalha_data_base", "Sim")).capitalize()
                    trabalha_base_alterar = st.selectbox(
                        "TRABALHA NA DATA BASE?",
                        ["Sim", "Não"],
                        index=0 if trabalha_atual != "Não" else 1,
                        key="trabalha_base_colaborador_edit"
                    )

                status_atual = str(dados_colaborador.get("status_colaborador", "Ativo")).capitalize()
                status_alterar = st.selectbox(
                    "STATUS",
                    ["Ativo", "Inativo"],
                    index=0 if status_atual != "Inativo" else 1,
                    key="status_colaborador_edit"
                )

                if st.button("SALVAR COLABORADOR"):
                    if not nome_alterar or not funcao_alterar:
                        st.error("Informe nome e função.")
                    elif nome_alterar != colaborador_alterar and nome_alterar in todos_colaboradores:
                        st.error("Já existe outro colaborador com este nome.")
                    else:
                        mask_colaborador = (
                            (df_faltas["base_frequencia"] == base_faltas_atual)
                            & (df_faltas["colaborador"] == colaborador_alterar)
                        )
                        df_faltas.loc[mask_colaborador, "colaborador"] = nome_alterar
                        df_faltas.loc[mask_colaborador, "funcao"] = funcao_alterar
                        df_faltas.loc[mask_colaborador, "tipo_escala"] = tipo_escala_alterar
                        df_faltas.loc[mask_colaborador, "data_base_escala"] = data_base_alterar
                        df_faltas.loc[mask_colaborador, "trabalha_data_base"] = trabalha_base_alterar
                        df_faltas.loc[mask_colaborador, "status_colaborador"] = status_alterar
                        df_faltas.drop(columns=["data_dt"], errors="ignore").to_excel(CONTROLE_FALTAS_XLSX, index=False)
                        st.success("Colaborador atualizado.")
                        st.rerun()
            else:
                st.info("Nenhum colaborador cadastrado.")

        st.divider()
        st.subheader("Inativar colaborador")
        colaboradores_ativos_para_inativar = df_colaboradores_base[df_colaboradores_base["status_colaborador"] != "Inativo"]["colaborador"].tolist()
        if colaboradores_ativos_para_inativar:
            colaborador_inativar = st.selectbox("COLABORADOR PARA INATIVAR", colaboradores_ativos_para_inativar, key="colaborador_inativar")
            if st.button("INATIVAR COLABORADOR"):
                df_faltas.loc[
                    (df_faltas["base_frequencia"] == base_faltas_atual)
                    & (df_faltas["colaborador"] == colaborador_inativar),
                    "status_colaborador"
                ] = "Inativo"
                df_faltas.drop(columns=["data_dt"], errors="ignore").to_excel(CONTROLE_FALTAS_XLSX, index=False)
                st.success("Colaborador inativado.")
                st.rerun()
        else:
            st.info("Nenhum colaborador ativo para inativar.")

        st.divider()
        st.info("Para manter o histórico, colaboradores não são excluídos. Use a opção de inativar acima.")

        st.dataframe(formatar_colunas_tabela(df_colaboradores.drop(columns=colunas_escala_ocultas, errors="ignore")), use_container_width=True, hide_index=True)

    elif subtela_faltas == "RELATORIOS_FREQUENCIA":
        if st.button("Voltar Para Lançamentos", use_container_width=True, key="voltar_relatorios_lancamentos"):
            st.session_state["subtela_faltas"] = "LISTA DE FREQUÊNCIA"
            st.rerun()
        st.subheader("Painel De Relatórios")
        registros_relatorio = faltas_base[
            (faltas_base["data"].astype(str).str.strip() != "")
            & (faltas_base["data_dt"].notna())
        ].copy()

        if registros_relatorio.empty:
            st.info("Nenhum lançamento de frequência encontrado para gerar relatório.")
        else:
            data_minima = registros_relatorio["data_dt"].min().date()
            data_maxima = registros_relatorio["data_dt"].max().date()
            filtro_ini_col, filtro_fim_col = st.columns(2)
            data_inicio_rel = filtro_ini_col.date_input("Data Inicial", value=data_minima, key="rel_frequencia_inicio")
            data_fim_rel = filtro_fim_col.date_input("Data Final", value=data_maxima, key="rel_frequencia_fim")

            if data_inicio_rel > data_fim_rel:
                st.error("A data inicial não pode ser maior que a data final.")
            else:
                rel_filtrado = registros_relatorio[
                    (registros_relatorio["data_dt"].dt.date >= data_inicio_rel)
                    & (registros_relatorio["data_dt"].dt.date <= data_fim_rel)
                ].copy()

                total_lancamentos = len(rel_filtrado)
                total_presentes = int((rel_filtrado["presenca"].astype(str).str.upper() == "PRESENTE").sum()) if not rel_filtrado.empty else 0
                total_faltas = int(rel_filtrado["presenca"].astype(str).str.upper().isin(["FALTOU", "FALTA MEIO PERIODO"]).sum()) if not rel_filtrado.empty else 0
                total_atestados = int((rel_filtrado["presenca"].astype(str).str.upper() == "ATESTADO").sum()) if not rel_filtrado.empty else 0
                total_almocos = int((rel_filtrado["almocou_base"].astype(str).str.upper() == "SIM").sum()) if not rel_filtrado.empty else 0
                metricas_frequencia = {
                    "lancamentos": total_lancamentos,
                    "presentes": total_presentes,
                    "faltas": total_faltas,
                    "atestados": total_atestados,
                    "almocos": total_almocos
                }

                met1, met2, met3, met4, met5 = st.columns(5)
                met1.markdown(f"<div class='metric-card'><div class='metric-label'>Lançamentos</div><div class='metric-value'>{total_lancamentos}</div></div>", unsafe_allow_html=True)
                met2.markdown(f"<div class='metric-card'><div class='metric-label'>Presentes</div><div class='metric-value' style='color:#22c55e'>{total_presentes}</div></div>", unsafe_allow_html=True)
                met3.markdown(f"<div class='metric-card'><div class='metric-label'>Faltas</div><div class='metric-value' style='color:#ef4444'>{total_faltas}</div></div>", unsafe_allow_html=True)
                met4.markdown(f"<div class='metric-card'><div class='metric-label'>Atestados</div><div class='metric-value' style='color:#f59e0b'>{total_atestados}</div></div>", unsafe_allow_html=True)
                met5.markdown(f"<div class='metric-card'><div class='metric-label'>Almoços</div><div class='metric-value'>{total_almocos}</div></div>", unsafe_allow_html=True)

                st.divider()
                rel_col1, rel_col2 = st.columns(2)
                with rel_col1:
                    st.write("Resumo Por Presença")
                    resumo_presenca = rel_filtrado["presenca"].fillna("").replace("", "NÃO INFORMADO").value_counts().reset_index()
                    resumo_presenca.columns = ["presenca", "quantidade"]
                    st.dataframe(formatar_colunas_tabela(resumo_presenca), use_container_width=True, hide_index=True)

                    st.write("Resumo Por Função")
                    resumo_funcao = rel_filtrado.groupby("funcao").size().reset_index(name="quantidade") if not rel_filtrado.empty else pd.DataFrame(columns=["funcao", "quantidade"])
                    st.dataframe(formatar_colunas_tabela(resumo_funcao), use_container_width=True, hide_index=True)

                with rel_col2:
                    st.write("Resumo Por Dia")
                    resumo_dia = rel_filtrado.groupby(rel_filtrado["data_dt"].dt.date).agg(
                        lancamentos=("colaborador", "count"),
                        presentes=("presenca", lambda serie: int((serie.astype(str).str.upper() == "PRESENTE").sum())),
                        faltas=("presenca", lambda serie: int(serie.astype(str).str.upper().isin(["FALTOU", "FALTA MEIO PERIODO"]).sum())),
                        almocos=("almocou_base", lambda serie: int((serie.astype(str).str.upper() == "SIM").sum()))
                    ).reset_index()
                    resumo_dia = resumo_dia.rename(columns={"data_dt": "data"})
                    st.dataframe(formatar_colunas_tabela(resumo_dia), use_container_width=True, hide_index=True)

                    st.write("Quantidade De Almoço Por Função")
                    rel_almocos = rel_filtrado[rel_filtrado["almocou_base"].astype(str).str.upper() == "SIM"].copy()
                    resumo_almoco_funcao = rel_almocos.groupby("funcao").size().reset_index(name="quantidade_almocos") if not rel_almocos.empty else pd.DataFrame(columns=["funcao", "quantidade_almocos"])
                    st.dataframe(formatar_colunas_tabela(resumo_almoco_funcao), use_container_width=True, hide_index=True)

                st.write("Resumo Por Colaborador")
                resumo_colaborador = rel_filtrado.groupby("colaborador").agg(
                    lancamentos=("colaborador", "count"),
                    presentes=("presenca", lambda serie: int((serie.astype(str).str.upper() == "PRESENTE").sum())),
                    faltas=("presenca", lambda serie: int(serie.astype(str).str.upper().isin(["FALTOU", "FALTA MEIO PERIODO"]).sum())),
                    atestados=("presenca", lambda serie: int((serie.astype(str).str.upper() == "ATESTADO").sum())),
                    almocos=("almocou_base", lambda serie: int((serie.astype(str).str.upper() == "SIM").sum()))
                ).reset_index() if not rel_filtrado.empty else pd.DataFrame(columns=["colaborador", "lancamentos", "presentes", "faltas", "atestados", "almocos"])
                st.dataframe(formatar_colunas_tabela(resumo_colaborador), use_container_width=True, hide_index=True)

                st.write("Lançamentos Do Período")
                colunas_relatorio = ["data", "colaborador", "funcao", "presenca", "motivo_falta", "almocou_base", "observacoes"]
                st.dataframe(formatar_colunas_tabela(rel_filtrado[colunas_relatorio]), use_container_width=True, hide_index=True)
                st.divider()
                tipo_pdf_frequencia = st.selectbox(
                    "Selecionar Relatorio Para PDF",
                    ["Completo", "Por Presenca", "Por Funcao", "Por Dia", "Por Colaborador", "Almoco Por Funcao", "Lancamentos Detalhados"],
                    key="tipo_pdf_frequencia"
                )
                nome_base_pdf = base_faltas_atual.lower().replace(" ", "_")
                nome_tipo_pdf = tipo_pdf_frequencia.lower().replace(" ", "_")
                pdf_frequencia = gerar_pdf_relatorio_frequencia(
                    base_faltas_atual,
                    data_inicio_rel,
                    data_fim_rel,
                    rel_filtrado,
                    resumo_presenca,
                    resumo_funcao,
                    resumo_dia,
                    resumo_colaborador,
                    resumo_almoco_funcao,
                    metricas_frequencia,
                    tipo_pdf_frequencia
                )
                st.download_button(
                    "Baixar Relatório Em PDF",
                    data=pdf_frequencia,
                    file_name=f"relatorio_frequencia_{nome_tipo_pdf}_{nome_base_pdf}_{data_inicio_rel.isoformat()}_{data_fim_rel.isoformat()}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    elif subtela_faltas in ["ESTOQUE DA BASE", "ESTOQUE"]:
        if not supervisor_base_mode and st.button("Voltar", use_container_width=True, key="voltar_base_estoque"):
            st.session_state["subtela_faltas"] = ""
            st.session_state["acao_estoque_base"] = ""
            st.rerun()
        st.subheader(f"Estoque Local - {base_faltas_atual}")
        estoque_base = calcular_estoque_base(df_bases_movimentacoes, base_faltas_atual)
        st.session_state["acao_estoque_base"] = ""

        colunas_produto_base = ["codigo", "produto", "categoria", "estoque_minimo", "localizacao", "imagem"]
        produtos_base_info = df_produtos[colunas_produto_base].copy() if not df_produtos.empty else pd.DataFrame(columns=colunas_produto_base)
        estoque_base_view = estoque_base.merge(produtos_base_info, on="produto", how="left") if not estoque_base.empty else pd.DataFrame(columns=["produto", "entradas", "saidas", "estoque_atual"] + [c for c in colunas_produto_base if c != "produto"])
        for col_info in ["codigo", "categoria", "estoque_minimo", "localizacao", "imagem"]:
            if col_info not in estoque_base_view.columns:
                estoque_base_view[col_info] = ""
            estoque_base_view[col_info] = estoque_base_view[col_info].astype("object").fillna("")
        estoque_base_view["estoque_minimo"] = pd.to_numeric(estoque_base_view["estoque_minimo"], errors="coerce").fillna(0)
        estoque_base_view["situacao"] = estoque_base_view.apply(
            lambda row: "🔴 ESTOQUE BAIXO" if float(row.get("estoque_atual", 0)) <= float(row.get("estoque_minimo", 0)) else "🟢 OK",
            axis=1
        ) if not estoque_base_view.empty else ""

        total_itens_base = len(estoque_base_view)
        total_ok_base = int((estoque_base_view["situacao"] == "🟢 OK").sum()) if not estoque_base_view.empty else 0
        total_baixo_base = int((estoque_base_view["situacao"] == "🔴 ESTOQUE BAIXO").sum()) if not estoque_base_view.empty else 0

        b1, b2, b3 = st.columns(3)
        b1.markdown(f"<div class='metric-card'><div class='metric-label'>Total de Produtos Na Base</div><div class='metric-value'>{total_itens_base}</div><div class='metric-label'>{base_faltas_atual}</div></div>", unsafe_allow_html=True)
        b2.markdown(f"<div class='metric-card'><div class='metric-label'>Estoque OK</div><div class='metric-value' style='color:#22c55e'>{total_ok_base}</div><div class='metric-label'>Acima do mínimo</div></div>", unsafe_allow_html=True)
        b3.markdown(f"<div class='metric-card'><div class='metric-label'>Estoque Baixo</div><div class='metric-value' style='color:#ef4444'>{total_baixo_base}</div><div class='metric-label'>Abaixo ou igual ao mínimo</div></div>", unsafe_allow_html=True)

        reposicao_base = estoque_base_view.copy()
        reposicao_base["necessita"] = (reposicao_base["estoque_minimo"] + 5) - reposicao_base["estoque_atual"]
        reposicao_base = reposicao_base[reposicao_base["necessita"] > 0]
        if st.button("Solicitar Reposição Para Matriz", type="primary", use_container_width=True, key=f"solicitar_reposicao_{base_faltas_atual}"):
            if reposicao_base.empty:
                st.info("Nenhum item precisa de reposição nesta base.")
            else:
                pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                nome_base_arquivo = base_faltas_atual.lower().replace(" ", "_")
                caminho_pdf = os.path.join(pasta_downloads, f"solicitacao_reposicao_{nome_base_arquivo}.pdf")
                data_pdf = [["Código", "Produto", "Atual", "Mínimo", "Necessita", "Imagem"]]
                for _, r in reposicao_base.iterrows():
                    img_path = origem_imagem_produto(r.get("imagem", ""))
                    img_rl = ""
                    if img_path and os.path.exists(img_path):
                        try:
                            img_rl = RLImage(img_path, width=1 * inch, height=1 * inch)
                        except Exception:
                            pass
                    data_pdf.append([
                        r.get("codigo", ""),
                        r.get("produto", ""),
                        str(int(float(r.get("estoque_atual", 0)))),
                        str(int(float(r.get("estoque_minimo", 0)))),
                        str(int(float(r.get("necessita", 0)))),
                        img_rl
                    ])
                pdf = SimpleDocTemplate(caminho_pdf, pagesize=letter)
                tabela = Table(data_pdf, colWidths=[60, 150, 50, 60, 60, 100])
                tabela.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
                    ("TEXTCOLOR", (3, 1), (3, -1), colors.orange),
                    ("TEXTCOLOR", (4, 1), (4, -1), colors.red),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                ]))
                pdf.build([tabela])
                st.success(f"Solicitação de reposição salva em: {caminho_pdf}")

        st.markdown("<br>", unsafe_allow_html=True)
        busca_base = st.text_input("Busca", placeholder="BUSCAR POR CÓDIGO, PRODUTO OU CATEGORIA", label_visibility="collapsed", key=f"busca_estoque_base_{base_faltas_atual}")

        with st.expander("Filtros Avançados"):
            f_base_col1, f_base_col2 = st.columns(2)
            categorias_base = ["Todas"] + list(dict.fromkeys(estoque_base_view["categoria"].dropna().astype(str).tolist()))
            f_cat_base = f_base_col1.selectbox("Categoria", categorias_base, key=f"f_cat_base_{base_faltas_atual}")
            f_sit_base = f_base_col2.selectbox("Situação", ["Todas", "Estoque OK", "Estoque Baixo"], key=f"f_sit_base_{base_faltas_atual}")

        df_base_filtrado = estoque_base_view.copy()
        if busca_base:
            termo_base = str(busca_base).lower()
            df_base_filtrado = df_base_filtrado[
                df_base_filtrado["codigo"].astype(str).str.lower().str.contains(termo_base)
                | df_base_filtrado["produto"].astype(str).str.lower().str.contains(termo_base)
                | df_base_filtrado["categoria"].astype(str).str.lower().str.contains(termo_base)
            ]
        if f_cat_base != "Todas":
            df_base_filtrado = df_base_filtrado[df_base_filtrado["categoria"] == f_cat_base]
        if f_sit_base == "Estoque OK":
            df_base_filtrado = df_base_filtrado[df_base_filtrado["situacao"] == "🟢 OK"]
        elif f_sit_base == "Estoque Baixo":
            df_base_filtrado = df_base_filtrado[df_base_filtrado["situacao"] == "🔴 ESTOQUE BAIXO"]

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class='stock-table-header'>
                <div>Código</div>
                <div>Produto</div>
                <div>Categoria</div>
                <div>Atual</div>
                <div>Mínimo</div>
                <div>Localização</div>
                <div>Situação</div>
                <div>Imagem</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if df_base_filtrado.empty:
            st.info("Nenhum produto com estoque nesta base.")
        for i_base, row_base in df_base_filtrado.iterrows():
            col_base = st.columns([1, 2, 2, 1, 1, 2, 2, 3])
            col_base[0].write(row_base.get("codigo", ""))
            if col_base[1].button(row_base.get("produto", ""), key=f"prod_base_{base_faltas_atual}_{i_base}"):
                st.session_state["produto_base_historico"] = str(row_base.get("produto", ""))
            col_base[2].markdown(badge_categoria(row_base.get("categoria", "")), unsafe_allow_html=True)
            col_base[3].write(int(float(row_base.get("estoque_atual", 0))))
            col_base[4].markdown(f"<span style='color:#facc15'><b>{int(float(row_base.get('estoque_minimo', 0)))}</b></span>", unsafe_allow_html=True)
            col_base[5].write(row_base.get("localizacao", ""))
            col_base[6].markdown(badge_estoque(row_base.get("estoque_atual", 0), row_base.get("estoque_minimo", 0)), unsafe_allow_html=True)
            img_base = origem_imagem_produto(row_base.get("imagem", ""))
            if img_base:
                col_base[7].image(img_base, use_container_width=True)

        produto_base_historico = st.session_state.get("produto_base_historico", "")
        if produto_base_historico:
            st.divider()
            st.subheader(f"Histórico - {produto_base_historico}")
            hist_base_produto = df_bases_movimentacoes[
                (df_bases_movimentacoes["base"].astype(str) == base_faltas_atual)
                & (df_bases_movimentacoes["produto"].astype(str) == produto_base_historico)
            ].copy()
            if not hist_base_produto.empty:
                st.dataframe(formatar_colunas_tabela(hist_base_produto), use_container_width=True, hide_index=True)
            else:
                st.info("Sem movimentações para este produto nesta base.")
            if st.button("Fechar Histórico", key="fechar_historico_produto_base"):
                st.session_state.pop("produto_base_historico", None)
                st.rerun()
    elif subtela_faltas == "TRANSFERÊNCIAS":
        st.subheader("Transferência Da Matriz Para A Base")
        produtos_matriz = df_produtos["produto"].dropna().astype(str).tolist() if not df_produtos.empty else []
        if not produtos_matriz:
            st.info("Cadastre produtos no almoxarifado matriz antes de transferir.")
        else:
            c1, c2, c3 = st.columns(3)
            data_transf = c1.date_input("Data", value=datetime.now().date(), key="base_transf_data")
            produto_transf = c2.selectbox("Produto", produtos_matriz, key="base_transf_produto")
            quantidade_transf = c3.number_input("Quantidade", min_value=0.0, step=1.0, format="%.2f", key="base_transf_qtd")
            estoque_disponivel_matriz = estoque_matriz_produto(produto_transf)
            st.info(f"Estoque disponível na Matriz: {estoque_disponivel_matriz:,.2f}")
            c4, c5 = st.columns(2)
            responsavel_envio = c4.text_input("Responsável Pelo Envio", key="base_transf_envio").strip().upper()
            responsavel_recebimento = c5.text_input("Responsável Pelo Recebimento", key="base_transf_recebimento").strip().upper()
            obs_transf = st.text_area("Observações", key="base_transf_obs").strip()

            if st.button("ENVIAR PARA BASE", type="primary", use_container_width=True):
                if quantidade_transf <= 0:
                    st.error("Informe uma quantidade maior que zero.")
                elif quantidade_transf > estoque_disponivel_matriz:
                    st.error("Quantidade maior que o estoque disponível na Matriz.")
                elif not responsavel_envio or not responsavel_recebimento:
                    st.error("Informe os responsáveis pelo envio e recebimento.")
                else:
                    nova_saida_matriz = pd.DataFrame([{
                        "produto": produto_transf,
                        "tipo": "Saída",
                        "quantidade": float(quantidade_transf),
                        "data": datetime.now(),
                        "cliente": base_faltas_atual,
                        "observacao": f"Transferência Matriz -> {base_faltas_atual}. {obs_transf}".strip()
                    }])
                    df_mov = pd.concat([df_mov, nova_saida_matriz], ignore_index=True)
                    df_mov.to_excel(MOVIMENTACOES_XLSX, index=False)

                    nova_entrada_base = pd.DataFrame([{
                        "data": data_transf.isoformat(),
                        "base": base_faltas_atual,
                        "produto": produto_transf,
                        "tipo": "Entrada",
                        "quantidade": float(quantidade_transf),
                        "responsavel": responsavel_recebimento,
                        "origem_destino": "MATRIZ",
                        "observacoes": obs_transf
                    }])
                    df_bases_movimentacoes = pd.concat([df_bases_movimentacoes, nova_entrada_base], ignore_index=True)
                    df_bases_movimentacoes.to_excel(BASES_MOVIMENTACOES_XLSX, index=False)

                    nova_transferencia = pd.DataFrame([{
                        "data": data_transf.isoformat(),
                        "produto": produto_transf,
                        "quantidade": float(quantidade_transf),
                        "origem": "MATRIZ",
                        "destino": base_faltas_atual,
                        "responsavel_envio": responsavel_envio,
                        "responsavel_recebimento": responsavel_recebimento,
                        "status": "Recebido",
                        "observacoes": obs_transf
                    }])
                    df_bases_transferencias = pd.concat([df_bases_transferencias, nova_transferencia], ignore_index=True)
                    df_bases_transferencias.to_excel(BASES_TRANSFERENCIAS_XLSX, index=False)
                    st.success("Transferência registrada. A Matriz foi baixada e a Base recebeu a entrada.")
                    st.rerun()

        st.subheader("Histórico De Transferências")
        hist_transferencias = df_bases_transferencias[
            (df_bases_transferencias["destino"].astype(str) == base_faltas_atual)
            | (df_bases_transferencias["origem"].astype(str) == base_faltas_atual)
        ].copy()
        st.dataframe(formatar_colunas_tabela(hist_transferencias), use_container_width=True, hide_index=True)

    elif subtela_faltas == "RELATÓRIOS":
        with st.expander("Filtros", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            data_ini = f1.date_input("Data inicial", value=datetime.now().date().replace(day=1), key="faltas_data_ini")
            data_fim = f2.date_input("Data final", value=datetime.now().date(), key="faltas_data_fim")
            colaborador_filtro = f3.selectbox("Colaborador", ["Todos"] + colaboradores)
            status_filtro = f4.selectbox("Presença", ["Todos"] + presenca_opcoes)

        df_rel_faltas = faltas_base.copy()
        df_rel_faltas = df_rel_faltas[
            (df_rel_faltas["data_dt"] >= pd.to_datetime(data_ini))
            & (df_rel_faltas["data_dt"] <= pd.to_datetime(data_fim))
        ]
        if colaborador_filtro != "Todos":
            df_rel_faltas = df_rel_faltas[df_rel_faltas["colaborador"] == colaborador_filtro]
        if status_filtro != "Todos":
            df_rel_faltas = df_rel_faltas[df_rel_faltas["presenca"].astype(str).str.upper() == status_filtro]

        resumo_colaborador = pd.DataFrame(columns=[
            "colaborador", "funcao", "presencas", "faltas", "falta_meio_periodo",
            "atestados", "folgas", "ferias", "feriados", "dias_considerados",
            "almoco_na_base", "nao_almocou_na_base"
        ])
        if not df_rel_faltas.empty:
            df_rel_faltas["presenca_normalizada"] = df_rel_faltas["presenca"].astype(str).str.upper()
            df_rel_faltas["almoco_normalizado"] = df_rel_faltas["almocou_base"].astype(str).str.upper()
            resumo_colaborador = df_rel_faltas.groupby(["colaborador", "funcao"], as_index=False).agg(
                presencas=("presenca_normalizada", lambda s: (s == "PRESENTE").sum()),
                faltas=("presenca", lambda s: (s.astype(str).str.upper() == "FALTOU").sum()),
                falta_meio_periodo=("presenca", lambda s: (s.astype(str).str.upper() == "FALTA MEIO PERIODO").sum()),
                atestados=("presenca", lambda s: (s.astype(str).str.upper() == "ATESTADO").sum()),
                folgas=("presenca", lambda s: (s.astype(str).str.upper() == "FOLGA").sum()),
                ferias=("presenca", lambda s: (s.astype(str).str.upper() == "FÉRIAS").sum()),
                feriados=("presenca", lambda s: (s.astype(str).str.upper() == "FERIADO").sum()),
                dias_considerados=("presenca", "count"),
                almoco_na_base=("almocou_base", lambda s: (s.astype(str).str.upper() == "SIM").sum())
            )
            resumo_colaborador["nao_almocou_na_base"] = (
                resumo_colaborador["dias_considerados"] - resumo_colaborador["almoco_na_base"]
            ).clip(lower=0)

        total_medicao = {
            "presencas": int(resumo_colaborador["presencas"].sum()) if not resumo_colaborador.empty else 0,
            "faltas": int(resumo_colaborador["faltas"].sum()) if not resumo_colaborador.empty else 0,
            "falta_meio_periodo": int(resumo_colaborador["falta_meio_periodo"].sum()) if not resumo_colaborador.empty else 0,
            "atestados": int(resumo_colaborador["atestados"].sum()) if not resumo_colaborador.empty else 0,
            "folgas": int(resumo_colaborador["folgas"].sum()) if not resumo_colaborador.empty else 0,
            "ferias": int(resumo_colaborador["ferias"].sum()) if not resumo_colaborador.empty else 0,
            "feriados": int(resumo_colaborador["feriados"].sum()) if not resumo_colaborador.empty else 0,
            "dias_considerados": int(resumo_colaborador["dias_considerados"].sum()) if not resumo_colaborador.empty else 0,
            "almoco_na_base": int(resumo_colaborador["almoco_na_base"].sum()) if not resumo_colaborador.empty else 0
        }
        total_medicao["nao_almocou_na_base"] = max(total_medicao["dias_considerados"] - total_medicao["almoco_na_base"], 0)

        resumo_geral_medicao = pd.DataFrame([{
            "periodo": f"{data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
            "colaboradores": int(resumo_colaborador["colaborador"].nunique()) if not resumo_colaborador.empty else 0,
            **total_medicao
        }])

        resumo_funcao_medicao = pd.DataFrame(columns=[
            "funcao", "presencas", "faltas", "falta_meio_periodo",
            "atestados", "folgas", "ferias", "feriados", "dias_considerados",
            "almoco_na_base", "nao_almocou_na_base"
        ])
        if not resumo_colaborador.empty:
            resumo_funcao_medicao = resumo_colaborador.groupby("funcao", as_index=False)[[
                "presencas", "faltas", "falta_meio_periodo", "atestados",
                "folgas", "ferias", "feriados", "dias_considerados",
                "almoco_na_base", "nao_almocou_na_base"
            ]].sum()

        st.subheader("Medição Mensal")
        med1, med2, med3, med4, med5, med6 = st.columns(6)
        med1.markdown(f"<div class='metric-card'><div class='metric-label'>Presenças</div><div class='metric-value' style='color:#22c55e'>{total_medicao['presencas']}</div></div>", unsafe_allow_html=True)
        med2.markdown(f"<div class='metric-card'><div class='metric-label'>Faltas</div><div class='metric-value' style='color:#ef4444'>{total_medicao['faltas']}</div></div>", unsafe_allow_html=True)
        med3.markdown(f"<div class='metric-card'><div class='metric-label'>Atestados</div><div class='metric-value' style='color:#facc15'>{total_medicao['atestados']}</div></div>", unsafe_allow_html=True)
        med4.markdown(f"<div class='metric-card'><div class='metric-label'>Almoços Na Base</div><div class='metric-value' style='color:#38bdf8'>{total_medicao['almoco_na_base']}</div></div>", unsafe_allow_html=True)
        med5.markdown(f"<div class='metric-card'><div class='metric-label'>Não Almoçou</div><div class='metric-value' style='color:#f97316'>{total_medicao['nao_almocou_na_base']}</div></div>", unsafe_allow_html=True)
        med6.markdown(f"<div class='metric-card'><div class='metric-label'>Dias Considerados</div><div class='metric-value'>{total_medicao['dias_considerados']}</div></div>", unsafe_allow_html=True)

        st.subheader("Resumo Geral Para Cliente")
        st.dataframe(formatar_colunas_tabela(resumo_geral_medicao), use_container_width=True)

        st.subheader("Resumo Por Função")
        st.dataframe(formatar_colunas_tabela(resumo_funcao_medicao), use_container_width=True)

        st.subheader("Quantitativos por colaborador")
        st.dataframe(formatar_colunas_tabela(resumo_colaborador), use_container_width=True)

        st.subheader("Histórico de frequência")
        historico_faltas_exibir = df_rel_faltas.drop(
            columns=["data_dt", "presenca_normalizada", "almoco_normalizado"] + colunas_escala_ocultas,
            errors="ignore"
        )
        st.dataframe(formatar_colunas_tabela(historico_faltas_exibir), use_container_width=True)

        buffer_faltas = io.BytesIO()
        with pd.ExcelWriter(buffer_faltas, engine="openpyxl") as writer:
            resumo_geral_medicao.to_excel(writer, sheet_name="Resumo Geral", index=False)
            resumo_funcao_medicao.to_excel(writer, sheet_name="Resumo Por Funcao", index=False)
            resumo_colaborador.to_excel(writer, sheet_name="Por Colaborador", index=False)
            historico_faltas_exibir.to_excel(writer, sheet_name="Historico", index=False)
        buffer_faltas.seek(0)
        st.download_button(
            "Exportar Excel",
            data=buffer_faltas,
            file_name="controle_de_faltas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    elif subtela_faltas in ["DESPESAS DE FROTA", "DESPESAS FROTA", "DESPESAS FROTAS"]:
        if not supervisor_base_mode and st.button("Voltar", use_container_width=True, key="voltar_base_despesas"):
            st.session_state["subtela_faltas"] = ""
            st.rerun()
        if usuario_pode_lancar_despesa_frota(usuario_logado):
            tela_responsavel_frota()
        else:
            st.error("Você não tem permissão para lançar despesas de frota.")


# =========================
# RELATORIOS
# =========================
elif menu == "RELATÓRIOS":
    st.title("RELATÓRIOS")

    top1, top2, top3, top4 = st.columns([1, 1, 1, 6])

    with st.expander("Filtros", expanded=True):
        f1, f2, f3, f4, f5 = st.columns(5)
        periodo = f1.selectbox("Período", ["7 dias", "30 dias", "Personalizado"], index=1)
        tipo_relatorio = f2.selectbox("Tipo", ["Por cliente", "Por produto"])
        categoria_rel = f3.selectbox("Categoria", ["Todas"] + list(df_produtos["categoria"].dropna().unique()))
        produto_rel = f4.selectbox("Produto", ["Todos"] + list(df_produtos["produto"].dropna().unique()))
        clientes_rel_lista = list(dict.fromkeys(
            df_clientes["nome_cliente"].dropna().astype(str).tolist()
            + df_mov["cliente"].dropna().astype(str).tolist()
        ))
        clientes_rel_lista = [c for c in clientes_rel_lista if c.strip()]
        cliente_rel = f5.selectbox("Cliente", ["Todos"] + clientes_rel_lista)

        data_ini_rel, data_fim_rel = None, None
        if periodo == "Personalizado":
            d1, d2 = st.columns(2)
            data_ini_rel = d1.date_input("Data inicial")
            data_fim_rel = d2.date_input("Data final")

        filtrar = st.button("Filtrar")

    df_rel = filtrar_movimentacoes(df_mov, periodo, "Todos", categoria_rel, produto_rel, data_ini_rel, data_fim_rel)
    if cliente_rel != "Todos":
        df_rel = df_rel[df_rel["cliente"].fillna("").astype(str) == cliente_rel]
    df_criticos = df_produtos[df_produtos["estoque_atual"] <= df_produtos["estoque_minimo"]].copy()
    produtos_rel = df_produtos.copy()
    if categoria_rel != "Todas":
        produtos_rel = produtos_rel[produtos_rel["categoria"] == categoria_rel]
    if produto_rel != "Todos":
        produtos_rel = produtos_rel[produtos_rel["produto"] == produto_rel]
    df_menos_mov = calcular_menos_movimentados(df_rel, produtos_rel)
    df_gastos_clientes, df_gastos_detalhe = calcular_gastos_clientes(df_rel)
    df_top_produtos_saidas = produtos_mais_saidas(df_rel)
    metricas = {
        "total_produtos": int(len(df_produtos)),
        "entradas": int(df_rel[df_rel["tipo"] == "Entrada"]["quantidade"].sum()) if not df_rel.empty else 0,
        "saidas": int(df_rel[df_rel["tipo"] == "Saída"]["quantidade"].sum()) if not df_rel.empty else 0,
        "criticos": int(len(df_criticos)),
        "gasto_clientes": float(df_gastos_clientes["total"].sum()) if not df_gastos_clientes.empty else 0
    }

    with top1:
        st.download_button("PDF", data=gerar_pdf_relatorios(df_rel, df_criticos, df_menos_mov, df_gastos_clientes, df_gastos_detalhe, metricas), file_name="relatorios_estoque.pdf", mime="application/pdf", use_container_width=True)
    with top2:
        st.download_button("Excel", data=gerar_excel_relatorios(df_rel, df_criticos, df_menos_mov, df_gastos_clientes, df_gastos_detalhe, metricas), file_name="relatorios_estoque.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with top3:
        if filtrar:
            st.success("Filtros aplicados")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f"<div class='metric-card'><div class='metric-label'>Total de produtos</div><div class='metric-value'>{metricas['total_produtos']}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-label'>Entradas</div><div class='metric-value' style='color:#22c55e'>{metricas['entradas']}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-label'>Saídas</div><div class='metric-value' style='color:#ef4444'>{metricas['saidas']}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-label'>Itens críticos</div><div class='metric-value' style='color:#facc15'>{metricas['criticos']}</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='metric-card'><div class='metric-label'>Gasto clientes</div><div class='metric-value' style='color:#22c55e'>R$ {metricas['gasto_clientes']:,.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Entradas x Saídas")
        barras = pd.DataFrame({
            "Tipo": ["Entrada", "Saída"],
            "Quantidade": [metricas["entradas"], metricas["saidas"]]
        })
        if px:
            fig_barras = px.bar(
                barras,
                x="Tipo",
                y="Quantidade",
                color="Tipo",
                color_discrete_map={"Entrada": "#22C55E", "Saída": "#EF4444"},
                text="Quantidade",
            )
            fig_barras.update_traces(textposition="outside", marker_line_width=0)
            st.plotly_chart(plotly_layout(fig_barras), use_container_width=True)
        else:
            st.bar_chart(barras.set_index("Tipo"))

    with g2:
        st.subheader("Categorias")
        if not df_produtos.empty:
            categorias_pizza = df_produtos["categoria"].value_counts()
            if px:
                categorias_df = categorias_pizza.reset_index()
                categorias_df.columns = ["Categoria", "Total"]
                fig_pizza = px.donut(
                    categorias_df,
                    values="Total",
                    names="Categoria",
                    hole=.58,
                    color_discrete_sequence=["#0B1F3A", "#F97316", "#22C55E", "#2563EB", "#FACC15", "#EF4444"],
                )
                fig_pizza.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(plotly_layout(fig_pizza), use_container_width=True)
            else:
                try:
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots()
                    ax.pie(categorias_pizza.values, labels=categorias_pizza.index, autopct="%1.1f%%", startangle=90)
                    ax.axis("equal")
                    st.pyplot(fig)
                except Exception:
                    st.dataframe(categorias_pizza.rename("Total"), use_container_width=True)
        else:
            st.info("Sem produtos cadastrados.")

    st.subheader("Total Gasto Por Cliente")
    if not df_gastos_clientes.empty:
        df_total_cliente = df_gastos_clientes.copy()
        df_total_cliente["total"] = df_total_cliente["total"].map(lambda v: f"R$ {v:,.2f}")
        st.dataframe(formatar_colunas_tabela(df_total_cliente), use_container_width=True)
    else:
        st.info("Sem gastos por cliente no período selecionado.")

    r1, r2 = st.columns(2)
    with r1:
        st.subheader("Top 5 Clientes Que Mais Gastam")
        if not df_gastos_clientes.empty:
            top_clientes_mais_grafico = df_gastos_clientes.sort_values("total", ascending=False).head(5).copy()
            top_clientes_mais = top_clientes_mais_grafico.copy()
            top_clientes_mais["total"] = top_clientes_mais["total"].map(lambda v: f"R$ {v:,.2f}")
            st.dataframe(formatar_colunas_tabela(top_clientes_mais), use_container_width=True, hide_index=True)
            if px:
                fig_clientes_mais = px.bar(
                    top_clientes_mais_grafico,
                    x="total",
                    y="cliente",
                    orientation="h",
                    color_discrete_sequence=["#F97316"],
                    text="total",
                )
                fig_clientes_mais.update_traces(texttemplate="R$ %{x:,.2f}", textposition="outside")
                st.plotly_chart(plotly_layout(fig_clientes_mais, 330), use_container_width=True)
            else:
                st.bar_chart(top_clientes_mais_grafico.set_index("cliente")[["total"]])
        else:
            st.info("Sem dados de clientes.")

    with r2:
        st.subheader("Top 5 Clientes Que Menos Gastam")
        if not df_gastos_clientes.empty:
            top_clientes_menos_grafico = df_gastos_clientes.sort_values("total", ascending=True).head(5).copy()
            top_clientes_menos = top_clientes_menos_grafico.copy()
            top_clientes_menos["total"] = top_clientes_menos["total"].map(lambda v: f"R$ {v:,.2f}")
            st.dataframe(formatar_colunas_tabela(top_clientes_menos), use_container_width=True, hide_index=True)
            if px:
                fig_clientes_menos = px.bar(
                    top_clientes_menos_grafico,
                    x="total",
                    y="cliente",
                    orientation="h",
                    color_discrete_sequence=["#0B1F3A"],
                    text="total",
                )
                fig_clientes_menos.update_traces(texttemplate="R$ %{x:,.2f}", textposition="outside")
                st.plotly_chart(plotly_layout(fig_clientes_menos, 330), use_container_width=True)
            else:
                st.bar_chart(top_clientes_menos_grafico.set_index("cliente")[["total"]])
        else:
            st.info("Sem dados de clientes.")

    st.subheader("Top 5 Produtos Com Mais Saídas")
    if not df_top_produtos_saidas.empty:
        st.dataframe(formatar_colunas_tabela(df_top_produtos_saidas.head(5)), use_container_width=True, hide_index=True)
    else:
        st.info("Sem saídas de produtos no período selecionado.")

    if tipo_relatorio == "Por cliente":
        st.subheader("Produtos por cliente")
        if not df_gastos_detalhe.empty:
            df_gastos_detalhe_exibir = df_gastos_detalhe.copy()
            df_gastos_detalhe_exibir["valor_unitario"] = df_gastos_detalhe_exibir["valor_unitario"].map(lambda v: f"R$ {v:,.2f}")
            df_gastos_detalhe_exibir["total"] = df_gastos_detalhe_exibir["total"].map(lambda v: f"R$ {v:,.2f}")
            st.dataframe(formatar_colunas_tabela(df_gastos_detalhe_exibir), use_container_width=True)
        else:
            st.info("Sem produtos consumidos por cliente no período selecionado.")

    elif tipo_relatorio == "Por produto":
        st.subheader("Produtos mais movimentados")
        if not df_rel.empty:
            mais_mov = df_rel.groupby("produto")["quantidade"].sum().reset_index().sort_values("quantidade", ascending=False)
            st.dataframe(formatar_colunas_tabela(mais_mov), use_container_width=True)
        else:
            st.info("Sem movimentações no período selecionado.")

        st.subheader("Produtos menos movimentados")
        st.dataframe(formatar_colunas_tabela(df_menos_mov), use_container_width=True)

    st.subheader("Histórico")
    hist_rel = df_rel.copy()
    if not hist_rel.empty:
        hist_rel["data"] = pd.to_datetime(hist_rel["data"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(formatar_colunas_tabela(hist_rel), use_container_width=True)


# =========================
# FROTAS
# =========================
elif menu == "FROTAS":
    st.title("FROTAS")

    if "subtela_frotas" not in st.session_state:
        st.session_state["subtela_frotas"] = "PAINEL"

    subtela_frotas = st.session_state["subtela_frotas"]
    placas_ativas = df_frotas_veiculos[df_frotas_veiculos["status"] != "Inativo"]["placa"].dropna().astype(str).tolist()
    placas_ativas = [p for p in placas_ativas if p.strip()]
    alertas_preventiva = alertas_manutencao_preventiva(df_frotas_manutencoes)
    assinatura_alerta_frotas = assinatura_alertas_preventiva(alertas_preventiva)
    alertas_vistorias = alertas_vistorias_veiculos(df_frotas_veiculos)
    assinatura_alerta_vistorias = assinatura_alertas_vistorias(alertas_vistorias)

    if not alertas_preventiva.empty and st.session_state.get("alerta_preventiva_ok") != assinatura_alerta_frotas:
        preventivas_vencidas = alertas_preventiva[alertas_preventiva["status"] == "Vencida"]
        preventivas_vencendo = alertas_preventiva[alertas_preventiva["status"] != "Vencida"]
        if not preventivas_vencidas.empty:
            placas_vencidas = ", ".join(preventivas_vencidas["placa"].astype(str).tolist())
            st.error(f"Manutenção preventiva vencida: {placas_vencidas}. Registrar execução da preventiva para encerrar o alerta.")
            st.dataframe(formatar_colunas_tabela(preventivas_vencidas), use_container_width=True, hide_index=True)
        if not preventivas_vencendo.empty:
            placas_vencendo = ", ".join(preventivas_vencendo["placa"].astype(str).tolist())
            st.warning(f"Manutenção preventiva vencendo em até 10 dias: {placas_vencendo}.")
            st.dataframe(formatar_colunas_tabela(preventivas_vencendo), use_container_width=True, hide_index=True)

    if not alertas_vistorias.empty and st.session_state.get("alerta_vistorias_ok") != assinatura_alerta_vistorias:
        vistorias_vencidas = alertas_vistorias[alertas_vistorias["status"] == "Vencida"]
        vistorias_vencendo = alertas_vistorias[alertas_vistorias["status"] != "Vencida"]
        if not vistorias_vencidas.empty:
            st.error("Existem vistorias de veículos vencidas. Registre uma nova vistoria para encerrar o alerta.")
            st.dataframe(formatar_colunas_tabela(vistorias_vencidas), use_container_width=True, hide_index=True)
        if not vistorias_vencendo.empty:
            st.warning("Existem vistorias vencendo em até 10 dias.")
            st.dataframe(formatar_colunas_tabela(vistorias_vencendo), use_container_width=True, hide_index=True)
        if st.button("OK, Entendi As Vistorias Pendentes", key="ok_alerta_vistorias"):
            st.session_state["alerta_vistorias_ok"] = assinatura_alerta_vistorias
            st.rerun()

    if subtela_frotas == "PAINEL":
        hoje = datetime.now().date()
        documentos_temp = df_frotas_documentos.copy()
        documentos_temp["vencimento_dt"] = pd.to_datetime(documentos_temp["vencimento"], errors="coerce").dt.date
        documentos_vencendo = int(((pd.to_datetime(documentos_temp["vencimento_dt"], errors="coerce") >= pd.to_datetime(hoje)) & (pd.to_datetime(documentos_temp["vencimento_dt"], errors="coerce") <= pd.to_datetime(hoje + timedelta(days=30)))).sum()) if not documentos_temp.empty else 0
        documentos_vencidos = int((pd.to_datetime(documentos_temp["vencimento_dt"], errors="coerce") < pd.to_datetime(hoje)).sum()) if not documentos_temp.empty else 0
        gasto_abastecimento = float(df_frotas_abastecimentos["valor_total"].sum()) if not df_frotas_abastecimentos.empty else 0
        gasto_manutencao = float(df_frotas_manutencoes["valor"].sum()) if not df_frotas_manutencoes.empty else 0

        total_vistorias_alerta = len(alertas_vistorias)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.markdown(f"<div class='metric-card'><div class='metric-label'>Veículos</div><div class='metric-value'>{len(df_frotas_veiculos)}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-label'>Ativos</div><div class='metric-value' style='color:#22c55e'>{len(placas_ativas)}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-label'>Documentos Vencidos</div><div class='metric-value' style='color:#ef4444'>{documentos_vencidos}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><div class='metric-label'>Vencendo 30 Dias</div><div class='metric-value' style='color:#facc15'>{documentos_vencendo}</div></div>", unsafe_allow_html=True)
        c5.markdown(f"<div class='metric-card'><div class='metric-label'>Vistorias Pendentes</div><div class='metric-value' style='color:#f59e0b'>{total_vistorias_alerta}</div></div>", unsafe_allow_html=True)
        c6.markdown(f"<div class='metric-card'><div class='metric-label'>Gasto Total</div><div class='metric-value' style='color:#38bdf8'>R$ {gasto_abastecimento + gasto_manutencao:,.2f}</div></div>", unsafe_allow_html=True)

        st.subheader("Veículos Cadastrados")
        st.dataframe(formatar_colunas_tabela(df_frotas_veiculos), use_container_width=True, hide_index=True)

    elif subtela_frotas == "VEÍCULOS":
        st.subheader("Veículos")
        acao_veiculo = st.radio(
            "Ação",
            ["Adicionar", "Editar", "Inativar"],
            horizontal=True,
            label_visibility="collapsed"
        )
        if acao_veiculo == "Adicionar":
            placa = st.text_input("Placa").strip().upper()
            modelo = st.text_input("Modelo").strip().title()
            marca = st.text_input("Marca").strip().title()
            ano = st.number_input("Ano", min_value=1900, max_value=2100, value=datetime.now().year)
            tipo = st.selectbox("Tipo", ["Carro", "Moto", "Caminhão", "Van", "Utilitário", "Outro"])
            responsavel = st.text_input("Responsável").strip().title()
            cidade_local = st.text_input("Cidade / Local").strip().title()
            km_atual = st.text_input("Km Atual").strip()
            periodicidade_vistoria = st.selectbox("Periodicidade Da Vistoria", ["Semanal", "Quinzenal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"], index=2)
            if st.button("ADICIONAR VEÍCULO"):
                if not placa:
                    st.error("Informe a placa.")
                elif placa in df_frotas_veiculos["placa"].astype(str).tolist():
                    st.error("Já existe veículo com esta placa.")
                else:
                    novo = pd.DataFrame([{
                        "placa": placa,
                        "modelo": modelo,
                        "marca": marca,
                        "ano": int(ano),
                        "tipo": tipo,
                        "responsavel": responsavel,
                        "cidade_local": cidade_local,
                        "status": "Ativo",
                        "km_atual": km_atual,
                        "periodicidade_vistoria": periodicidade_vistoria,
                        "ultima_vistoria": "",
                        "proxima_vistoria": "",
                        "status_responsabilidade": "Em Uso" if responsavel else "Disponível"
                    }])
                    df_frotas_veiculos = pd.concat([df_frotas_veiculos, novo], ignore_index=True)
                    df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                    st.success("Veículo adicionado.")
                    st.rerun()
        elif acao_veiculo == "Editar":
            if df_frotas_veiculos.empty:
                st.info("Nenhum veículo cadastrado.")
            else:
                placa_sel = st.selectbox("Veículo", df_frotas_veiculos["placa"].astype(str).tolist())
                dados = df_frotas_veiculos[df_frotas_veiculos["placa"].astype(str) == placa_sel].iloc[0]
                modelo = st.text_input("Modelo", str(dados.get("modelo", ""))).strip().title()
                marca = st.text_input("Marca", str(dados.get("marca", ""))).strip().title()
                ano = st.number_input("Ano", min_value=1900, max_value=2100, value=int(dados.get("ano", datetime.now().year)) if str(dados.get("ano", "")).isdigit() else datetime.now().year)
                tipo = st.text_input("Tipo", str(dados.get("tipo", ""))).strip().title()
                responsavel = st.text_input("Responsável", str(dados.get("responsavel", ""))).strip().title()
                cidade_local = st.text_input("Cidade / Local", str(dados.get("cidade_local", ""))).strip().title()
                status = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if str(dados.get("status", "Ativo")) != "Inativo" else 1)
                km_atual = st.text_input("Km Atual", str(dados.get("km_atual", ""))).strip()
                opcoes_periodicidade = ["Semanal", "Quinzenal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"]
                periodicidade_atual = str(dados.get("periodicidade_vistoria", "Mensal")).strip().title()
                periodicidade_vistoria = st.selectbox(
                    "Periodicidade Da Vistoria",
                    opcoes_periodicidade,
                    index=opcoes_periodicidade.index(periodicidade_atual) if periodicidade_atual in opcoes_periodicidade else 2
                )
                proxima_vistoria_atual = pd.to_datetime(dados.get("proxima_vistoria", ""), errors="coerce")
                proxima_vistoria = st.date_input(
                    "Próxima Vistoria",
                    value=proxima_vistoria_atual.date() if not pd.isna(proxima_vistoria_atual) else datetime.now().date() + timedelta(days=dias_periodicidade_vistoria(periodicidade_vistoria))
                )
                status_responsabilidade = st.selectbox(
                    "Status Da Responsabilidade",
                    ["Disponível", "Em Uso"],
                    index=1 if str(dados.get("status_responsabilidade", "Disponível")) == "Em Uso" else 0
                )
                if st.button("SALVAR VEÍCULO"):
                    linha = df_frotas_veiculos["placa"].astype(str) == placa_sel
                    df_frotas_veiculos.loc[linha, ["modelo", "marca", "ano", "tipo", "responsavel", "cidade_local", "status", "km_atual", "periodicidade_vistoria", "proxima_vistoria", "status_responsabilidade"]] = [modelo, marca, int(ano), tipo, responsavel, cidade_local, status, km_atual, periodicidade_vistoria, proxima_vistoria.isoformat(), status_responsabilidade]
                    df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                    st.success("Veículo atualizado.")
                    st.rerun()
        else:
            if placas_ativas:
                placa_inativar = st.selectbox("Veículo Para Inativar", placas_ativas)
                if st.button("INATIVAR VEÍCULO"):
                    df_frotas_veiculos.loc[df_frotas_veiculos["placa"].astype(str) == placa_inativar, "status"] = "Inativo"
                    df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                    st.success("Veículo inativado.")
                    st.rerun()
            else:
                st.info("Nenhum veículo ativo.")
        st.dataframe(formatar_colunas_tabela(df_frotas_veiculos), use_container_width=True, hide_index=True)

    elif subtela_frotas == "ENTREGA DE VEÍCULO":
        st.subheader("Entrega De Veículo")
        if not placas_ativas:
            st.info("Cadastre um veículo ativo antes de registrar entrega.")
        else:
            opcoes_checklist_vistoria = ["OK", "Atenção", "Irregular", "Não Se Aplica"]
            opcoes_periodicidade = ["Semanal", "Quinzenal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"]
            placa = st.selectbox("Veículo", placas_ativas, key="entrega_veiculo_placa")
            veiculo_entrega = df_frotas_veiculos[df_frotas_veiculos["placa"].astype(str) == str(placa)]
            dados_veiculo_entrega = veiculo_entrega.iloc[0] if not veiculo_entrega.empty else {}
            responsaveis = colaboradores_ativos_para_responsavel()
            responsavel_padrao = str(dados_veiculo_entrega.get("responsavel", "")).strip().title() if hasattr(dados_veiculo_entrega, "get") else ""
            if responsaveis:
                opcoes_responsavel = ["Informar Manualmente"] + responsaveis
                indice_responsavel = opcoes_responsavel.index(responsavel_padrao) if responsavel_padrao in opcoes_responsavel else 0
                responsavel_opcao = st.selectbox("Responsável Pelo Veículo", opcoes_responsavel, index=indice_responsavel)
                responsavel = responsavel_opcao if responsavel_opcao != "Informar Manualmente" else st.text_input("Nome Do Responsável").strip().title()
            else:
                responsavel = st.text_input("Responsável Pelo Veículo", value=responsavel_padrao).strip().title()
            data_entrega = st.date_input("Data Da Entrega", value=datetime.now().date(), key="entrega_data")
            km_entrega = st.number_input("Km Da Entrega", min_value=0, value=0, key="entrega_km")
            periodicidade_atual = str(dados_veiculo_entrega.get("periodicidade_vistoria", "Mensal")).strip().title() if hasattr(dados_veiculo_entrega, "get") else "Mensal"
            periodicidade = st.selectbox(
                "Periodicidade Da Vistoria",
                opcoes_periodicidade,
                index=opcoes_periodicidade.index(periodicidade_atual) if periodicidade_atual in opcoes_periodicidade else 2,
                key="entrega_periodicidade"
            )
            col_v1, col_v2, col_v3 = st.columns(3)
            pneus = col_v1.selectbox("Pneus", opcoes_checklist_vistoria, key="entrega_pneus")
            lataria = col_v2.selectbox("Lataria", opcoes_checklist_vistoria, key="entrega_lataria")
            vidros = col_v3.selectbox("Vidros", opcoes_checklist_vistoria, key="entrega_vidros")
            col_v4, col_v5, col_v6 = st.columns(3)
            farois_lanternas = col_v4.selectbox("Faróis E Lanternas", opcoes_checklist_vistoria, key="entrega_farois")
            documentacao = col_v5.selectbox("Documentação", opcoes_checklist_vistoria, key="entrega_documentacao")
            itens_obrigatorios = col_v6.selectbox("Itens Obrigatórios", opcoes_checklist_vistoria, key="entrega_itens")
            fotos = st.file_uploader(
                "Fotos Da Entrega E Vistoria",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="entrega_fotos"
            )
            observacoes = st.text_area("Observações", key="entrega_observacoes")

            if st.button("SALVAR ENTREGA DE VEÍCULO", use_container_width=True):
                if not responsavel:
                    st.error("Informe o responsável pelo veículo.")
                elif km_entrega <= 0:
                    st.error("Informe o km da entrega.")
                elif not fotos:
                    st.error("Anexe pelo menos uma foto da entrega/vistoria.")
                else:
                    proxima_vistoria = calcular_proxima_vistoria(data_entrega, periodicidade)
                    caminhos_fotos = salvar_anexos_frota(fotos, placa, "entrega_vistoria")
                    registro_entrega = {
                        "data": data_entrega.isoformat(),
                        "placa": placa,
                        "responsavel": responsavel,
                        "km": int(km_entrega),
                        "periodicidade": periodicidade,
                        "proxima_vistoria": proxima_vistoria,
                        "pneus": pneus,
                        "lataria": lataria,
                        "vidros": vidros,
                        "farois_lanternas": farois_lanternas,
                        "documentacao": documentacao,
                        "itens_obrigatorios": itens_obrigatorios,
                        "fotos": caminhos_fotos,
                        "observacoes": observacoes.strip(),
                        "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }
                    df_frotas_entregas = pd.concat([df_frotas_entregas, pd.DataFrame([registro_entrega])], ignore_index=True)
                    df_frotas_entregas.to_excel(FROTAS_ENTREGAS_XLSX, index=False)
                    registro_vistoria = dict(registro_entrega)
                    registro_vistoria["tipo_vistoria"] = "Entrega"
                    df_frotas_vistorias = pd.concat([df_frotas_vistorias, pd.DataFrame([registro_vistoria])], ignore_index=True)
                    df_frotas_vistorias.to_excel(FROTAS_VISTORIAS_XLSX, index=False)
                    linha = df_frotas_veiculos["placa"].astype(str) == placa
                    df_frotas_veiculos.loc[linha, ["responsavel", "km_atual", "periodicidade_vistoria", "ultima_vistoria", "proxima_vistoria", "status_responsabilidade"]] = [responsavel, int(km_entrega), periodicidade, data_entrega.isoformat(), proxima_vistoria, "Em Uso"]
                    df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                    st.success("Entrega salva e veículo vinculado ao responsável.")
                    st.rerun()

        st.subheader("Histórico De Entregas")
        st.dataframe(formatar_colunas_tabela(df_frotas_entregas), use_container_width=True, hide_index=True)

    elif subtela_frotas == "VISTORIAS":
        st.subheader("Vistorias")
        if not alertas_vistorias.empty:
            st.warning("Vistorias vencidas ou próximas do vencimento.")
            st.dataframe(formatar_colunas_tabela(alertas_vistorias), use_container_width=True, hide_index=True)
        if not placas_ativas:
            st.info("Cadastre um veículo ativo antes de registrar vistoria.")
        else:
            opcoes_checklist_vistoria = ["OK", "Atenção", "Irregular", "Não Se Aplica"]
            opcoes_periodicidade = ["Semanal", "Quinzenal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"]
            placa = st.selectbox("Veículo", placas_ativas, key="vistoria_placa")
            veiculo_vistoria = df_frotas_veiculos[df_frotas_veiculos["placa"].astype(str) == str(placa)]
            dados_veiculo_vistoria = veiculo_vistoria.iloc[0] if not veiculo_vistoria.empty else {}
            responsavel_padrao = str(dados_veiculo_vistoria.get("responsavel", "")).strip().title() if hasattr(dados_veiculo_vistoria, "get") else ""
            data_vistoria = st.date_input("Data Da Vistoria", value=datetime.now().date(), key="vistoria_data")
            tipo_vistoria = st.selectbox("Tipo De Vistoria", ["Periódica", "Devolução", "Avulsa"], key="tipo_vistoria")
            responsavel = st.text_input("Responsável Pelo Veículo", value=responsavel_padrao, key="vistoria_responsavel").strip().title()
            km_vistoria = st.number_input("Km Da Vistoria", min_value=0, value=0, key="vistoria_km")
            periodicidade_atual = str(dados_veiculo_vistoria.get("periodicidade_vistoria", "Mensal")).strip().title() if hasattr(dados_veiculo_vistoria, "get") else "Mensal"
            periodicidade = st.selectbox(
                "Periodicidade Da Vistoria",
                opcoes_periodicidade,
                index=opcoes_periodicidade.index(periodicidade_atual) if periodicidade_atual in opcoes_periodicidade else 2,
                key="vistoria_periodicidade"
            )
            col_v1, col_v2, col_v3 = st.columns(3)
            pneus = col_v1.selectbox("Pneus", opcoes_checklist_vistoria, key="vistoria_pneus")
            lataria = col_v2.selectbox("Lataria", opcoes_checklist_vistoria, key="vistoria_lataria")
            vidros = col_v3.selectbox("Vidros", opcoes_checklist_vistoria, key="vistoria_vidros")
            col_v4, col_v5, col_v6 = st.columns(3)
            farois_lanternas = col_v4.selectbox("Faróis E Lanternas", opcoes_checklist_vistoria, key="vistoria_farois")
            documentacao = col_v5.selectbox("Documentação", opcoes_checklist_vistoria, key="vistoria_documentacao")
            itens_obrigatorios = col_v6.selectbox("Itens Obrigatórios", opcoes_checklist_vistoria, key="vistoria_itens")
            fotos = st.file_uploader(
                "Fotos Da Vistoria",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="vistoria_fotos"
            )
            observacoes = st.text_area("Observações", key="vistoria_observacoes")

            if st.button("SALVAR VISTORIA", use_container_width=True):
                if tipo_vistoria != "Devolução" and not responsavel:
                    st.error("Informe o responsável pelo veículo.")
                elif km_vistoria <= 0:
                    st.error("Informe o km da vistoria.")
                elif not fotos:
                    st.error("Anexe pelo menos uma foto da vistoria.")
                else:
                    proxima_vistoria = calcular_proxima_vistoria(data_vistoria, periodicidade)
                    caminhos_fotos = salvar_anexos_frota(fotos, placa, "vistoria")
                    novo = pd.DataFrame([{
                        "data": data_vistoria.isoformat(),
                        "placa": placa,
                        "tipo_vistoria": tipo_vistoria,
                        "responsavel": responsavel,
                        "km": int(km_vistoria),
                        "periodicidade": periodicidade,
                        "proxima_vistoria": proxima_vistoria,
                        "pneus": pneus,
                        "lataria": lataria,
                        "vidros": vidros,
                        "farois_lanternas": farois_lanternas,
                        "documentacao": documentacao,
                        "itens_obrigatorios": itens_obrigatorios,
                        "fotos": caminhos_fotos,
                        "observacoes": observacoes.strip(),
                        "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
                    }])
                    df_frotas_vistorias = pd.concat([df_frotas_vistorias, novo], ignore_index=True)
                    df_frotas_vistorias.to_excel(FROTAS_VISTORIAS_XLSX, index=False)
                    linha = df_frotas_veiculos["placa"].astype(str) == placa
                    status_responsabilidade = "Disponível" if tipo_vistoria == "Devolução" else "Em Uso"
                    responsavel_atualizado = "" if tipo_vistoria == "Devolução" else responsavel
                    df_frotas_veiculos.loc[linha, ["responsavel", "km_atual", "periodicidade_vistoria", "ultima_vistoria", "proxima_vistoria", "status_responsabilidade"]] = [responsavel_atualizado, int(km_vistoria), periodicidade, data_vistoria.isoformat(), proxima_vistoria, status_responsabilidade]
                    df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                    st.success("Vistoria salva.")
                    st.rerun()

        st.subheader("Histórico De Vistorias")
        st.dataframe(formatar_colunas_tabela(df_frotas_vistorias), use_container_width=True, hide_index=True)

    elif subtela_frotas == "ABASTECIMENTOS":
        st.subheader("Abastecimentos")
        if not placas_ativas:
            st.info("Cadastre um veículo ativo antes de registrar abastecimento.")
        else:
            data = st.date_input("Data", value=datetime.now().date(), key="abastecimento_data")
            placa = st.selectbox("Veículo", placas_ativas, key="abastecimento_placa")
            veiculo_lancamento = df_frotas_veiculos[df_frotas_veiculos["placa"].astype(str) == str(placa)]
            responsavel_padrao = str(veiculo_lancamento.iloc[0].get("responsavel", "")).strip().title() if not veiculo_lancamento.empty else ""
            responsavel_lancamento = st.text_input(
                "Responsável Pelo Lançamento",
                value=responsavel_padrao,
                key=f"abastecimento_responsavel_{placa}"
            ).strip().title()
            km = st.number_input("Km", min_value=0, value=0, key="abastecimento_km")
            combustivel = st.selectbox("Combustível", ["Gasolina", "Etanol", "Diesel", "GNV", "Outro"])
            litros = st.number_input("Litros", min_value=0.0, step=0.01, format="%.2f")
            valor_litro = st.number_input("Valor Por Litro", min_value=0.0, step=0.01, format="%.2f")
            valor_total = litros * valor_litro
            posto = st.text_input("Posto").strip().title()
            observacoes = st.text_area("Observações")
            hodometro_anexo = st.file_uploader(
                "Foto Do Hodômetro",
                type=["png", "jpg", "jpeg", "webp"],
                key="abastecimento_hodometro"
            )
            st.write(f"Valor Total: R$ {valor_total:,.2f}")
            if st.button("SALVAR ABASTECIMENTO"):
                if not responsavel_lancamento:
                    st.error("Informe o responsável pelo lançamento.")
                elif km <= 0:
                    st.error("Informe o km.")
                elif not hodometro_anexo:
                    st.error("Anexe a foto do hodômetro para salvar o abastecimento.")
                else:
                    caminho_hodometro = salvar_anexo_frota(hodometro_anexo, placa, "hodometro_abastecimento")
                    novo = pd.DataFrame([{"data": data.isoformat(), "placa": placa, "km": int(km), "combustivel": combustivel, "litros": float(litros), "valor_litro": float(valor_litro), "valor_total": float(valor_total), "posto": posto, "responsavel_lancamento": responsavel_lancamento, "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "nota_anexo": caminho_hodometro, "status_conferencia": "Pendente", "observacao_administrativo": "", "observacoes": observacoes.strip()}])
                    df_frotas_abastecimentos = pd.concat([df_frotas_abastecimentos, novo], ignore_index=True)
                    df_frotas_abastecimentos.to_excel(FROTAS_ABASTECIMENTOS_XLSX, index=False)
                    df_frotas_veiculos.loc[df_frotas_veiculos["placa"].astype(str) == placa, "km_atual"] = int(km)
                    df_frotas_veiculos.to_excel(FROTAS_VEICULOS_XLSX, index=False)
                    st.success("Abastecimento salvo.")
                    st.rerun()
        exibir_consulta_abastecimentos(df_frotas_abastecimentos)

    elif subtela_frotas == "MANUTENÇÕES":
        st.subheader("Manutenções")
        if not placas_ativas:
            st.info("Cadastre um veículo ativo antes de registrar manutenção.")
        else:
            if "tipo_lancamento_manutencao" not in st.session_state:
                st.session_state["tipo_lancamento_manutencao"] = "Atual"

            botao_atual, botao_programada = st.columns(2)
            if botao_atual.button(
                "MANUTENÇÃO ATUAL",
                type="primary" if st.session_state["tipo_lancamento_manutencao"] == "Atual" else "secondary",
                use_container_width=True
            ):
                st.session_state["tipo_lancamento_manutencao"] = "Atual"
                st.rerun()
            if botao_programada.button(
                "MANUTENÇÃO PROGRAMADA",
                type="primary" if st.session_state["tipo_lancamento_manutencao"] == "Programada" else "secondary",
                use_container_width=True
            ):
                st.session_state["tipo_lancamento_manutencao"] = "Programada"
                st.rerun()

            modo_manutencao = st.session_state["tipo_lancamento_manutencao"]
            placa = st.selectbox("Veículo", placas_ativas, key=f"manutencao_placa_{modo_manutencao}")
            veiculo_lancamento = df_frotas_veiculos[df_frotas_veiculos["placa"].astype(str) == str(placa)]
            responsavel_padrao = str(veiculo_lancamento.iloc[0].get("responsavel", "")).strip().title() if not veiculo_lancamento.empty else ""
            responsavel_lancamento = st.text_input(
                "Responsável Pelo Lançamento",
                value=responsavel_padrao,
                key=f"manutencao_responsavel_{modo_manutencao}_{placa}"
            ).strip().title()
            tipo_manutencao = st.selectbox("Tipo De Manutenção", ["Preventiva", "Corretiva"], key=f"tipo_manutencao_{modo_manutencao}")

            if modo_manutencao == "Atual":
                data = st.date_input("Data", value=datetime.now().date(), key="manutencao_data_atual")
                km = st.number_input("Km", min_value=0, value=0, key="manutencao_km_atual")
                servico_executado = st.text_input("Serviço Executado", key="servico_manutencao_atual").strip().title()
                fornecedor = st.text_input("Fornecedor/Oficina", key="fornecedor_manutencao_atual").strip().title()
                valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f", key="valor_manutencao_atual")
                observacoes = st.text_area("Observações", key="manutencao_obs_atual")
                if st.button("SALVAR MANUTENÇÃO ATUAL"):
                    if not responsavel_lancamento:
                        st.error("Informe o responsável pelo lançamento.")
                    else:
                        if tipo_manutencao == "Preventiva":
                            df_frotas_manutencoes = baixar_manutencoes_programadas(df_frotas_manutencoes, placa, data)
                        novo = pd.DataFrame([{
                            "data": data.isoformat(),
                            "placa": placa,
                            "tipo_manutencao": tipo_manutencao,
                            "km": int(km),
                            "servico_executado": servico_executado,
                            "fornecedor": fornecedor,
                            "valor": float(valor),
                            "manutencao_agendada": "",
                            "proxima_revisao": "",
                            "status_manutencao": "Executada",
                            "responsavel_lancamento": responsavel_lancamento,
                            "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "observacoes": observacoes.strip()
                        }])
                        df_frotas_manutencoes = pd.concat([df_frotas_manutencoes, novo], ignore_index=True)
                        df_frotas_manutencoes.to_excel(FROTAS_MANUTENCOES_XLSX, index=False)
                        st.success("Manutenção atual salva.")
                        st.rerun()
            else:
                manutencao_agendada = st.date_input("Manutenção Agendada", value=datetime.now().date() + timedelta(days=10), key="manutencao_agendada_programada")
                servico_executado = st.text_input("Serviço Programado", key="servico_manutencao_programada").strip().title()
                observacoes = st.text_area("Observações", key="manutencao_obs_programada")
                if st.button("SALVAR MANUTENÇÃO PROGRAMADA"):
                    if not responsavel_lancamento:
                        st.error("Informe o responsável pelo lançamento.")
                    else:
                        novo = pd.DataFrame([{
                            "data": datetime.now().date().isoformat(),
                            "placa": placa,
                            "tipo_manutencao": tipo_manutencao,
                            "km": 0,
                            "servico_executado": servico_executado,
                            "fornecedor": "",
                            "valor": 0.0,
                            "manutencao_agendada": manutencao_agendada.isoformat(),
                            "proxima_revisao": "",
                            "status_manutencao": "Programada",
                            "responsavel_lancamento": responsavel_lancamento,
                            "registrado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "observacoes": observacoes.strip()
                        }])
                        df_frotas_manutencoes = pd.concat([df_frotas_manutencoes, novo], ignore_index=True)
                        df_frotas_manutencoes.to_excel(FROTAS_MANUTENCOES_XLSX, index=False)
                        st.success("Manutenção programada salva.")
                        st.rerun()
        st.dataframe(formatar_colunas_tabela(df_frotas_manutencoes), use_container_width=True, hide_index=True)

    elif subtela_frotas == "CONFERÊNCIA":
        st.subheader("Conferência De Despesas Recebidas")
        pend_abast = int((df_frotas_abastecimentos["status_conferencia"].astype(str) == "Pendente").sum()) if not df_frotas_abastecimentos.empty else 0
        pend_manut = int((df_frotas_manutencoes["status_conferencia"].astype(str) == "Pendente").sum()) if not df_frotas_manutencoes.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-card'><div class='metric-label'>Abastecimentos Pendentes</div><div class='metric-value'>{pend_abast}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-label'>Manutenções Pendentes</div><div class='metric-value'>{pend_manut}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-label'>Total Pendente</div><div class='metric-value'>{pend_abast + pend_manut}</div></div>", unsafe_allow_html=True)

        tab_abastecimentos, tab_manutencoes = st.tabs(["ABASTECIMENTOS", "MANUTENÇÕES"])
        with tab_abastecimentos:
            exibir_conferencia_lancamentos("Abastecimento", df_frotas_abastecimentos, FROTAS_ABASTECIMENTOS_XLSX)
        with tab_manutencoes:
            exibir_conferencia_lancamentos("Manutenção", df_frotas_manutencoes, FROTAS_MANUTENCOES_XLSX)

    elif subtela_frotas == "DOCUMENTOS":
        st.subheader("Documentos")
        if not placas_ativas:
            st.info("Cadastre um veículo ativo antes de registrar documento.")
        else:
            placa = st.selectbox("Veículo", placas_ativas, key="documento_placa")
            documento = st.selectbox("Documento", ["Licenciamento", "Seguro", "IPVA", "Multa", "Outro"])
            vencimento = st.date_input("Vencimento", value=datetime.now().date() + timedelta(days=30))
            valor = st.number_input("Valor", min_value=0.0, step=0.01, format="%.2f", key="documento_valor")
            status = st.selectbox("Status", ["Ativo", "Pago", "Pendente", "Vencido"])
            observacoes = st.text_area("Observações", key="documento_obs")
            if st.button("SALVAR DOCUMENTO"):
                novo = pd.DataFrame([{"placa": placa, "documento": documento, "vencimento": vencimento.isoformat(), "valor": float(valor), "status": status, "observacoes": observacoes.strip()}])
                df_frotas_documentos = pd.concat([df_frotas_documentos, novo], ignore_index=True)
                df_frotas_documentos.to_excel(FROTAS_DOCUMENTOS_XLSX, index=False)
                st.success("Documento salvo.")
                st.rerun()
        st.dataframe(formatar_colunas_tabela(df_frotas_documentos), use_container_width=True, hide_index=True)

    elif subtela_frotas == "RELATÓRIOS":
        st.subheader("Relatórios De Frotas")
        placas_rel = ["Todos"] + sorted(df_frotas_veiculos["placa"].dropna().astype(str).unique().tolist())
        placa_rel = st.selectbox("Veículo", placas_rel)
        abast_rel = df_frotas_abastecimentos.copy()
        manut_rel = df_frotas_manutencoes.copy()
        if placa_rel != "Todos":
            abast_rel = abast_rel[abast_rel["placa"].astype(str) == placa_rel]
            manut_rel = manut_rel[manut_rel["placa"].astype(str) == placa_rel]
        gasto_abast = float(abast_rel["valor_total"].sum()) if not abast_rel.empty else 0
        gasto_manut = float(manut_rel["valor"].sum()) if not manut_rel.empty else 0
        r1, r2, r3 = st.columns(3)
        r1.markdown(f"<div class='metric-card'><div class='metric-label'>Abastecimentos</div><div class='metric-value'>R$ {gasto_abast:,.2f}</div></div>", unsafe_allow_html=True)
        r2.markdown(f"<div class='metric-card'><div class='metric-label'>Manutenções</div><div class='metric-value'>R$ {gasto_manut:,.2f}</div></div>", unsafe_allow_html=True)
        r3.markdown(f"<div class='metric-card'><div class='metric-label'>Total</div><div class='metric-value'>R$ {gasto_abast + gasto_manut:,.2f}</div></div>", unsafe_allow_html=True)
        exibir_consulta_abastecimentos(abast_rel, "Abastecimentos")
        st.subheader("Manutenções")
        st.dataframe(formatar_colunas_tabela(manut_rel), use_container_width=True, hide_index=True)

# =========================
# CONFIGURACOES
# =========================
elif menu == "CONFIGURAÇÕES":
    st.title("CONFIGURAÇÕES")

    st.markdown(
        f"""
        <div class='saas-card'>
            <b>Status do sistema</b><br>
            Sistema online &nbsp;|&nbsp; Backup: {status_backup} &nbsp;|&nbsp; Último backup: {config.get('ultimo_backup', 'Nunca')} &nbsp;|&nbsp; Itens críticos: {total_criticos_sidebar}
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    usuario_atual = st.session_state.get("usuario_logado", {})
    admin_logado = usuario_eh_admin(usuario_atual)

    if admin_logado:
        tab_geral, tab_usuarios, tab_estoque, tab_categorias, tab_unidades, tab_aparencia, tab_backup, tab_auditoria = st.tabs([
            "GERAL", "USUÁRIOS", "ESTOQUE", "CATEGORIAS", "UNIDADE", "APARÊNCIA", "BACKUP", "AUDITORIA"
        ])
    else:
        tab_usuarios, tab_aparencia, tab_backup = st.tabs([
            "USUÁRIOS", "APARÊNCIA", "BACKUP"
        ])

    if admin_logado:
        with tab_geral:
            with st.form("form_geral"):
                empresa = st.text_input("Nome empresa", config.get("empresa", ""))
                email = st.text_input("Email", config.get("email", ""))
                telefone = st.text_input("Telefone", config.get("telefone", ""))
                endereco = st.text_area("Endereço", config.get("endereco", ""))
                logo = st.file_uploader("Logo", type=["png", "jpg", "jpeg"])
                salvar_geral = st.form_submit_button("Salvar")
                if salvar_geral:
                    config.update({
                        "empresa": empresa,
                        "email": email,
                        "telefone": telefone,
                        "endereco": endereco
                    })
                    if logo:
                        nome_logo = "".join(caractere for caractere in os.path.basename(logo.name) if caractere.isalnum() or caractere in "._- ").strip()
                        if ambiente_producao():
                            caminho_logo = f"Imagens Sistema/logo_{nome_logo}"
                            content_type = getattr(logo, "type", None) or mimetypes.guess_type(nome_logo)[0] or "application/octet-stream"
                            if not upload_arquivo_storage(caminho_logo, logo.getbuffer(), content_type):
                                erro = st.session_state.get("ultimo_erro_supabase", "")
                                st.error(f"Erro ao enviar logo para o Supabase Storage. {erro}")
                                st.stop()
                            config["logo"] = caminho_logo
                        else:
                            logo_path = os.path.join(BASE_DIR, f"logo_{nome_logo}")
                            with open(logo_path, "wb") as arquivo:
                                arquivo.write(logo.getbuffer())
                            upload_arquivo_remoto(logo_path) if os.path.abspath(logo_path).startswith(os.path.abspath(DATA_DIR)) else None
                            marcar_backup_pendente(logo_path) if os.path.abspath(logo_path).startswith(os.path.abspath(DATA_DIR)) else None
                            config["logo"] = logo_path
                    salvar_json(CONFIG_JSON, config)
                    st.success("Configurações gerais salvas.")

    with tab_usuarios:
        usuarios = carregar_json(USUARIOS_JSON, [])
        st.write(f"Usuário: {usuario_atual.get('nome', '')}")
        st.write(f"Nível: {usuario_atual.get('nivel', '')}")

        with st.form("alterar_senha_usuario"):
            senha_atual = st.text_input("Senha atual", type="password")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirmar nova senha", type="password")
            if st.form_submit_button("Alterar senha"):
                usuario_encontrado = next(
                    (
                        u for u in usuarios
                        if u.get("nome") == usuario_atual.get("nome")
                        or u.get("email") == usuario_atual.get("email")
                    ),
                    None
                )
                if not usuario_encontrado:
                    st.error("Usuário logado não encontrado.")
                elif not verificar_senha(senha_atual, usuario_encontrado.get("senha")):
                    st.error("Senha atual incorreta.")
                elif not nova_senha:
                    st.error("Informe a nova senha.")
                elif nova_senha != confirmar_senha:
                    st.error("A confirmação da senha não confere.")
                else:
                    usuario_encontrado["senha"] = hash_senha(nova_senha)
                    salvar_json(USUARIOS_JSON, usuarios)
                    st.success("Senha alterada com sucesso.")

        if admin_logado:
            st.divider()
            st.subheader("Gerenciar usuários")
            st.dataframe(pd.DataFrame([{k: v for k, v in u.items() if k != "senha"} for u in usuarios]), use_container_width=True)

            niveis_usuario = [
                "CEO",
                "Administrador",
                "ADM",
                "Almoxarife",
                "Supervisor Base TMG",
                "Motorista",
                "Usuário",
                "Supervisor Base",
                "Responsável Frota",
            ]
            colunas_frotas_usuarios = ["placa", "modelo", "marca", "ano", "tipo", "responsavel", "cidade_local", "status", "km_atual"]
            for coluna_frota in colunas_frotas_usuarios:
                if coluna_frota not in df_frotas_veiculos.columns:
                    df_frotas_veiculos[coluna_frota] = "Ativo" if coluna_frota == "status" else ""
                df_frotas_veiculos[coluna_frota] = df_frotas_veiculos[coluna_frota].astype("object").fillna("")
            df_frotas_veiculos.loc[df_frotas_veiculos["status"].astype(str).str.strip() == "", "status"] = "Ativo"

            veiculos_ativos_usuarios = sorted(
                df_frotas_veiculos[df_frotas_veiculos["status"].astype(str) != "Inativo"]["placa"]
                .dropna()
                .astype(str)
                .tolist()
            )
            responsaveis_frota = sorted(set(
                nome
                for responsavel in df_frotas_veiculos["responsavel"].dropna().astype(str).tolist()
                for nome in nomes_responsaveis_frota(responsavel)
            ))
            acao_usuario = st.radio("Ação", ["Criar", "Editar", "Inativar"], horizontal=True)
            if acao_usuario == "Criar":
                nivel = st.selectbox("Nível", niveis_usuario, key="nivel_criar_usuario")
                bases_permitidas = st.multiselect(
                    "Bases Permitidas",
                    BASES_FREQUENCIA,
                    default=BASES_FREQUENCIA if nivel in ["Administrador", "CEO", "Supervisor Base TMG"] else ["TMG BASE SORRISO"] if nivel == "Supervisor Base" else [],
                    key="bases_criar_usuario"
                )
                pode_lancar_despesa_frota = st.checkbox(
                    "Permitir Lançamento De Despesas De Frota",
                    value=nivel in ["Administrador", "CEO", "Supervisor Base", "Supervisor Base TMG", "Responsável Frota", "Motorista"],
                    key="pode_lancar_frota_criar"
                )
                with st.form("criar_usuario"):
                    if nivel in ["Responsável Frota", "Motorista"]:
                        if responsaveis_frota:
                            opcoes_responsavel_usuario = ["Informar Manualmente"] + responsaveis_frota
                            nome_opcao = st.selectbox("Nome", opcoes_responsavel_usuario)
                            nome = nome_opcao if nome_opcao != "Informar Manualmente" else st.text_input("Nome do usuário").strip().title()
                        else:
                            nome = st.text_input("Nome")
                    else:
                        nome = st.text_input("Nome")
                    email_user = st.text_input("Email")
                    veiculos_frota = []
                    if nivel in ["Responsável Frota", "Motorista"] or pode_lancar_despesa_frota:
                        if nome and "responsavel" in df_frotas_veiculos.columns and "placa" in df_frotas_veiculos.columns:
                            veiculos_sugeridos = df_frotas_veiculos[
                                df_frotas_veiculos["responsavel"].astype(str).apply(
                                    lambda responsavel: str(nome).strip().title() in nomes_responsaveis_frota(responsavel)
                                )
                            ]["placa"].dropna().astype(str).tolist()
                        else:
                            veiculos_sugeridos = []
                        veiculos_frota = st.multiselect(
                            "Veículos Liberados",
                            veiculos_ativos_usuarios,
                            default=[p for p in veiculos_sugeridos if p in veiculos_ativos_usuarios]
                        )
                    senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("Criar usuário"):
                        nome_existe = any(u.get("nome", "").lower() == nome.lower() for u in usuarios)
                        email_existe = bool(email_user) and any(u.get("email", "").lower() == email_user.lower() for u in usuarios)
                        if not nome or not senha:
                            st.error("Informe nome e senha.")
                        elif nome_existe:
                            st.error("Já existe um usuário com esse nome.")
                        elif email_existe:
                            st.error("Já existe um usuário com esse email.")
                        else:
                            usuarios.append({
                                "nome": nome,
                                "email": email_user,
                                "nivel": nivel,
                                "veiculo_frota": veiculos_frota[0] if len(veiculos_frota) == 1 else "",
                                "veiculos_frota": veiculos_frota,
                                "bases_permitidas": BASES_FREQUENCIA if nivel in ["Administrador", "CEO"] else bases_permitidas,
                                "pode_lancar_despesa_frota": bool(pode_lancar_despesa_frota),
                                "senha": hash_senha(senha),
                                "status": "Ativo",
                                "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
                            })
                            salvar_json(USUARIOS_JSON, usuarios)
                            registrar_auditoria("CRIAR", "USUÁRIOS", "Usuário criado", nome)
                            st.success("Usuário criado.")
                            st.rerun()

            elif acao_usuario == "Editar":
                if usuarios:
                    nomes = [u["nome"] for u in usuarios]
                    selecionado = st.selectbox("Usuário", nomes)
                    idx = nomes.index(selecionado)
                    with st.form("editar_usuario"):
                        nome = st.text_input("Nome", usuarios[idx].get("nome", ""))
                        email_user = st.text_input("Email", usuarios[idx].get("email", ""))
                        nivel_atual = usuarios[idx].get("nivel", "Usuário")
                        if nivel_atual not in niveis_usuario:
                            nivel_atual = "Usuário"
                        nivel = st.selectbox("Nível", niveis_usuario, index=niveis_usuario.index(nivel_atual))
                        status_usuario = st.selectbox(
                            "Status",
                            ["Ativo", "Inativo"],
                            index=0 if usuarios[idx].get("status", "Ativo") != "Inativo" else 1
                        )
                        bases_atuais = usuarios[idx].get("bases_permitidas", [])
                        if isinstance(bases_atuais, str):
                            bases_atuais = [bases_atuais] if bases_atuais.strip() else []
                        bases_permitidas = st.multiselect(
                            "Bases Permitidas",
                            BASES_FREQUENCIA,
                            default=BASES_FREQUENCIA if nivel in ["Administrador", "CEO"] else [b for b in bases_atuais if b in BASES_FREQUENCIA]
                        )
                        pode_lancar_despesa_frota = st.checkbox(
                            "Permitir Lançamento De Despesas De Frota",
                            value=bool(usuarios[idx].get("pode_lancar_despesa_frota", False)) or nivel in ["Administrador", "CEO", "Supervisor Base", "Supervisor Base TMG", "Responsável Frota", "Motorista"]
                        )
                        veiculos_atuais = usuarios[idx].get("veiculos_frota", [])
                        if isinstance(veiculos_atuais, str):
                            veiculos_atuais = [veiculos_atuais] if veiculos_atuais.strip() else []
                        veiculo_antigo = usuarios[idx].get("veiculo_frota", "")
                        if veiculo_antigo and veiculo_antigo not in veiculos_atuais:
                            veiculos_atuais.append(veiculo_antigo)
                        veiculos_edicao = sorted(set(veiculos_ativos_usuarios + veiculos_atuais))
                        veiculos_frota = []
                        if nivel in ["Responsável Frota", "Motorista"] or pode_lancar_despesa_frota:
                            veiculos_frota = st.multiselect(
                                "Veículos Liberados",
                                veiculos_edicao,
                                default=[p for p in veiculos_atuais if p in veiculos_edicao]
                            )
                        nova_senha_admin = st.text_input("Nova senha", type="password")
                        if st.form_submit_button("Salvar usuário"):
                            usuarios[idx]["nome"] = nome
                            usuarios[idx]["email"] = email_user
                            usuarios[idx]["nivel"] = nivel
                            usuarios[idx]["status"] = status_usuario
                            usuarios[idx]["veiculo_frota"] = veiculos_frota[0] if len(veiculos_frota) == 1 else ""
                            usuarios[idx]["veiculos_frota"] = veiculos_frota
                            usuarios[idx]["bases_permitidas"] = BASES_FREQUENCIA if nivel in ["Administrador", "CEO"] else bases_permitidas
                            usuarios[idx]["pode_lancar_despesa_frota"] = bool(pode_lancar_despesa_frota)
                            if nova_senha_admin:
                                usuarios[idx]["senha"] = hash_senha(nova_senha_admin)
                            salvar_json(USUARIOS_JSON, usuarios)
                            st.success("Usuário atualizado.")
                            st.rerun()

            elif acao_usuario == "Inativar":
                if usuarios:
                    nomes = [u["nome"] for u in usuarios]
                    selecionado = st.selectbox("Usuário", nomes, key="inativar_usuario")
                    if st.button("Inativar usuário"):
                        usuario = next(u for u in usuarios if u["nome"] == selecionado)
                        admins = [u for u in usuarios if u.get("nivel") in PERFIS_ADMIN]
                        if usuario.get("nivel") in PERFIS_ADMIN and len(admins) <= 1:
                            st.error("Não é permitido inativar o último usuário com acesso total.")
                        else:
                            antes_usuario = dict(usuario)
                            usuario["status"] = "Inativo"
                            salvar_json(USUARIOS_JSON, usuarios)
                            registrar_auditoria("INATIVAR", "USUÁRIOS", "Usuário inativado", selecionado, antes_usuario, usuario)
                            st.success("Usuário inativado.")
                            st.rerun()

    if admin_logado:
        with tab_estoque:
            with st.form("form_estoque"):
                estoque_minimo_padrao = st.number_input("Estoque mínimo padrão", 0, value=int(config.get("estoque_minimo_padrao", 1)))
                alerta_estoque = st.toggle("Alerta de estoque", value=bool(config.get("alerta_estoque", True)))
                permitir_negativo = st.toggle("Permitir negativo", value=bool(config.get("permitir_negativo", False)))
                if st.form_submit_button("Salvar estoque"):
                    config["estoque_minimo_padrao"] = int(estoque_minimo_padrao)
                    config["alerta_estoque"] = bool(alerta_estoque)
                    config["permitir_negativo"] = bool(permitir_negativo)
                    salvar_json(CONFIG_JSON, config)
                    st.success("Configurações de estoque salvas.")

        with tab_categorias:
            st.dataframe(pd.DataFrame(categorias_config), use_container_width=True)
            acao_cat = st.radio("Ação de categoria", ["Adicionar", "Editar", "Inativar"], horizontal=True)

            if acao_cat == "Adicionar":
                nome_cat = st.text_input("Nome da categoria")
                cor_cat = st.color_picker("Cor", "#6157ff")
                if st.button("Adicionar categoria"):
                    if nome_cat:
                        categorias_config.append({"nome": nome_cat.upper(), "cor": cor_cat, "status": "Ativo"})
                        salvar_json(CATEGORIAS_JSON, categorias_config)
                        registrar_auditoria("CRIAR", "CATEGORIAS", "Categoria criada", nome_cat.upper())
                        st.success("Categoria adicionada.")
                        st.rerun()

            elif acao_cat == "Editar" and categorias_config:
                nomes_cat = [c["nome"] for c in categorias_config]
                selecionada = st.selectbox("Categoria", nomes_cat, key="editar_cat")
                idx = nomes_cat.index(selecionada)
                nome_cat = st.text_input("Nome", categorias_config[idx]["nome"])
                cor_cat = st.color_picker("Cor", categorias_config[idx].get("cor", "#6157ff"))
                status_cat = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if categorias_config[idx].get("status", "Ativo") != "Inativo" else 1, key="status_cat")
                if st.button("Salvar categoria"):
                    antes_cat = dict(categorias_config[idx])
                    categorias_config[idx] = {"nome": nome_cat.upper(), "cor": cor_cat, "status": status_cat}
                    salvar_json(CATEGORIAS_JSON, categorias_config)
                    registrar_auditoria("EDITAR", "CATEGORIAS", "Categoria alterada", selecionada, antes_cat, categorias_config[idx])
                    st.success("Categoria atualizada.")
                    st.rerun()

            elif acao_cat == "Inativar" and categorias_config:
                categorias_ativas = [c for c in categorias_config if c.get("status", "Ativo") != "Inativo"]
                nomes_cat = [c["nome"] for c in categorias_ativas]
                if nomes_cat:
                    selecionada = st.selectbox("Categoria", nomes_cat, key="inativar_cat")
                    if st.button("Inativar categoria"):
                        idx_cat = next(i for i, c in enumerate(categorias_config) if c["nome"] == selecionada)
                        antes_cat = dict(categorias_config[idx_cat])
                        categorias_config[idx_cat]["status"] = "Inativo"
                        salvar_json(CATEGORIAS_JSON, categorias_config)
                        registrar_auditoria("INATIVAR", "CATEGORIAS", "Categoria inativada", selecionada, antes_cat, categorias_config[idx_cat])
                        st.success("Categoria inativada.")
                        st.rerun()
                else:
                    st.info("Nenhuma categoria ativa para inativar.")

        with tab_unidades:
            st.dataframe(pd.DataFrame(unidades_config), use_container_width=True)
            acao_unidade = st.radio("Ação de unidade", ["Adicionar", "Editar", "Inativar"], horizontal=True)

            if acao_unidade == "Adicionar":
                nome_unidade = st.text_input("Nome da unidade")
                cor_unidade = st.color_picker("Cor", "#38bdf8", key="cor_unidade_add")
                if st.button("Adicionar unidade"):
                    if nome_unidade:
                        unidades_config.append({"nome": nome_unidade.upper(), "cor": cor_unidade, "status": "Ativo"})
                        salvar_json(UNIDADES_JSON, unidades_config)
                        registrar_auditoria("CRIAR", "UNIDADES", "Unidade criada", nome_unidade.upper())
                        st.success("Unidade adicionada.")
                        st.rerun()

            elif acao_unidade == "Editar" and unidades_config:
                nomes_unidade = [u["nome"] for u in unidades_config]
                selecionada = st.selectbox("Unidade", nomes_unidade, key="editar_unidade")
                idx = nomes_unidade.index(selecionada)
                nome_unidade = st.text_input("Nome", unidades_config[idx]["nome"], key="nome_unidade_edit")
                cor_unidade = st.color_picker("Cor", unidades_config[idx].get("cor", "#38bdf8"), key="cor_unidade_edit")
                status_unidade = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if unidades_config[idx].get("status", "Ativo") != "Inativo" else 1, key="status_unidade")
                if st.button("Salvar unidade"):
                    antes_unidade = dict(unidades_config[idx])
                    unidades_config[idx] = {"nome": nome_unidade.upper(), "cor": cor_unidade, "status": status_unidade}
                    salvar_json(UNIDADES_JSON, unidades_config)
                    registrar_auditoria("EDITAR", "UNIDADES", "Unidade alterada", selecionada, antes_unidade, unidades_config[idx])
                    st.success("Unidade atualizada.")
                    st.rerun()

            elif acao_unidade == "Inativar" and unidades_config:
                unidades_ativas = [u for u in unidades_config if u.get("status", "Ativo") != "Inativo"]
                nomes_unidade = [u["nome"] for u in unidades_ativas]
                if nomes_unidade:
                    selecionada = st.selectbox("Unidade", nomes_unidade, key="inativar_unidade")
                    if st.button("Inativar unidade"):
                        idx_unidade = next(i for i, u in enumerate(unidades_config) if u["nome"] == selecionada)
                        antes_unidade = dict(unidades_config[idx_unidade])
                        unidades_config[idx_unidade]["status"] = "Inativo"
                        salvar_json(UNIDADES_JSON, unidades_config)
                        registrar_auditoria("INATIVAR", "UNIDADES", "Unidade inativada", selecionada, antes_unidade, unidades_config[idx_unidade])
                        st.success("Unidade inativada.")
                        st.rerun()
                else:
                    st.info("Nenhuma unidade ativa para inativar.")

    with tab_aparencia:
        with st.form("form_aparencia"):
            tema_form = st.selectbox("Tema", ["dark", "light"], index=0 if config.get("tema", "dark") == "dark" else 1)
            cor_form = st.color_picker("Cor principal", config.get("cor_principal", "#6157ff"))
            fonte_form = st.selectbox("Fonte", ["Inter", "Arial", "Roboto", "Segoe UI"], index=["Inter", "Arial", "Roboto", "Segoe UI"].index(config.get("fonte", "Inter")) if config.get("fonte", "Inter") in ["Inter", "Arial", "Roboto", "Segoe UI"] else 0)
            if st.form_submit_button("Salvar aparência"):
                config["tema"] = tema_form
                config["cor_principal"] = cor_form
                config["fonte"] = fonte_form
                salvar_json(CONFIG_JSON, config)
                st.success("Aparência salva. A interface será atualizada.")
                st.rerun()

    with tab_backup:
        st.write(f"Último backup: {config.get('ultimo_backup', 'Nunca')}")
        st.write(f"Último backup em nuvem: {config.get('ultimo_backup_google_drive', 'Nunca')}")
        backup_auto = st.toggle("Backup automático diário", value=bool(config.get("backup_automatico_diario", True)))
        if backup_auto != bool(config.get("backup_automatico_diario", True)):
            config["backup_automatico_diario"] = bool(backup_auto)
            salvar_json(CONFIG_JSON, config)
            registrar_auditoria("CONFIGURAR", "BACKUP", f"Backup automático diário: {backup_auto}", "backup_automatico_diario")
            st.rerun()
        backup_auto_alteracao = st.toggle(
            "Backup rápido a cada alteração de dados",
            value=bool(config.get("backup_incremental_alteracao", True)),
            help="Salva uma cópia apenas do arquivo alterado, com data e hora. É mais rápido que gerar um backup completo."
        )
        if backup_auto_alteracao != bool(config.get("backup_incremental_alteracao", True)):
            config["backup_incremental_alteracao"] = bool(backup_auto_alteracao)
            salvar_json(CONFIG_JSON, config)
            registrar_auditoria("CONFIGURAR", "BACKUP", f"Backup rápido por alteração: {backup_auto_alteracao}", "backup_incremental_alteracao")
            st.rerun()
        backup_completo_alteracao = st.toggle(
            "Backup completo a cada alteração (mais lento)",
            value=bool(config.get("backup_completo_alteracao", False)),
            help="Compacta o sistema inteiro a cada alteração. Use somente se precisar, pois pode deixar o sistema lento."
        )
        if backup_completo_alteracao != bool(config.get("backup_completo_alteracao", False)):
            config["backup_completo_alteracao"] = bool(backup_completo_alteracao)
            salvar_json(CONFIG_JSON, config)
            registrar_auditoria("CONFIGURAR", "BACKUP", f"Backup completo por alteração: {backup_completo_alteracao}", "backup_completo_alteracao")
            st.rerun()
        backup_drive_ativo = st.toggle("Copiar backup para OneDrive / Google Drive", value=bool(config.get("backup_google_drive_ativo", True)))
        pasta_drive_atual = obter_pasta_backup_nuvem()
        pasta_drive = st.text_input(
            "Pasta de backup em nuvem",
            value=pasta_drive_atual,
            placeholder=r"C:\Users\Dell\OneDrive\Backups Sistema Alpes"
        ).strip()
        if backup_drive_ativo != bool(config.get("backup_google_drive_ativo", True)) or pasta_drive != str(config.get("backup_google_drive_pasta", "")).strip():
            config["backup_google_drive_ativo"] = bool(backup_drive_ativo)
            config["backup_google_drive_pasta"] = pasta_drive
            salvar_config_sem_marcar_backup()
            registrar_auditoria("CONFIGURAR", "BACKUP", f"Backup em nuvem: {backup_drive_ativo} | {pasta_drive}", "backup_nuvem")
        erro_drive_backup = st.session_state.get("ultimo_erro_backup_google_drive", "")
        if erro_drive_backup:
            st.warning(erro_drive_backup)
        erro_backup_alteracao = st.session_state.get("erro_backup_automatico_alteracao", "")
        if erro_backup_alteracao:
            st.warning(f"Backup automático por alteração falhou: {erro_backup_alteracao}")
        erro_backup_incremental = st.session_state.get("erro_backup_incremental", "")
        if erro_backup_incremental:
            st.warning(f"Backup rápido por alteração falhou: {erro_backup_incremental}")
        ultimo_incremental = st.session_state.get("ultimo_backup_incremental", "")
        if ultimo_incremental:
            st.caption(f"Último backup rápido: {ultimo_incremental}")
        if config.get("alteracao_pendente_backup", False):
            st.warning(f"Backup pendente desde: {config.get('ultima_alteracao', 'alteracao recente')}")
        else:
            st.success("Backup atualizado.")
        if st.button("Gerar backup"):
            if ambiente_producao():
                registrar_auditoria("EXPORTAR", "BACKUP", "Backup local bloqueado em produção", "backup_local")
                st.info("Em produção, o backup operacional deve ser feito por snapshots/exportações do Supabase.")
            else:
                zip_path = gerar_backup()
                st.success(f"Backup gerado: {zip_path}")
                destino_drive = os.path.join(config.get("backup_google_drive_pasta", ""), os.path.basename(zip_path)) if config.get("backup_google_drive_pasta") else ""
                if destino_drive and os.path.exists(destino_drive):
                    st.success(f"Cópia em nuvem criada: {destino_drive}")

        export_col1, export_col2 = st.columns(2)
        buffer_produtos = io.BytesIO()
        with pd.ExcelWriter(buffer_produtos, engine="openpyxl") as writer:
            df_produtos.drop(columns=["estoque_atual", "situacao"], errors="ignore").to_excel(writer, sheet_name="Produtos", index=False)
        export_col1.download_button(
            "Exportar Produtos Para Excel",
            data=buffer_produtos.getvalue(),
            file_name=f"produtos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        buffer_movimentacoes = io.BytesIO()
        with pd.ExcelWriter(buffer_movimentacoes, engine="openpyxl") as writer:
            df_mov.to_excel(writer, sheet_name="Movimentacoes", index=False)
        export_col2.download_button(
            "Exportar Movimentações Para Excel",
            data=buffer_movimentacoes.getvalue(),
            file_name=f"movimentacoes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        if st.button("Sincronizar backup em nuvem", use_container_width=True):
            if ambiente_producao():
                st.warning("Restauração por ZIP/local não é permitida em produção. Use restauração controlada no Supabase.")
                st.stop()
            zip_recente = backup_nuvem_mais_recente()
            if not zip_recente:
                st.warning("Nenhum backup encontrado na pasta de nuvem.")
            else:
                try:
                    restaurar_backup_zip(zip_recente)
                    registrar_auditoria("SINCRONIZAR", "BACKUP", f"Backup restaurado da nuvem: {zip_recente}", os.path.basename(zip_recente))
                    if os.path.exists(PRODUTOS_XLSX):
                        try:
                            qtd_produtos_restaurados = len(pd.read_excel(PRODUTOS_XLSX))
                            st.info(f"Produtos restaurados no arquivo: {qtd_produtos_restaurados}")
                        except Exception:
                            pass
                    st.success(f"Último backup da nuvem restaurado: {zip_recente}")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Não foi possível restaurar o backup da nuvem: {erro}")

        backup_upload = st.file_uploader("Restaurar backup", type=["zip"])
        if backup_upload and st.button("Restaurar backup agora"):
            if ambiente_producao():
                st.warning("Restauração por ZIP/local não é permitida em produção. Use restauração controlada no Supabase.")
                st.stop()
            restaurar_backup_zip(backup_upload)
            if os.path.exists(PRODUTOS_XLSX):
                try:
                    qtd_produtos_restaurados = len(pd.read_excel(PRODUTOS_XLSX))
                    st.info(f"Produtos restaurados no arquivo: {qtd_produtos_restaurados}")
                except Exception:
                    pass
            st.success("Backup restaurado.")
            st.rerun()

    if admin_logado:
        with tab_auditoria:
            st.subheader("Histórico De Auditoria")
            auditoria = carregar_json(AUDITORIA_JSON, [])
            if auditoria:
                df_auditoria = pd.DataFrame(auditoria)
                modulo_auditoria = st.selectbox(
                    "Módulo",
                    ["Todos"] + sorted(df_auditoria.get("modulo", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
                )
                if modulo_auditoria != "Todos":
                    df_auditoria = df_auditoria[df_auditoria["modulo"].astype(str) == modulo_auditoria]
                st.dataframe(formatar_colunas_tabela(df_auditoria.tail(300).iloc[::-1]), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma ação registrada ainda.")


