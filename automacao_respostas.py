import subprocess
import sys
import os
import importlib.util

# --- INSTALAÇÃO AUTOMÁTICA DE DEPENDÊNCIAS ---
# Mapa: nome do pacote pip -> nome do módulo para checar
PACOTES_NECESSARIOS = {
    "opencv-python": "cv2",   # necessário para o parâmetro confidence do locateOnScreen
    "pillow": "PIL",          # abre as imagens de referência de forma tolerante
    "numpy": "numpy",         # conversão de imagem para o formato esperado pelo pyscreeze
    "pyautogui": "pyautogui",
    "pyperclip": "pyperclip",
    "keyboard": "keyboard",
    "pytesseract": "pytesseract",  # OCR do texto do comentário (exige o motor Tesseract instalado à parte, ver comentário abaixo)
}
# Ordem importa: cv2/PIL são checados ANTES de pyautogui, pois importar o
# pyautogui carrega o pyscreeze, que detecta a presença do OpenCV nesse
# instante e guarda o resultado em cache — se isso acontecer antes de o
# OpenCV estar instalado, o cache fica errado pelo resto da execução.


def garantir_dependencias():
    faltando = []
    for pacote_pip, modulo in PACOTES_NECESSARIOS.items():
        # find_spec só verifica se o módulo existe, sem importá-lo de fato —
        # assim não disparamos nenhum efeito colateral de import antes da hora
        if importlib.util.find_spec(modulo) is None:
            faltando.append(pacote_pip)

    if faltando:
        print(f"Instalando dependências ausentes: {', '.join(faltando)}...")
        for pacote_pip in faltando:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pacote_pip])
        print("Dependências instaladas com sucesso.\n")
    else:
        print("Todas as dependências já estão instaladas.\n")


garantir_dependencias()

import pyautogui
import time
import pyperclip
import keyboard
import numpy as np
import random
import pytesseract
from PIL import Image

# --- OCR (Tesseract) ---
# pytesseract é só um "wrapper" em Python; o motor de OCR de verdade
# (Tesseract-OCR) precisa estar instalado separadamente no Windows.
# Baixe em: https://github.com/UB-Mannheim/tesseract/wiki (marque o pacote
# de idioma Portuguese na instalação) e ajuste o caminho abaixo se necessário.
# Caminho do tesseract.exe: usa a variável de ambiente TESSERACT_CMD, se existir;
# senão tenta os locais padrão de instalação no Windows.
_CANDIDATOS_TESSERACT = [
    os.environ.get("TESSERACT_CMD", ""),
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
]
for _c in _CANDIDATOS_TESSERACT:
    if _c and os.path.exists(_c):
        pytesseract.pytesseract.tesseract_cmd = _c
        break

# --- CONFIGURAÇÕES DE SEGURANÇA ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# --- IMAGENS DE REFERÊNCIA (capture estes recortes de tela e salve com estes nomes) ---
# placeholder_resposta.png -> recorte do texto cinza "Escreva sua resposta" dentro da caixa vazia
# botao_responder.png      -> recorte do botão verde "Responder"
# Os caminhos são resolvidos a partir da pasta do PRÓPRIO SCRIPT, não da pasta
# onde o terminal foi aberto — assim funciona não importa de onde você execute.
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PLACEHOLDER = os.path.join(PASTA_SCRIPT, "placeholder_resposta.png")
CAMINHO_BOTAO = os.path.join(PASTA_SCRIPT, "botao_responder.png")
CAMINHO_CARREGAR_MAIS = os.path.join(PASTA_SCRIPT, "carregar_mais.png")
CAMINHO_BADGE_NOVO = os.path.join(PASTA_SCRIPT, "badge_novo.png")
CAMINHO_BADGE_LIDO = os.path.join(PASTA_SCRIPT, "badge_lido.png")
CAMINHO_BUSCAR_AGORA = os.path.join(PASTA_SCRIPT, "buscar_agora.png")
CAMINHO_NOTA_5 = os.path.join(PASTA_SCRIPT, "nota_5.png")
CAMINHO_SEM_COMENTARIO = os.path.join(PASTA_SCRIPT, "sem_comentario.png")
CAMINHO_FECHAR = os.path.join(PASTA_SCRIPT, "fechar.png")


