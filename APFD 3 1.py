# Sistema de Geracao de Manifestacoes APFD - MPMG

from dotenv import load_dotenv
import os
import google.generativeai as genai
import tiktoken
from langgraph.graph import StateGraph
from openai import AzureOpenAI
from tkinter import Tk, filedialog
from typing import TypedDict, List, Optional, Dict
from IPython.display import display, Markdown
from datetime import datetime

# ===== CONFIGURACAO INICIAL =====
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ===== ROUTER LLM =====
class LLMRouter:
    """Router inteligente para gerenciar Azure OpenAI e Gemini"""
    
    def __init__(self, azure_client, azure_model_name, gemini_model_name="gemini-1.5-flash", 
                 token_threshold=100000, encoding_name="cl100k_base"):
        self.azure_client = azure_client
        self.azure_model_name = azure_model_name
        self.gemini_model_name = gemini_model_name
        self.token_threshold = token_threshold
        self.cumulative_tokens = 0
        self.azure_failed = False
        
        try:
            self.encoder = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            print(f"Aviso: Erro ao carregar encoder {encoding_name}: {e}")
            self.encoder = tiktoken.get_encoding("cl100k_base")
            
        try:
            if GOOGLE_API_KEY:
                self.gemini_model = genai.GenerativeModel(gemini_model_name)
            else:
                self.gemini_model = None
        except Exception as e:
            print(f"Erro ao inicializar Gemini: {e}")
            self.gemini_model = None

    def _count_tokens(self, messages):
        try:
            tokens = 0
            for msg in messages:
                content = msg.get('content', '')
                if isinstance(content, str):
                    tokens += len(self.encoder.encode(content))
            return tokens
        except Exception:
            total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
            return total_chars // 4

    def _use_azure(self, messages, temperature=0.3, max_tokens=4096):
        try:
            response = self.azure_client.chat.completions.create(
                model=self.azure_model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=8192
            )
            usage = getattr(response, 'usage', None)
            if usage:
                self.cumulative_tokens += getattr(usage, 'total_tokens', 0)
            print(f"Azure OpenAI usado - tokens acumulados: {self.cumulative_tokens}")
            self.azure_failed = False
            return response
        except Exception as e:
            print(f"ERRO no Azure: {e}")
            self.azure_failed = True
            raise

    def _use_gemini(self, messages, temperature=0.3, max_tokens=4096):
        if not self.gemini_model:
            raise Exception("Modelo Gemini não disponível")
        
        prompt_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                prompt_parts.append(f"Sistema: {content}")
            elif role == 'user':
                prompt_parts.append(f"Usuário: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistente: {content}")
        
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistente:"
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=min(max_tokens, 8192)
        )
        
        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            print("Gemini usado como backup")
            
            class Message:
                def __init__(self, content):
                    self.content = content
            class Choice:
                def __init__(self, content):
                    self.message = Message(content)
            class MockResponse:
                def __init__(self, content):
                    self.choices = [Choice(content)]
                    self.usage = None
            
            return MockResponse(response.text)
        except Exception as e:
            print(f"ERRO no Gemini: {e}")
            raise Exception(f"Ambos os modelos falharam: {e}")

    def chat_completion(self, messages, temperature=0.3, max_tokens=4096):
        prompt_tokens = self._count_tokens(messages)
        
        if (not self.azure_failed and 
            self.cumulative_tokens + prompt_tokens <= self.token_threshold):
            try:
                return self._use_azure(messages, temperature, max_tokens)
            except Exception:
                pass
        
        return self._use_gemini(messages, temperature, max_tokens)

    def get_status(self):
        return {
            "tokens_acumulados": self.cumulative_tokens,
            "limite_tokens": self.token_threshold,
            "azure_disponivel": not self.azure_failed,
            "gemini_disponivel": self.gemini_model is not None
        }

# ===== INICIALIZACAO DO SISTEMA =====
try:
    azure_client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2025-01-01-preview",
        azure_endpoint=AZURE_OPENAI_ENDPOINT
    ) if AZURE_OPENAI_API_KEY else None
except:
    azure_client = None

router = LLMRouter(
    azure_client=azure_client,
    azure_model_name=AZURE_OPENAI_DEPLOYMENT_NAME or "gpt-4",
    gemini_model_name="gemini-2.5-flash",
    token_threshold=100000
)

# ===== ESTADO DO LANGGRAPH =====
class EstadoAPFD(TypedDict):
    files: Optional[List[Dict[str, str]]]
    texto_base: Optional[str]
    analise_antecedentes: Optional[Dict]
    apfd_data: Optional[Dict]
    manifestacao_apfd: Optional[str]

# ===== FUNCOES AUXILIARES =====
def selecionar_arquivos():
    root = Tk()
    root.withdraw()
    caminhos = filedialog.askopenfilenames(
        title="Selecione os documentos do caso",
        filetypes=[
            ("PDF e Word", ("*.pdf", "*.docx")),
            ("Textos", ("*.txt", "*.md", "*.csv")),
            ("Todos os arquivos", "*.*")
        ]
    )
    return list(caminhos)

EASY_OCR_READER = None

def _get_easyocr_reader():
    global EASY_OCR_READER
    if EASY_OCR_READER is None:
        import easyocr  # type: ignore
        # Idiomas principais usados nos documentos: português e inglês (fallback)
        EASY_OCR_READER = easyocr.Reader(['pt', 'en'], gpu=False)
    return EASY_OCR_READER

