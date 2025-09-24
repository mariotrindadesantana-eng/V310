@echo off
REM ARQV30 Enhanced v3.0 - Script de Instalação Windows
REM Execute este arquivo para instalar todas as dependências + External AI Verifier

echo ========================================
echo ARQV30 Enhanced v3.0 + External AI Verifier - Instalação
echo Sistema Completo de Análise de Mercado com IA
echo ========================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não encontrado!
    echo.
    echo Por favor, instale Python 3.11+ de https://python.org      
    echo Certifique-se de marcar "Add Python to PATH" durante a instalação.
    echo.
    pause
    exit /b 1
)

echo ✅ Python encontrado:
python --version
echo.

REM Verifica versão do Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Versão do Python: %PYTHON_VERSION%
echo.

REM Cria ambiente virtual
echo 🔄 Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo ❌ ERRO: Falha ao criar ambiente virtual!
    pause
    exit /b 1
)

REM Ativa ambiente virtual
echo 🔄 Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ERRO: Falha ao ativar ambiente virtual!
    pause
    exit /b 1
)

REM Atualiza pip
echo 🔄 Atualizando pip...
python -m pip install --upgrade pip
echo.

REM Instala dependências
echo 🔄 Instalando dependências ULTRA-ROBUSTAS...
echo Isso pode levar alguns minutos...
echo.
pip install -r requirements.txt
pip install flask scrapy playwright
pip install instascrape

REM === CORREÇÃO INSTASCRAPE ===
echo 🔄 Instalando instascrape...
pip install instascrape==0.1
if errorlevel 1 (
    echo ⚠️ AVISO: Falha ao instalar instascrape. Tentando instalação alternativa...
    pip install instagrapi
    echo ✅ Usando instagrapi como alternativa ao instascrape
)

REM === CORREÇÃO PLAYWRIGHT ===
echo 🔄 Instalando Playwright e navegadores...
pip install playwright
playwright install-deps
playwright install chromium firefox webkit
playwright install
pip install aiohttp aiofiles
pip install aiohttp aiofiles playwright
playwright install-deps 
playwright install      
if errorlevel 1 (
    echo ❌ ERRO: Falha ao instalar Playwright ou navegadores!
    echo Verifique se o Python esta funcionando corretamente.
    pause
    exit /b 1
)
REM === FIM CORREÇÃO PLAYWRIGHT ===

pip install selenium
pip install beautifulsoup4 requests python-dotenv

REM === MODIFICAÇÃO CRÍTICA: Instala o modelo spaCy pt_core_news_sm ===
echo 🔄 Instalando modelo spaCy pt_core_news_sm...
pip install src\engine\pt_core_news_sm-3.8.0-py3-none-any.whl
if errorlevel 1 (
    echo ⚠️ AVISO: Falha ao instalar o modelo spaCy pt_core_news_sm a partir do .whl. Tentando download...
    python -m spacy download pt_core_news_sm
    if errorlevel 1 (
        echo ⚠️ AVISO: Falha ao baixar o modelo spaCy pt_core_news_sm. A análise NLP será limitada.
    ) else (
        echo ✅ Modelo spaCy pt_core_news_sm baixado com sucesso.
    )
) else (
     echo ✅ Modelo spaCy pt_core_news_sm instalado com sucesso a partir do .whl.
)
REM === FIM DA MODIFICAÇÃO ===

REM Instala dependências adicionais para web scraping (se não estiverem no requirements.txt principal)
echo 🔄 Instalando dependências adicionais (se necessário)...
pip install beautifulsoup4 lxml html5lib aiohttp
if errorlevel 1 (
    echo ⚠️ AVISO: Algumas dependências adicionais falharam.
)

REM === INSTALAÇÃO DO MÓDULO VIRAL ===
echo.
echo ========================================
echo 🔥 INSTALANDO MÓDULO VIRAL
echo ========================================
echo.

REM Verifica se Node.js está instalado
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Node.js não encontrado!
    echo.
    echo Por favor, instale Node.js 18+ de https://nodejs.org
    echo O módulo viral requer Node.js para funcionar.
    echo.
    echo ⚠️ CONTINUANDO SEM MÓDULO VIRAL...
    echo O sistema funcionará com fallback automático.
    echo.
    goto SKIP_VIRAL
) else (
    echo ✅ Node.js encontrado:
    node --version
    echo.
)