def carregar_imagem_referencia(caminho):
    """Abre a imagem com Pillow (mais tolerante a variações de PNG do que o
    decoder do OpenCV) e converte para o array BGR que o pyautogui/pyscreeze
    espera internamente. Evita o erro 'can't open/read file' do cv2.imread
    quando o PNG foi salvo por ferramentas como Paint/Snipping Tool."""
    try:
        img_pil = Image.open(caminho).convert("RGB")
    except Exception as e:
        raise SystemExit(
            f"Não consegui abrir a imagem de referência '{caminho}'.\n"
            f"Verifique se o arquivo existe e é um PNG válido (reabra e salve de novo "
            f"se necessário). Erro original: {e}"
        )
    arr_rgb = np.array(img_pil)
    arr_bgr = arr_rgb[:, :, ::-1].copy()  # Pillow usa RGB, OpenCV/pyscreeze usa BGR
    return arr_bgr


# Carregadas UMA vez no início — já como array, então o cv2.imread problemático
# nunca é chamado durante a execução
IMG_PLACEHOLDER = carregar_imagem_referencia(CAMINHO_PLACEHOLDER)
IMG_BOTAO = carregar_imagem_referencia(CAMINHO_BOTAO)
IMG_CARREGAR_MAIS = carregar_imagem_referencia(CAMINHO_CARREGAR_MAIS)
IMG_BADGE_NOVO = carregar_imagem_referencia(CAMINHO_BADGE_NOVO)
IMG_BADGE_LIDO = carregar_imagem_referencia(CAMINHO_BADGE_LIDO)
IMG_BUSCAR_AGORA = carregar_imagem_referencia(CAMINHO_BUSCAR_AGORA)
IMG_NOTA_5 = carregar_imagem_referencia(CAMINHO_NOTA_5)
IMG_SEM_COMENTARIO = carregar_imagem_referencia(CAMINHO_SEM_COMENTARIO)
IMG_FECHAR = carregar_imagem_referencia(CAMINHO_FECHAR)

CONFIDENCE = 0.8          # baixe para 0.7 se o locate estiver falhando por antialiasing
TIMEOUT_BUSCA = 3         # segundos tentando localizar o elemento antes de desistir
MAX_TENTATIVAS_PULO = 8   # quantas avaliações seguidas ele pode pular procurando uma não respondida
SCROLL_POR_AVANCO = -200  # quanto rolar a lista quando não há "Novo"/"Lido" visível

X3, Y3 = 332, 302         # Barra lateral (lista de nomes) — isso pode continuar fixo,
                          # pois é a lista que não muda de posição, só o conteúdo dela

# Região de leitura da avaliação (nota + comentário). A altura é calculada
# DINAMICAMENTE a cada review — do link "Fechar" (topo do painel de detalhe)
# até a caixa de resposta — em vez de um valor fixo, porque: (1) comentários
# curtos e longos têm alturas bem diferentes, e (2) o painel da direita pode
# manter rolagem de uma avaliação pra outra, então nem o topo é garantido
# estar sempre no mesmo Y da tela. Localizar "Fechar" a cada vez resolve os
# dois problemas de uma vez.
REGIAO_LARGURA_CARD = 680      # largura do card de comentário, a partir do X do placeholder
MARGEM_INFERIOR_CARD = 55      # espaço a não incluir logo acima do placeholder (evita pegar "Resposta"/a linha da nota)
MARGEM_SUPERIOR_CARD = 45      # espaço a pular logo abaixo do "Fechar" (evita pegar título/selo)
MARGEM_ESQUERDA_TEXTO = 130    # folga à esquerda do X do placeholder (ele marca o CENTRO do texto "Escreva sua resposta", não a borda — folga maior evita cortar início das linhas do comentário)
ALTURA_MINIMA_REGIAO = 60      # nunca busca numa região menor que isso
Y_TOPO_CARD_FALLBACK = 300     # usado só se o "Fechar" não for encontrado (rede lenta, etc.)