def _ocr_pdf(file_path: str) -> str:
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        return f"[Erro OCR: PyMuPDF (fitz) não instalado: {e}]"
    try:
        reader = _get_easyocr_reader()
    except Exception as e:
        return f"[Erro OCR: EasyOCR não instalado/configurado: {e}]"

    try:
        doc = fitz.open(file_path)
        textos = []
        # Renderiza páginas com zoom para melhorar OCR
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat)
            # Converte para numpy array (H, W, C)
            import numpy as np
            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.h, pix.w, pix.n)
            # EasyOCR aceita grayscale ou RGB; garantir RGB
            if pix.n == 4:
                img = img[:, :, :3]
            results = reader.readtext(img, detail=0, paragraph=True)
            if results:
                textos.append("\n".join(results))
        doc.close()
        texto_ocr = "\n\n".join(t for t in textos if t and t.strip())
        return texto_ocr if texto_ocr.strip() else ""
    except Exception as e:
        return f"[Erro ao executar OCR no PDF: {e}]"

def get_file_content(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in [".txt", ".md", ".csv"]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
    
    elif ext == ".pdf":
        # 1) Tentativa com PyPDF2 (texto embutido)
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                textos = []
                for page in pdf_reader.pages:
                    try:
                        t = page.extract_text() or ""
                    except Exception:
                        t = ""
                    if t:
                        textos.append(t)
                texto = "\n".join(textos)
                if texto.strip():
                    return texto
        except Exception:
            pass
        # 2) Fallback: OCR com EasyOCR + PyMuPDF
        ocr_text = _ocr_pdf(file_path)
        if ocr_text and not ocr_text.startswith("[Erro"):
            return ocr_text
        # 3) Se nada funcionar, retorna erro
        return f"[Erro ao ler PDF: {file_path}]"
    
    elif ext in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except:
            return f"[Erro ao ler documento Word: {file_path}]"
    
    else:
        return f"[Arquivo não suportado: {file_path}]"

# ===== NOS DO LANGGRAPH =====

def upload_node_files_only(state):
    print("=== CONFIGURAÇÃO INICIAL - APFD ===")
    print(f"Status do Router: {router.get_status()}")
    print("Selecione os arquivos do caso:")
    lista_de_arquivos = selecionar_arquivos()
    if not lista_de_arquivos:
        raise ValueError("Nenhum arquivo selecionado.")

    files_content = []
    for path in lista_de_arquivos:
        print(f"Processando: {os.path.basename(path)}")
        content = get_file_content(path)
        if content and not content.startswith("[Erro"):
            files_content.append({"name": os.path.basename(path), "content": content})

    if not files_content:
        raise ValueError("Nenhum conteúdo foi carregado.")

    print(f"{len(files_content)} arquivo(s) carregado(s)")
    state["files"] = files_content
    state["manifestacao_base"] = None

    return state

def gerar_texto_base_node(state):
    if state.get("manifestacao_base"):
        print("Manifestação base fornecida pelo usuário; pulando geração da base...")
        state["texto_base"] = state.get("manifestacao_base", "")
        return state
    if state.get("texto_base"):
        print("Manifestação base já carregada, pulando geração...")
        return state
    
    print("\n [GERANDO BASE PARA MANIFESTAÇÃO APFD]\n")
    
    documentos_texto = "Documentos do processo:\n"
    for file in state.get("files", []):
        documentos_texto += f"\n--- {file['name']} ---\n{file['content']}\n"
    
    system_message = (
        "Você é um Promotor de Justiça do Ministério Público de Minas Gerais. "
        "Elabore uma síntese estruturada do auto de prisão em flagrante para subsidiar a manifestação ministerial."
    )
    
    prompt = """
    Analise os documentos e produza uma base informativa para a manifestação em APFD seguindo este formato:
    1. Identificação completa do(s) autuado(s)
    2. Resumo circunstanciado do flagrante
    3. Elementos probatórios relevantes
    4. Pontos a verificar para a atuação ministerial
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": documentos_texto + prompt}
    ]
    
    try:
        response = router.chat_completion(messages, temperature=0.3, max_tokens=4096)
        manifestacao_base_texto = response.choices[0].message.content.strip()
        print("Base da manifestação gerada")
        state["texto_base"] = manifestacao_base_texto
        state["manifestacao_base"] = manifestacao_base_texto
    except Exception as e:
        print(f"Erro: {e}")
        state["manifestacao_base"] = "[ERRO] Não foi possível gerar a manifestação base"
    
    return state

def analisar_antecedentes_node(state):
    print("\n [ANALISANDO ANTECEDÊNTES E MEDIDAS DESPENALIZADORAS]\n")
    
    texto_base = state.get("texto_base", "")
    if state.get("files"):
        documentos = "\n\nDocumentos adicionais:\n"
        for file in state.get("files", []):
            documentos += f"\n--- {file['name']} ---\n{file['content']}\n"
        texto_completo = texto_base + documentos
    else:
        texto_completo = texto_base
    
    system_message = "Você é um analista jurídico especializado em análise de antecedentes criminais."
    
    prompt = """
    Analise os documentos fornecidos e, com base nos conceitos abaixo, extraia as respostas para as seguintes perguntas usando Chain of Thoughts:

    resposta_promotoria: Promotoria de Justiça responsável pela manifestação;
    resposta_comarca: comarca da Promotoria e do juízo competentes;
    resposta_numero_processo: número dos autos do processo;
    resposta_flagranteados: nome do(s) flagranteados(s);
    resposta_crimes: crime(s) flagranteados(s);
    resposta_data_crimes: data(s) da prática do(s) crime(s) flagranteado(s);
    resposta_penas: pena(s) cominada(s) ao(s) crime(s) flagranteados(s) [resposta_crimes]. Pena mínima cominada ao menor pena aplicável a um delito, prevista na própria Lei. Pena máxima cominada é a maior pena aplicável a um delito, prevista na prápria Lei. Obs. importante: sempre seguir a pena mínima e máxima cominada do crime específico identificado no dispositivo legal referenciado (caput, parágrafo, etc). Ex.: Furto simples (art. 155, caput, do Código Penal) - Pena mínima cominada: 1 ano de reclusão; Pena máxima cominada: 4 anos de reclusão; Furto qualificado (art. 155, inciso, I a V, do Código penal) - Pena mínima cominada: 2 anos de reclusão; Pena máxima cominada: 8 anos de reclusão. Se houver mais de um crime, some as penas mínimas cominadas e as penas máximas cominadas para as avaliações futuras.
    resposta_homologacao: cabimento, ou não, da homologação do flagrante delito;
    resposta_incisos_art_302: inciso(s) do art. 302 do código de Processo Penal que justificam a homologação do flagrante delito;
    resposta_reincidencia: reincidência(s) do(s) flagranteados(s). Pode ser extraído das certidões de antecedentes criminais juntadas aos autos;
    resposta_antecedentes: antecedentes criminais do(s) flagranteados(s). Pode ser extraído das certidões de antecedentes criminais juntadas aos autos;
    
    1. REINCIDÊNCIA:
        Conceito: Reincidência é a prática do crime flagranteado por um indivíduo previamente condenado com trânsito em julgado por crime anterior cuja pena ainda não foi extinta há mais de 5 anos. Não se deve confundir reincidência com passagens policiais anteriores, pois a reincidência exige a prensença dos requisitos apontados nesta conceituação.
        - Há certidões de antecedentes criminais [resposta_antecedentes]?
        - O flagranteado possui condenações pretéritas já transidas em julgado que configurem reincidência? Pela prática de qual crime?
        - Há menção a reincidência específica ou genérica?
        - Tempo decorrido desde a última condenação?

    2. MAUS ANTECEDENTES CRIMINAIS:
        Conceito: Maus antecedentes criminais são as condenações criminais anteriores ao crime flagranteado já transitadas em julgado cuja pena jã foi cumprida e extinta há mais de 5 anos. Não se deve confundir maus antecedentes criminais com passagens policiais anteriores, pois a configuração de maus antecedentes criminais exige a presença dos requisitos apontados nesta conceituação.
        - Há certidões de antecedentes criminais [resposta_antecedentes]?
        - Nas certidões criminais do flagranteado constam maus antecedentes criminais? Quais? [resposta_antecedentes]

    3. HOMOLOGAÇÃO DO FLAGRANTE DELITO:
        Conceito: A homologação do flagrante delito é a decisão do juízo que confirma a ratificação do flagrante delito pelo Delegado de Polícia. Para que o flagrante delito seja homologado, é necessário que o(s) suposto(s) autor(es) tenham sido flagrados a) na prática do delito, b) logo após cometé-lo, c) sendo perseguidos, presumindo-se ser(em) o(s) autores(s), ou d) na posse de instrumentos, armas, objetos ou papéis que permitam presumir a autoria do delito, tudo nos termos do art. 302, incisos I a IV, do Código de Processo Penal.
        - O(s) flagranteado(s) foi(foram) flagrado(s) na prática do delito, logo após cometé-lo, sendo perseguido(s), presumindo-se ser(em) o(s) autor(es), ou na posse de instrumentos, armas, objetos ou papÃ©is que permitam presumir a autoria do delito? [resposta_homologacao]

    4. PRISÃO PREVENTIVA:
        Conceito: A prisão preventiva é uma hipótese de prisão provisória cabível quando o(s) crime(s) flagranteado(s) doloso(s) possui(em) pena máxima cominada superior a 4 (quatro) anos, quando o réu for reincidente, ou se necessário para garantia do cumprimento das medidas protetivas de urgência em crimes envolvendo violência doméstica e familiar contra a mulher, criançaa, adolescente, idoso, enfermo ou pessoa com deficiência, desde que haja prova da existência do crime, indício suficiente de autoria e de perigo gerado pelo estado de liberdade do flagranteado. Para sua decretação, a prisão preventiva deve ser necessária e recomendável para garantia da ordem pública, da ordem econômica, para conveniência da instrução criminal ou para assegurar a aplicação da lei penal, bem como em razão do descumprimento das medidas cautelares diversas da prisão fixadas. Deve ser motivada e fundamentada em receio de perigo e existência concreta de fatos novos ou contemporâneos. Encontra-se prevista nos arts. 312 e 313 do Código de Processo Penal.
        - O crime flagranteado é doloso e possui pena máxima cominada superior a 4 (quatro) anos? [resposta_penas]
        - O flagranteado é reincidente? [resposta_reincidencia]
        - A prisão preventiva é necessÃ¡ria para garantir o cumprimento das medidas protetivas de urgência em crimes envolvendo violência doméstica e familiar contra a mulher, criança, adolescente, idoso, enfermo ou pessoa com deficiência?
        - Existe prova da existência do crime, indício suficiente de autoria e de perigo gerado pelo estado de liberdade do flagranteado (ex.: reiteração delitiva)?
        - Existem concretamente fatos novos ou contemporâneos que permitam a constatação de receio de perigo e que justifiquem a prisão preventiva?
        - A prisão preventiva deve ser necessária e recomendável para garantia da ordem pública, da ordem econômica, para conveniência da instrução criminal ou para assegurar a aplicação da lei penal, ou ainda em razão do descumprimento das medidas cautelares diversas da prisão fixadas?

    5. MEDIDAS CAUTELARES DIVERSAS DA PRISÃO:
        Conceito: As medidas cautelares diversas da prisão são medidas aplicadas quando, presentes materialidade e indícios de autoria do crime flagranteado, não é cabível a prisãoo preventiva por ser medida extrema e desnecessária no caso concreto, podendo ser adotadas medidas alternativas menos gravosas para garantir a inexistência ou reduzir o perigo gerado pelo estado de liberdade do flagranteado. São recomendadas quando a gravidade concreta do delito, ou o histórico criminal do flagranteado, não recomendam a prisão preventiva. As medidas cabíveis estão previstas no art. 319 do Código de Processo Penal. Devem ser analisadas apenas quando não for cabível a prisão preventiva. As medidas cautelares a serem aplicadas devem ter correlação fática com seu objetivo, vale dizer, a supressão ou redução do perigo gerado pelo estado de liberdade do flagranteado, assim como a garantia de escorreita apuração criminal.
        - Há provas de materialidade e indícios de autoria?
        - E necessária ou recomendável a decretação da prisão preventiva?
        - Caso negativa a resposta anterior, as medidas cautelares diversas da prisão são suficientes para garantir a inexistência ou reduzir o perigo gerado pelo estado de liberdade do flagranteado?
        - Quais as medidas cautelares diversas da prisão cabíveeis ao caso concreto?
    
    ### ANÁLISE DE ANTECEDENTES ###
    [Sua análise detalhada aqui]
    
    ### RESUMO EXECUTIVO ###
    - Reincidência: [SIM/NÃO - detalhes]
    - Maus antecedentes: [SIM/NÃO - detalhes]
    - Homologação do flagrante delito: [SIM/NÃO - detalhes]
    - Prisão preventiva: [SIM/NÃO - detalhes]
    - Medidas cautelares diversas da prisão: [SIM/NÃO - detalhes]

    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": texto_completo + "\n\n" + prompt}
    ]
    
    try:
        response = router.chat_completion(messages, temperature=0.3, max_tokens=2048)
        analise = response.choices[0].message.content.strip()
        print(analise)
        state["analise_antecedentes"] = {"analise_completa": analise}
    except Exception as e:
        print(f"Erro: {e}")
        state["analise_antecedentes"] = {"analise_completa": "Erro na análise"}
    
    return state