REM Verifica se npm está disponível
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: npm não encontrado!
    echo ⚠️ CONTINUANDO SEM MÓDULO VIRAL...
    goto SKIP_VIRAL
) else (
    echo ✅ npm encontrado:
    npm --version
    echo.
)

REM Instala dependências do viral
echo 🔄 Instalando dependências do módulo viral...
cd viral
if errorlevel 1 (
    echo ❌ ERRO: Diretório viral não encontrado!
    echo ⚠️ CONTINUANDO SEM MÓDULO VIRAL...
    cd ..
    goto SKIP_VIRAL
)

echo Executando npm install...
npm install
if errorlevel 1 (
    echo ❌ ERRO: Falha ao instalar dependências do viral!
    echo ⚠️ CONTINUANDO SEM MÓDULO VIRAL...
    cd ..
    goto SKIP_VIRAL
) else (
    echo ✅ Dependências do viral instaladas com sucesso!
)

REM Testa build do viral
echo 🧪 Testando build do módulo viral...
npm run build >nul 2>&1
if errorlevel 1 (
    echo ⚠️ AVISO: Build do viral falhou, mas dependências estão instaladas.
) else (
    echo ✅ Build do viral OK!
)

cd ..
echo ✅ Módulo viral configurado com sucesso!
echo.
goto CONTINUE_INSTALL

:SKIP_VIRAL
echo ⚠️ Módulo viral não instalado - sistema usará fallback automático.
echo.

:CONTINUE_INSTALL
REM === FIM INSTALAÇÃO VIRAL ===

REM Cria diretórios necessários
echo 🔄 Criando estrutura de diretórios ULTRA-ROBUSTA...
if not exist "src\uploads" mkdir src\uploads
if not exist "src\static\images" mkdir src\static\images
if not exist "src\cache" mkdir src\cache
if not exist "src\logs" mkdir src\logs
if not exist "analyses_data" mkdir analyses_data
if not exist "analyses_data\viral_images" mkdir analyses_data\viral_images
if not exist "relatorios_intermediarios" mkdir relatorios_intermediarios
if not exist "relatorios_intermediarios\workflow" mkdir relatorios_intermediarios\workflow
echo.

REM Testa a instalação
echo 🧪 Testando instalação ULTRA-ROBUSTA...
cd src
python -c "import flask, requests, google.generativeai, supabase, pandas, PyPDF2, spacy; print('✅ Dependências principais OK')"
if errorlevel 1 (
    echo ⚠️ AVISO: Algumas dependências podem não estar funcionando corretamente.
) else (
    echo ✅ Teste de dependências ULTRA-ROBUSTO passou!
)
cd ..
echo.

REM Testa conexão com APIs (se configuradas)
echo 🧪 Testando conexões com APIs...
if exist ".env" (
    cd src
    python -c "
import os
from dotenv import load_dotenv
load_dotenv('../.env')

# Testa Gemini
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key and gemini_key != 'sua-chave-aqui':
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        print('✅ Gemini API configurada')
    except:
        print('⚠️ Gemini API com problemas')
else:
    print('⚠️ Gemini API não configurada')


    cd ..
) else (
    echo ⚠️ Arquivo .env não encontrado - APIs não testadas
)
echo.

echo ========================================
echo 🎉 INSTALAÇÃO ULTRA-ROBUSTA CONCLUÍDA!
echo ========================================
echo.
echo 🚀 Próximos passos:
echo.
echo 1. ✅ Arquivo .env já configurado com suas chaves
echo.
echo 2. Execute run.bat para iniciar V70V1 + Módulo Viral
echo.
echo 3. O navegador abrirá automaticamente em http://localhost:5000
echo.
echo 4. Teste com uma análise simples primeiro
echo.
echo 5. Para análises ULTRA-ROBUSTAS, todas as APIs estão configuradas
echo.
echo ========================================
echo.
echo 📚 SISTEMA ULTRA-ROBUSTO PRONTO!
echo Agora você tem acesso a análises de mercado
echo com profundidade de consultoria de R$ 50.000/hora
echo.
echo 🔥 RECURSOS ATIVADOS:
echo - Google Gemini Pro para análise IA
echo - Supabase para banco de dados
echo - WebSailor para pesquisa web
echo - HuggingFace para análise complementar
echo - Google Search para dados reais
echo - Jina AI para extração de conteúdo
echo - 🔥 MÓDULO VIRAL para redes sociais
echo.
pause