# --- TEMPLATES DE RESPOSTA POR CATEGORIA ---
# Várias opções por categoria — o script sorteia uma a cada resposta, pra não
# repetir sempre a mesma frase.
RESPOSTAS = {
    "sem_comentario": [
        "Olá! Muito obrigado pela avaliação. Ficamos felizes que você tenha gostado da compra. Conte sempre com a gente!",
        "Olá! Obrigado pela sua avaliação. Ficamos felizes que tenha tido uma boa experiência com a compra. Até a próxima!",
    ],
    "produto": [
        "Olá! Agradecemos por avaliar sua compra. Ficamos muito felizes que o produto tenha te agradado — que ele te acompanhe em muitos passos! Volte sempre.",
        "Olá! Que bom saber que você gostou do produto escolhido! Agradecemos a avaliação e esperamos que ele te acompanhe por muito tempo.",
    ],
    "atendimento": [
        "Olá! Ficamos muito felizes com seu elogio ao nosso atendimento — vamos repassar seu feedback para a equipe! Agradecemos a confiança e esperamos te ver novamente em breve.",
        "Olá! Agradecemos muito pelo carinho com o nosso time de atendimento. Isso nos motiva a continuar melhorando cada vez mais. Volte sempre!",
    ],
    "detalhado": [
        "Olá! Ficamos muito felizes em saber que sua experiência foi positiva! Agradecemos por compartilhar sua avaliação com tantos detalhes — esse tipo de feedback é muito importante para continuarmos aprimorando nossa experiência de compra e atendimento. Obrigado por confiar em nós, esperamos te ver novamente em breve!",
        "Olá! Muito obrigado pelo relato detalhado da sua experiência. Nós acompanhamos de perto os comentários dos nossos clientes, e o seu ajuda a orientar melhorias reais. Agradecemos a confiança!",
    ],
    "ressalva": [
        "Olá! Agradecemos sua avaliação e ficamos felizes que, no geral, a experiência tenha sido positiva. Também levamos a sério o ponto que você trouxe, e vamos usá-lo para melhorar ainda mais. Obrigado pela confiança!",
        "Olá! Muito obrigado pelo feedback sincero. Ficamos felizes com a nota, e o ponto de melhoria que você apontou é muito valioso para nós — vamos repassar para a equipe responsável. Conte sempre com a gente!",
    ],
}

PALAVRAS_ATENDIMENTO = ["atendimento", "vendedor", "vendedora", "atendente", "equipe", "funcionári"]
PALAVRAS_RESSALVA = [" mas ", " porém", " só que", "poderia ser", "poderia melhorar", "faltou", "demorou"]
LIMITE_DETALHADO_PALAVRAS = 25  # nº de palavras — mais resistente a ruído de OCR do que contar caracteres