def montar_exemplos_cod(exemplos: List[Dict[str, str]]) -> str:
    partes = []
    for ex in exemplos:
        partes.append(f"**{ex['aspecto']}**\nPontos de verificação:\n{ex['analise']}")
    return "\n\n".join(partes)

def gerarPromocaoHomologacaoComPreventiva(manifestacao_base: str, analise: str) -> str:
    exemplos_apfd_draft = [
        {
            'aspecto': 'Análise de reincidência',
            'analise': """
            Condenação anterior transitada? Verificar.
            Tempo inferior a 5 anos? Calcular.
            Crime anterior similar? Comparar.
            Reincidência específica ou genêrica?
            """.strip()
        },
        {
            'aspecto': 'Análise de maus antecedentes criminais',
            'analise': """
            Condenação anterior transitada? Verificar.
            Tempo desde a extinçãoo da pena superior a 5 anos? Calcular.
            """.strip()
        },
        {
            'aspecto': 'Fundamentação de cabimento ou não de homologação do flagrante delito',
            'analise': """
            Presentes os requisitos do flagrante estabelecidos no art. 302, incisos I a IV, do Código de Processo Penal? Verificar.
            Fundamentação adequada e específica.
            """.strip()
        },
        {
            'aspecto': 'Fundamentação da prisão preventiva',
            'analise': """
            Verificar o fumus comissi delicti (materialidade e indícios de autoria).
            Detalhar o periculum libertatis com base em fatos concretos.
            Confirmar o atendimento aos arts. 312 e 313 do CPP.
            Demonstrar a insuficiência das medidas cautelares diversas da prisão.
            """.strip()
        }
    ]
    exemplos_texto = montar_exemplos_cod(exemplos_apfd_draft)
    system_message = 'Você é um Promotor de Justiça do MPMG redigindo manifestação pela homologação do flagrante e conversão em prisão preventiva.'
    prompt = f"""    Com base na síntese do flagrante e na análise abaixo, redija a promoção ministerial que homologa o auto de prisão em flagrante e requer sua conversão em prisão preventiva.
    
    Use o método Chain of Draft (CoD) - analise cada aspecto passo a passo antes de redigir:
    
    {exemplos_texto}
    
    SÍNTESE DO FLAGRANTE PARA ANÁLISE:
    
    SÍNTESE DO FLAGRANTE:
    {manifestacao_base}
    
    ANÁLISE PRÉVIA:
    {analise}
    
    ESTRUTURA DA PROMOÇÃO MINISTERIAL:
    
    1. IDENTIFICAÇÃO PROCESSUAL
        - Identificar o processo e o(s) investigados(s), em linhas distintas;
        - Ex.: "AUTOS nº [resposta_numero_processo]".
        - Ex.: "FLAGRANTEADO(S): [resposta_flagranteados]".
    
    2. ABERTURA DA MANIFESTAÇÃO:
        - Sempre incluir o seguinte parágrafo inicial: "O MINISTÉRIO PÚBLICO DO ESTADO DE MINAS GERAIS, por meio do Promotor de Justiça que esta subscreve, vem, à vista da comunicação do flagrante do autuado, manifestar-se nos seguintes termos:"

    
    3. FUNDAMENTAÇÃO  (Use CoD aqui)
        a) Homologação  do flagrante delito
        - Analise o cabimento, ou não, da homologação do flagrante delito.
        - Exemplo de cabimento: "Cuida-se da comunicação de prisão em flagrante delito de [resposta_flagranteados] pela prática, no dia [resposta_data_crimes], do(s) delito(s) previsto(s) no(s) art. [resposta_crimes].
        Tendo sido observados pela autoridade policial todos os requisitos legais e encontrando a presente situação arrimo no art. 302, inciso(s) [resposta_incisos_art_302], e 304 do Código de Processo Penal, o Ministério Público manifesta-se pela homologação da prisão em flagrante do autuado."
        - Exemplo de não cabimento: "Cuida-se da comunicação de prisão em flagrante delito de [resposta_flagranteados] pela prática, no dia [resposta_data_crimes], do(s) delito(s) previsto(s) no(s) art. [resposta_crimes].
        Analisando a situação posta, não se vislumbra o cumprimento, pelas autoridades responsáveis pela condução do autuado em flagrante, de todos os requisitos legais necessários para o reconhecimento de situação de flagrância, haja vista a ausência de quaisquer das hipóteses do art. 302, incisos I a IV, do Código de Processo Penal.
        Isso porque [explicar a situação que impede a homologação ...].
        Pelo exposto, o Ministério Público manifesta-se pela não homologação da prisão em flagrante do autuado."

        b) Conversão do flagrante em prisão preventiva
        - Fundamente a necessidade de conversão do flagrante em prisão preventiva, partindo da premissa de que essa é a medida adequada ao caso.
        - Detalhe o fumus comissi delicti, evidenciando prova da materialidade e indícios de autoria disponíveis.
        - Demonstre o periculum libertatis com base em dados concretos (garantia da ordem pública, conveniência da instrução criminal, asseguramento da aplicação da lei penal ou risco de reiteração).
        - Aponte o enquadramento jurídico nos arts. 312 e 313 do Código de Processo Penal, identificando os incisos pertinentes.
        - Explique por que as medidas cautelares previstas no art. 319 do CPP seriam insuficientes ou inadequadas para mitigar o risco identificado.
        - Exemplo de cabimento de prisão preventiva: "
                 A prisão foi realizada nos termos legais e já cumpriu suas funções primordiais, quais sejam, evitar que a ação criminosa possa gerar todos os seus efeitos e garantir a qualidade e a idoneidade da prova colhida imediatamente após a prática do delito, restando, agora, analisar a necessidade de sua conversão em prisão preventiva, nos termos do art. 310 do CPP.
                Neste ponto, entende o Parquet ser imperiosa a decretação da prisão preventiva do autuado.
                
                A pena máxima do delito previsto no art. 33, caput, da Lei n. 11.343/2006 é muito superior a quatro anos, razão pela qual presente o requisito do art. 313, I, do CPP.

                Ademais, são claras a autoria e a materialidade do delito, como se infere da leitura do REDS, bem como do auto de prisão em flagrante, em especial da quantidade e forma de acondicionamento dos entorpecentes encontrados, dos acessórios para a traficância também encontrados e da confissão do autuado da propriedade dos entorpecentes e destino ao tráfico de drogas há muito praticado, tudo quando registrado no REDS, além dos depoimentos dos policiais militares que atenderam à ocorrência, sendo imperioso realçar que, tratando-se de atos de agentes públicos no escorreito exercício de sua função, gozam da cabível presunção de veracidade, como reconhecido pela jurisprudência:

                            EMENTA: APELAÇÃO CRIMINAL - TRÁFICO DE DROGAS E ASSOCIAÇÃO AO TRÁFICO - PRELIMINARES - CERCEAMENTO DE DEFESA E VÍCIO PROCEDIMENTAL - INOCORRÊNCIA - INTERCEPTAÇÕES TELEFÔNICAS - LEGALIDADE - DECISÕES SOBRE A INTERCEPTAÇÃO DEVIDAMENTE FUNDAMENTADAS - NULIDADE DO FEITO POR VIOLAÇÃO AO PRINCÍPIO DA IDENTIDADE FÍSICA DO JUIZ - DESCABIMENTO - MATERIALIDADE - COMPROVAÇÃO - IRREGULARIDADE FORMAL AFASTADA - REJEIÇÃO - CONDUTAS INDIVIDUALIZADAS - PRELIMINARES REJEITADAS - MÉRITO - ABSOLVIÇÃO - IMPOSSIBILIDADE - MATERIALIDADE E AUTORIA COMPROVADAS - REDUÇÃO DAS PENAS-BASE - NECESSIDADE - DECOTE DA AGRAVANTE DA REINCIDÊNCIA - CABIMENTO - RESTITUIÇÃO DE BENS APREENDIDOS - INVIABILIDADE - RECURSO DEFENSIVO PARCIALMENTE PROVIDO.

                            [...]

                            9- Os depoimentos de policiais como testemunhas gozam de presunção iuris tantum de veracidade, portanto, prevalecem até prova em contrário.

                            [...]

                            (TJMG -  Apelação Criminal  1.0672.12.018960-6/002, Relator(a): Des. (a) Eduardo Machado , 5ª CÂMARA CRIMINAL, julgamento em 14/11/2017, publicação da súmula em 27/11/2017)


                Embora a segregação cautelar seja a última ratio, no presente caso ela se afigura necessária para a garantia da ordem pública.

                 Isso porque a gravidade concreta do delito é motivo suficiente para fundamentar a prisão preventiva, desde que sua constatação seja feita com base em dados concretos, como no caso dos autos, em que o autuado, ao que indicam elementos confiáveis, rende-se à prática de delitos, valendo lembrar que o autuado registra outras 4 (quatro) passagens prévias, por receptação (REDS 2017-007630482-001), homicídio tentado (REDS 2012-002493031-001) e tráfico de drogas (REDS 2015-026463147-001 e 2019-023280087-001).

                A liberdade do autuado, em tal panorama, faz-se evidentemente contrária à garantia da ordem pública, principalmente pela violação à saúde e à segurança pública, por óbvio afetadas com o fornecimento de substâncias ilícitas e com o fomento do tráfico e dos demais crimes que lhe são consequentes. Ao praticar a traficância, o autuado não só mantinha ativa a rede de tráfico que afetava a sociedade como um todo, como também sustentava o vício ou viciava usuários, fomentando modalidade criminosa cujo combate tantos esforços têm exigido das autoridades de segurança pública.

                Logo, eventual concessão de liberdade, neste momento, servirá apenas para que a atividade ilícita retome seu rumo livre e desenfreada, com a manutenção do fornecimento de drogas a pessoas já deveras debilitadas ou em vias de debilitação pelo vício nefasto.

                Acerca da decretação da prisão preventiva para garantir a ordem pública diante de risco de reiteração criminosa, colhe-se julgado do e. Supremo Tribunal Federal:

                            Ementa: HABEAS CORPUS. PENAL. TRÁFICO DE DROGAS. CONVERSÃO DA PRISÃO EM FLAGRANTE EM CUSTÓDIA PREVENTIVA. LEGITIMIDADE DOS FUNDAMENTOS UTILIZADOS. GARANTIA DA ORDEM PÚBLICA. REITERAÇÃO DELITIVA. ORDEM DENEGADA. I – A prisão cautelar mostra-se suficientemente motivada para a preservação da ordem pública, haja vista a possibilidade concreta de reiteração delitiva pelo paciente. Precedentes. II – A menção feita no acórdão impugnado de que o réu exercia a atividade de segurança em local conhecido como distribuição de entorpecentes não agravou a situação do paciente, mas tão somente ratificou o decreto constritivo, no sentido da necessidade da prisão preventiva para acautelar o meio social. III – Demonstrada a habitualidade delitiva do paciente e, por conseguinte, a higidez dos motivos apresentados para a decretação da prisão preventiva do paciente, sua substituição por outra medida cautelar diversa se afigura inadequada e insuficiente. IV – Ordem denegada. (HC 118700, Relator(a): RICARDO LEWANDOWSKI, Segunda Turma, julgado em 06/11/2013, PROCESSO ELETRÔNICO DJe-227 DIVULG 18-11-2013  PUBLIC 19-11-2013)

                O Superior Tribunal de Justiça neste mesmo sentido:

                            conforme pacífica jurisprudência desta Corte, a preservação da  ordem pública justifica a imposição da prisão preventiva quando o agente ostentar maus  antecedentes, reincidência, atos infracionais pretéritos, inquéritos ou mesmo ações penais em  curso, porquanto tais circunstâncias denotam sua contumácia delitiva e, por via de consequência, sua periculosidade (RHC 107.238/GO, Rel. Ministro ANTONIO SALDANHA PALHEIRO, SEXTA TURMA, DJe 12/03/2019).  

                O Tribunal de Justiça de Minas Gerais, nesse mesmo compasso, decidiu que elementos concretos dos autos são fundamentos válidos para se converter a prisão em flagrante em prisão preventiva, para resguardar a ordem pública, como se infere do julgado abaixo:

                            EMENTA: HABEAS CORPUS. ESTELIONATO. PRISÃO PREVENTIVA. FUNDAMENTAÇÃO CONCRETA. PRESENÇA DOS REQUISITOS FÁTICOS (ARTIGO 312 DO CPP) E INSTRUMENTAL (ARTIGO 313, I, DO CPP) DA MEDIDA. GARANTIA DA ORDEM PÚBLICA. RISCO DE REITERAÇÃO DELITIVA. APLICAÇÃO DE MEDIDAS CAUTELARES DIVERSAS DA PRISÃO. DESCABIMENTO. CONSTRANGIMENTO ILEGAL NÃO CONFIGURADO. ORDEM DENEGADA. 1. Tendo sido os pacientes presos preventivamente pela suposta prática do delito de estelionato, presentes a prova da materialidade delitiva e os indícios suficientes de autoria, inexiste constrangimento ilegal na decisão que, fundamentadamente, decretou as suas segregações cautelares, visando a garantir a ordem pública e evitar a reiteração delitiva. 2. O princípio do estado de inocência, estatuído no artigo 5º, LVII, da Constituição da República, não impede a manutenção da prisão provisória quando presentes os requisitos dos artigos 312 e 313 do Código de Processo Penal. 3. O Código de Processo Penal preconiza, de forma expressa, o princípio da proporcionalidade, composto por dois outros, quais sejam: adequação e necessidade. 4. A prisão preventiva, espécie de medida cautelar é exceção na sistemática processual, dando, o quanto possível, promoção efetiva ao princípio constitucional da não-culpabilidade. Todavia, embora medida extrema, a manutenção da segregação cautelar do paciente pode ser determinada sempre que presentes os requisitos exigidos pelo Código de Processo Penal. 5. Sendo a pena máxima cominada ao delito de estelionato superior a quatro anos é admissível a manutenção da segregação provisória, como forma de garantia da ordem pública. 6. Não se mostrando adequadas e suficientes, no caso concreto, as medidas cautelares diversas da prisão, não poderão ser aplicadas, mormente quando presentes os requisitos para a manutenção da prisão preventiva. 7. Ordem denegada.  (TJMG -  Habeas Corpus Criminal  1.0000.20.461608-0/000, Relator(a): Des.(a) Marcílio Eustáquio Santos , 7ª CÂMARA CRIMINAL, julgamento em 22/07/2020, publicação da súmula em 22/07/2020)

                Ante o exposto, estando presentes os motivos ensejadores da segregação cautelar e se apresentando insuficientes as cautelares arroladas no art. 319 do CPP, o Ministério Público manifesta-se pela homologação do auto de prisão em flagrante do autuado e por sua conversão em prisão preventiva, para garantia da ordem pública, nos termos do art. 312 e 313, I, do CPP."

                - Em caso de cabimento de preventiva, transcreva as jurisprudências acima citadas, quando cabíveis.

    4. FECHO

        - Local e data (use a data atual, {datetime.now().strftime("%d de %B de %Y")}). Ex.: Belo Horizonte, 12 de agosto de 2025.

        - Assinatura do Promotor de Justiça

    IMPORTANTE: Use o Chain of Draft (CoD) para cada análise - verifique sistematicamente cada requisito antes de concluir sobre o cabimento ou não da prisão preventiva.

    IMPORTANTE: Não escreva um parágrafo específico sobre a análise de reincidência ou de maus antecedentes criminais. Analise-as juntamente à fundamentação da prisão preventiva, sem criar seção autônoma.

    Após analisar, escreva cada item em formato e estilo de peça judicial, sem enumerá-los como tópicos. Não mencione o uso de Chain of Draft (CoD) na análise.

    """
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': prompt}
    ]
    response = router.chat_completion(messages, temperature=0.3, max_tokens=2048)
    return response.choices[0].message.content.strip()

def gerarPromocaoHomologacaoComLiberdadeProvisoria(manifestacao_base: str, analise: str) -> str:
    exemplos_apfd_draft = [
        {
            'aspecto': 'Análise de reincidência',
            'analise': """
            Condenação anterior transitada? Verificar.
            Tempo inferior a 5 anos? Calcular.
            Crime anterior similar? Comparar.
            Reincidência específica ou genêrica?
            """.strip()
        },
        {
            'aspecto': 'Análise de maus antecedentes criminais',
            'analise': """
            Condenação anterior transitada? Verificar.
            Tempo desde a extinção da pena superior a 5 anos? Calcular.
            """.strip()
        },
        {
            'aspecto': 'Fundamentação de cabimento ou não de homologação do flagrante delito',
            'analise': """
            Presentes os requisitos do flagrante estabelecidos no art. 302, incisos I a IV, do Código de Processo Penal? Verificar.
            Fundamentação adequada e específica.
            """.strip()
        },
        {
            'aspecto': 'Fundamentação da liberdade provisória',
            'analise': """
            Confirmar a ausência dos requisitos da prisão preventiva.
            Identificar medidas cautelares diversas adequadas e suficientes.
            Justificar a proporcionalidade da liberdade provisória diante das circunstâncias.
            """.strip()
        }
    ]
    exemplos_texto = montar_exemplos_cod(exemplos_apfd_draft)
    system_message = 'Você é um Promotor de Justiçaa do MPMG redigindo manifestação pela homologação do flagrante e concessão de liberdade provisória.'
    prompt = f"""    Com base na síntese do flagrante e na análise abaixo, redija a promoção ministerial que homologa o auto de prisão em flagrante e requer a concessão de liberdade provisória ao autuado.
    
    Use o método Chain of Draft (CoD) - analise cada aspecto passo a passo antes de redigir:
    
    {exemplos_texto}
    
    SÍNTESE DO FLAGRANTE PARA ANÁLISE:
    
    SÍNTESE DO FLAGRANTE:
    {manifestacao_base}
    
    ANÁLISE PRÉVIA:
    {analise}
    
    ESTRUTURA DA PROMOÃ‡ÃƒO MINISTERIAL:
    
    1. IDENTIFICAÇÃO PROCESSUAL
    - Identificar o processo e o(s) investigados(s), em linhas distintas;
    - Ex.: "AUTOS nº [resposta_numero_processo]".
    - Ex.: "FLAGRANTEADO(S): [resposta_flagranteados]".
    
    2. ABERTURA DA MANIFESTAÇÃO:
        - Sempre incluir o seguinte parágrafo inicial: "O MINISTÉRIO PÚBLICO DO ESTADO DE MINAS GERAIS, por meio do Promotor de Justiça que esta subscreve, vem, à vista da comunicação do flagrante do autuado, manifestar-se nos seguintes termos:"
    
    3. FUNDAMENTAÇÃO (Use CoD aqui)
        a) Homologação do flagrante delito
        - Analise o cabimento, ou não, da homologação do flagrante delito.
        - Exemplo de cabimento: "Cuida-se da comunicação de prisão em flagrante delito de [resposta_flagranteados] pela prática, no dia [resposta_data_crimes], do(s) delito(s) previsto(s) no(s) art. [resposta_crimes].
        Tendo sido observados pela autoridade policial todos os requisitos legais e encontrando a presente situação arrimo no art. 302, inciso(s) [resposta_incisos_art_302], e 304 do Código de Processo Penal, o Ministério Público manifesta-se pela homologação da prisão em flagrante do autuado." 
        - Exemplo de não cabimento: "Cuida-se da comunicação de prisão em flagrante delito de [resposta_flagranteados] pela prática, no dia [resposta_data_crimes], do(s) delito(s) previsto(s) no(s) art. [resposta_crimes].
        Analisando a situação posta, não se vislumbra o cumprimento, pelas autoridades responsáveis pela condução do autuado em flagrante, de todos os requisitos legais necessários para o reconhecimento de situação de flagrância, haja vista a ausência de quaisquer das hipóteses do art. 302, incisos I a IV, do Código de Processo Penal. 
        Isso porque [explicar a situação que impede a homologação ...]. 
        Pelo exposto, o Ministério Público manifesta-se pela não homologação da prisão em flagrante do autuado."

        b) Concessão de liberdade provisória (com ou sem cautelares)
        - Parta da premissa de que a prisão preventiva não será requerida e demonstre a regularidade do flagrante.
        - Analise a ausência dos requisitos dos arts. 312 e 313 do Código de Processo Penal, evidenciando a inexistência de fumus comissi delicti ou periculum libertatis suficientes para a custódia.
        - Indique, quando adequado, medidas cautelares do art. 319 do CPP que assegurem os fins do processo, justificando a suficiência e proporcionalidade de cada uma.
        - Argumente de forma explícita contra a prisão preventiva, destacando por que seria medida excessiva ou desnecessária no caso concreto.
        - Exemplo 2: "A prisão do(s) autuado(s) foi realizada nos termos legais e já cumpriu suas funções primordiais, quais sejam, evitar que a ação criminosa possa gerar todos os seus efeitos e garantir a qualidade e a idoneidade da prova colhida imediatamente após a prática do delito, restando, agora, analisar a necessidade de sua conversão em prisão preventiva, nos termos do art. 310 do Código de Processo Penal.
    
    	        Neste ponto, entende o Parquet não se fazerem presentes os requisitos e fundamentos da prisão preventiva.

                Isso porque o(s) delito(s) em questão não preenche(m) os requisitos do art. 313, I, do CPP. Ademais, o(s) autuado(s) não é(são) reincidente(s), sendo tecnicamente primário(s), razão pela qual também inexistente o requisito do art. 313, II, do CPP.

                Não obstante, considerando as circunstâncias dos fatos delitivos, praticados após o consumo imoderado de bebidas alcoólicas [colocar motivação para as medidas cautelares diversas da prisão], bem como em respeito aos incisos I e II do caput do art. 282 do CPP, entende o Ministério Público razoável a fixação das medidas cautelares diversas da prisão previstas no art. 319, II e V, do CPP, determinando-se ao autuado a obrigação de não frequentar bares e estabelecimentos congêneres, recolhendo-se à sua residência nos dias de semana das 20h às 06h do dia seguinte, e nos finais de semana, das 15h às 06h do dia seguinte, salvo situações previamente autorizadas por esse Juízo.

                Por todo o exposto, o Ministério Público manifesta-se pela homologação da prisão em flagrante e pela concessão de liberdade provisória ao autuado, cumulada com as medidas cautelares previstas no art. 319, II e V, do CPP, determinando-se ao autuado a obrigação de não frequentar bares e estabelecimentos congêneres, recolhendo-se à sua residência nos dias de semana das 20h às 06h do dia seguinte, e nos finais de semana, das 15h às 06h do dia seguinte, salvo situações previamente autorizadas por esse Juízo."
    4. FECHO
        - Local e data (use a data atual, {datetime.now().strftime("%d de %B de %Y")}). Ex.: Belo Horizonte, 12 de agosto de 2025.
    - Assinatura do Promotor de Justiça

    IMPORTANTE: Use o Chain of Draft (CoD) para cada análise - verifique sistematicamente cada requisito antes de concluir sobre o cabimento ou não da liberdade provisória e das medidas cautelares sugeridas.

    IMPORTANTE: Não escreva um parágrafo específico sobre reincidência ou maus antecedentes criminais. Integre essa avaliação à fundamentação que demonstra a suficiência das medidas diversas da prisão.

    Após analisar, escreva cada item em formato e estilo de peça judicial, sem enumerá-los como tópicos. Não mencione o uso de Chain of Draft (CoD) na análise.
    """
    messages = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': prompt}
    ]
    response = router.chat_completion(messages, temperature=0.3, max_tokens=2048)
    return response.choices[0].message.content.strip()