def localizar(imagem, timeout=TIMEOUT_BUSCA, confidence=CONFIDENCE):
    """Tenta localizar uma imagem na tela por até `timeout` segundos.
    Retorna o centro (x, y) ou None se não encontrar."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            pos = pyautogui.locateCenterOnScreen(imagem, confidence=confidence)
            if pos:
                return pos
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    return None


def rolar_lista():
    """Rola a lista da barra lateral (sem clicar) para trazer mais itens à vista."""
    pyautogui.moveTo(X3, Y3)
    time.sleep(0.2)
    pyautogui.scroll(SCROLL_POR_AVANCO, x=X3, y=Y3)
    time.sleep(0.6)


def verificar_e_carregar_mais():
    """Verifica se o botão 'Carregar mais' está visível (fim do lote atual da
    lista) e clica nele se estiver. Usa timeout curto pois essa checagem roda
    a cada tentativa."""
    pos_carregar = localizar(IMG_CARREGAR_MAIS, timeout=1)
    if pos_carregar:
        print("  → Fim do lote carregado. Clicando em 'Carregar mais'...")
        pyautogui.click(pos_carregar.x, pos_carregar.y)
        time.sleep(2.5)  # tempo para o novo lote carregar
        return True
    return False


def localizar_badge_pendente():
    """Procura na tela um selo 'Novo' ou 'Lido' (avaliação pendente de resposta).
    Ignora 'Respondido' por completo, pois não há template para ele — só clicamos
    no que precisa de resposta. Retorna a posição do selo encontrado, ou None."""
    pos = localizar(IMG_BADGE_NOVO, timeout=1)
    if pos:
        return pos
    pos = localizar(IMG_BADGE_LIDO, timeout=1)
    if pos:
        return pos
    return None


def clicar_buscar_agora():
    """Sobe a lista AOS POUCOS, checando a cada passo se o botão 'Buscar agora'
    já apareceu — o painel de filtros pode estar colapsado ou expandido
    ('Mais filtros' aberto), então a distância até o topo varia, e subir um
    número fixo de vezes não é confiável. Ao final (achando o botão ou não),
    desce a lista de volta pela mesma quantidade de passos, para não deixar a
    barra de rolagem largada no topo."""
    print("  → Tentando 'Buscar agora' para recarregar a lista...")
    passos_subidos = 0
    pos = None

    for _ in range(10):
        pyautogui.moveTo(X3, Y3)
        pyautogui.scroll(300, x=X3, y=Y3)  # positivo = sobe
        passos_subidos += 1
        time.sleep(0.4)
        pos = localizar(IMG_BUSCAR_AGORA, timeout=1)
        if pos:
            break
    else:
        pos = None  # esgotou os 10 passos sem achar

    encontrado = pos is not None
    if encontrado:
        pyautogui.click(pos.x, pos.y)
        time.sleep(2.5)
    else:
        print("  → Não encontrei o botão 'Buscar agora' na tela.")

    # Desce de volta, restaurando a lista para perto de onde estava antes de subir
    for _ in range(passos_subidos):
        pyautogui.moveTo(X3, Y3)
        pyautogui.scroll(-300, x=X3, y=Y3)
        time.sleep(0.2)

    return encontrado


def encontrar_avaliacao_nao_respondida():
    """Procura na tela um card com selo 'Novo' ou 'Lido' e clica nele para
    selecioná-lo. Se só houver 'Respondido' visível (nenhum selo pendente
    encontrado), rola a lista e tenta de novo, até MAX_TENTATIVAS_PULO vezes.
    Retorna (posição_do_placeholder, quantidade_de_rolagens); posição vem
    None se esgotar as tentativas."""
    for tentativa in range(1, MAX_TENTATIVAS_PULO + 1):
        pos_badge = localizar_badge_pendente()

        if pos_badge:
            pyautogui.click(pos_badge.x, pos_badge.y)
            time.sleep(1.2)
            pos_placeholder = localizar(IMG_PLACEHOLDER)
            if pos_placeholder:
                return pos_placeholder, tentativa - 1
            # Clicou mas a caixa de resposta não apareceu (raro) — tenta de novo

        print(f"  → Nenhuma pendente visível (tentativa {tentativa}/{MAX_TENTATIVAS_PULO}). Rolando lista...")
        if keyboard.is_pressed('esc'):
            return None, tentativa - 1

        verificar_e_carregar_mais()
        rolar_lista()

    print("  → Limite de rolagens atingido sem achar avaliação pendente.")
    return None, MAX_TENTATIVAS_PULO


def calcular_regiao_avaliacao(pos_placeholder):
    """Calcula o retângulo (x, y, largura, altura) do card de avaliação.
    TOPO vem do 'Fechar' (cabeçalho do painel), localizado a cada vez — não
    fixamos um Y calibrado, porque o painel pode manter rolagem de uma
    avaliação pra outra. BORDA ESQUERDA vem do X do próprio placeholder,
    com folga. LARGURA é um valor fixo curto (REGIAO_LARGURA_CARD): usar o
    X do 'Fechar' como borda direita foi tentado e vazou pro card de dados
    do cliente ao lado (Fechar fica no topo da página inteira, mais à
    direita que esse card) — confirmado em teste real. ALTURA é dinâmica:
    distância real entre o 'Fechar' e a caixa de resposta.
    Força tudo para int nativo do Python — coordenadas vindas do
    locateCenterOnScreen às vezes chegam como numpy.int64, e o
    pyautogui.screenshot no Windows exige int puro em region."""
    pos_fechar = localizar(IMG_FECHAR, timeout=1)
    y0 = int(pos_fechar.y) + MARGEM_SUPERIOR_CARD if pos_fechar else Y_TOPO_CARD_FALLBACK

    x0 = max(0, int(pos_placeholder.x) - MARGEM_ESQUERDA_TEXTO)
    altura = max(ALTURA_MINIMA_REGIAO, int(pos_placeholder.y) - y0 - MARGEM_INFERIOR_CARD)
    return (int(x0), int(y0), int(REGIAO_LARGURA_CARD), int(altura))


def extrair_estrelas_e_texto(pos_placeholder):
    """Verifica se a nota é 5 estrelas (comparando o bloco 'N★' inteiro contra
    a tela — o site mostra número+ícone juntos, não 5 ícones separados) e lê
    o texto do comentário (via OCR, só quando não for 'sem comentário') dentro
    da região do card de avaliação atual."""
    regiao = calcular_regiao_avaliacao(pos_placeholder)

    try:
        pos_nota_5 = pyautogui.locateOnScreen(IMG_NOTA_5, region=regiao, confidence=CONFIDENCE)
    except Exception:
        pos_nota_5 = None
    e_nota_5 = pos_nota_5 is not None

    pos_sem_comentario = None
    try:
        pos_sem_comentario = pyautogui.locateOnScreen(IMG_SEM_COMENTARIO, region=regiao, confidence=CONFIDENCE)
    except Exception:
        pass

    texto_comentario = ""
    if pos_sem_comentario is None:
        screenshot = pyautogui.screenshot(region=regiao)
        try:
            texto_bruto = pytesseract.image_to_string(screenshot, lang="por")
            # Limpa ruído comum de OCR: linhas em branco, espaços duplicados
            texto_comentario = " ".join(texto_bruto.split())
        except Exception as e:
            print(f"  → OCR falhou ({e}). Tratando como sem comentário classificável.")

    return e_nota_5, texto_comentario


def classificar_review(e_nota_5, texto_comentario):
    """Decide a categoria de resposta, ou 'manual' se a nota não for 5
    estrelas — nesse caso o script NÃO responde, deixando para tratativa
    individual, como combinado com a gestão."""
    if not e_nota_5:
        return "manual"

    texto_lower = texto_comentario.lower()
    if not texto_lower:
        return "sem_comentario"

    if any(p in texto_lower for p in PALAVRAS_ATENDIMENTO):
        return "atendimento"

    if any(p in texto_lower for p in PALAVRAS_RESSALVA):
        return "ressalva"

    if len(texto_comentario.split()) > LIMITE_DETALHADO_PALAVRAS:
        return "detalhado"

    return "produto"


def rodar_automacao():
    print("\n--- SCRIPT ATIVO ---")
    try:
        num_input = input("Quantas avaliações deseja processar? ")
        NUMERO_DE_AVALIACOES = int(num_input)
    except ValueError:
        NUMERO_DE_AVALIACOES = 1

    print("Iniciando em 5 segundos... Prepare a tela!")
    time.sleep(5)

    respondidas = 0
    puladas = 0
    manual = 0

    i = 0
    while i < NUMERO_DE_AVALIACOES:
        if keyboard.is_pressed('esc'):
            print("\n[!] Parando...")
            break

        try:
            print(f"Processando ciclo {i + 1} de {NUMERO_DE_AVALIACOES}...")

            # 1. Procurar uma avaliação sem resposta, pulando automaticamente as que já têm
            pos_placeholder, qtd_pulada = encontrar_avaliacao_nao_respondida()
            puladas += qtd_pulada

            if pos_placeholder is None:
                # Antes de desistir de vez: clica em "Buscar agora" pra recarregar
                # a lista e tenta achar uma pendente mais uma vez.
                if clicar_buscar_agora():
                    pos_placeholder, qtd_pulada = encontrar_avaliacao_nao_respondida()
                    puladas += qtd_pulada

            if pos_placeholder is None:
                print("  → Nenhuma avaliação pendente encontrada, mesmo após 'Buscar agora'. Encerrando.")
                break

            # 1.5 Ler nota + comentário e decidir a categoria de resposta
            e_nota_5, texto_comentario = extrair_estrelas_e_texto(pos_placeholder)
            categoria = classificar_review(e_nota_5, texto_comentario)

            if categoria == "manual":
                print("  → Nota diferente de 5★ (ou não identificada) — fora do escopo automático. Deixando para tratativa individual.")
                manual += 1
                rolar_lista()  # se afasta do card para não ficar reprocessando ele
                continue  # não conta como ciclo (não incrementa i)

            texto_escolhido = random.choice(RESPOSTAS[categoria])
            print(f"  → Categoria: {categoria} (5★)")
            if texto_comentario:
                print(f"  → OCR leu: \"{texto_comentario[:150]}\"")

            # 2. Clicar exatamente onde a caixa de texto está AGORA (posição dinâmica)
            pyautogui.click(pos_placeholder.x, pos_placeholder.y, clicks=2)
            time.sleep(0.5)
            pyperclip.copy(texto_escolhido)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)

            # 3. Localizar e clicar no botão "Responder" dinamicamente
            pos_botao = localizar(IMG_BOTAO)
            if pos_botao:
                pyautogui.click(pos_botao.x, pos_botao.y)
                respondidas += 1
            else:
                # fallback: tenta TAB + ENTER se o botão não foi localizado
                print("  → Botão não localizado por imagem, usando fallback TAB+ENTER.")
                pyautogui.press('tab')
                time.sleep(0.3)
                pyautogui.press('enter')
                respondidas += 1

            # 4. Aguardar o envio processar
            time.sleep(3.5)

            if keyboard.is_pressed('esc'):
                break

            # 5. Rola um pouco a lista para se afastar do card recém-respondido —
            #    evita reencontrá-lo caso o selo demore a atualizar de Novo/Lido
            #    para Respondido. A busca do próximo ainda é feita do zero no
            #    próximo ciclo (por selo, não por posição).
            rolar_lista()
            print(f"✔ Ciclo {i + 1} concluído.")
            i += 1

        except pyautogui.FailSafeException:
            # Mouse foi para o canto da tela (bloqueio de tela, notificação, etc.)
            # Em vez de encerrar e perder o progresso, pausa e espera você resolver.
            print("\n[!] O mouse foi para o canto da tela (fail-safe do pyautogui disparou).")
            print("    Isso costuma acontecer por bloqueio de tela/proteção de tela do Windows.")
            input("    Resolva o que interrompeu (ex: desbloqueie a tela) e pressione ENTER para continuar de onde parou...")
            continue  # repete o MESMO i, sem incrementar

    print(f"\n--- Automação finalizada! Respondidas: {respondidas} | Puladas (já tinham resposta): {puladas} | Deixadas para tratativa manual: {manual} ---")


if __name__ == "__main__":
    print("1 - Calibrar / 2 - Iniciar")
    escolha = input("Opção: ").strip()

    if escolha == "1":
        print("Mova o mouse e pressione CTRL+C para capturar.")
        try:
            while True:
                print(f"X={pyautogui.position().x}, Y={pyautogui.position().y}", end="\r")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\nCapturado: {pyautogui.position()}")
    elif escolha == "2":
        rodar_automacao()