def gerar_manifestacao_apfd_node(state):
    print("\n[GERANDO MANIFESTAÇÃO APFD]\n")
    manifestacao_base = state.get('manifestacao_base') or state.get('texto_base') or ''
    analise = state.get('analise_antecedentes', {}).get('analise_completa', '')
    print('Escolha qual manifestação deseja gerar:')
    print('1. Homologação com conversão em prisão preventiva')
    print('2. Homologação com concessão de liberdade provisória')
    opcao = input('Opção (1 ou 2): ').strip()
    try:
        if opcao == '1':
            apfd_texto = gerarPromocaoHomologacaoComPreventiva(manifestacao_base, analise)
            state['cenario_apfd'] = 'preventiva'
        elif opcao == '2':
            apfd_texto = gerarPromocaoHomologacaoComLiberdadeProvisoria(manifestacao_base, analise)
            state['cenario_apfd'] = 'liberdade_provisoria'
        else:
            raise ValueError('Opção inválida. Informe 1 ou 2.')
        print('\r\n===== APFD GERADA =====\r\n')
        display(Markdown(apfd_texto))
        state['manifestacao_apfd'] = apfd_texto
    except Exception as e:
        print(f'ERRO: {e}')
        state['manifestacao_apfd'] = 'Erro na geração da APFD'
    return state
def fim_node(state):
    print("\n === PROCESSAMENTO CONCLUÍDO ===")
    print(f"Status final: {router.get_status()}")
    return state
# ===== CONSTRUCAO DO GRAFO =====
def build_graph():
    workflow = StateGraph(state_schema=EstadoAPFD)
    
    workflow.add_node("upload", upload_node_files_only)
    workflow.add_node("gerar_texto_base", gerar_texto_base_node)
    workflow.add_node("analisar_antecedentes", analisar_antecedentes_node)
    workflow.add_node("gerar_manifestacao_apfd", gerar_manifestacao_apfd_node)
    workflow.add_node("fim", fim_node)
    
    workflow.set_entry_point("upload")
    workflow.add_edge("upload", "gerar_texto_base")
    workflow.add_edge("gerar_texto_base", "analisar_antecedentes")
    workflow.add_edge("analisar_antecedentes", "gerar_manifestacao_apfd")
    workflow.add_edge("gerar_manifestacao_apfd", "fim")
    
    return workflow.compile()

# ===== FUNCAO PARA SALVAR RESULTADOS =====
def salvar_resultados(result):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if result.get("manifestacao_apfd"):
        with open(f"apfd_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(result["manifestacao_apfd"])
        print(f"APFD salvo: apfd_{timestamp}.txt")
    
    if result.get("analise_antecedentes"):
        with open(f"analise_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(result["analise_antecedentes"].get("analise_completa", ""))
        print(f"Análise salva: analise_{timestamp}.txt")

# ===== FUNCAO PRINCIPAL =====
def main():
    print("=== SISTEMA DE GERACAO DE APFD - MPMG ===")
    print("Sistema para gerar manifestacoes APFD\n")
    
    if not (AZURE_OPENAI_API_KEY or GOOGLE_API_KEY):
        print("ERRO: Configure ao menos uma API (Azure ou Google)")
        print("Crie um arquivo .env com:")
        print("AZURE_OPENAI_API_KEY=sua_chave")
        print("GOOGLE_API_KEY=sua_chave")
        return None
    
    try:
        graph = build_graph()
        result = graph.invoke({})
        
        print("\n=== OPCOES FINAIS ===")
        if input("Deseja salvar os resultados? (s/n): ").lower() == 's':
            salvar_resultados(result)
        
        return result
        
    except KeyboardInterrupt:
        print("\nProcesso interrompido")
        return None
    except Exception as e:
        print(f"\nERRO: {e}")
        return None

if __name__ == "__main__":
    result = main()
    print("\nSistema finalizado!")

