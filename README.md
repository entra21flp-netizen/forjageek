# ForjaGeek

Plataforma Django para colecionadores cadastrarem peças, organizarem estantes virtuais, criarem dioramas e negociarem itens com a comunidade.

## Funcionalidades

- Cadastro de modelos e unidades de colecionáveis;
- Busca de produto por código de barras EAN, JAN ou UPC;
- Página de Exibição com pesquisa e filtros;
- Estantes públicas ou privadas, com organização por arrastar e soltar;
- Dioramas predefinidos e personalizados;
- Mercado, carrinho, Wishlist e conversas;
- Histórico de vendas e avaliações;
- Autenticação, recuperação de conta e verificação de WhatsApp.

## Estrutura de dados

O projeto mantém os nomes organizados das tabelas de catálogo:

- `tipos_colecionaveis`
- `modelos_colecionaveis`
- `imagens_modelos`
- `caracteristicas`
- `tipos_caracteristicas`
- `modelos_caracteristicas`
- `dioramas_padrao` — cenários oferecidos pelo site
- `dioramas_ia` — dioramas confirmados pelos usuários

As migrações são a fonte oficial da estrutura. Para criar um banco vazio com o esquema atual, execute:

```bash
python manage.py migrate
```

Esse comando cria somente as tabelas definidas pelos aplicativos e pelas dependências do Django. Não use comandos SQL manuais para criar tabelas paralelas.

## Configuração local

Requer Python 3.12.

```bash
python -m venv .venv
```

No Windows:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Para usar SQLite localmente, configure no `.env`:

```env
SECRET_KEY=uma-chave-local
DEBUG=True
FORJAGEEK_USE_SQLITE=true
ALLOWED_HOSTS=localhost,127.0.0.1
```

Depois execute:

```bash
python manage.py migrate
python manage.py runserver
```

O site estará disponível em `http://127.0.0.1:8000/`.

## Neon/PostgreSQL

Para usar o banco do Neon, mantenha `FORJAGEEK_USE_SQLITE=false` e informe a conexão apenas no `.env` do servidor:

```env
NEON_DATABASE_URL=postgresql://usuario:senha@servidor/banco?sslmode=require
FORJAGEEK_USE_SQLITE=false
```

Nunca envie o `.env`, senhas ou URLs reais de conexão para o GitHub.

## Consulta por código de barras

No cadastro de colecionável, a busca consulta primeiro os modelos já existentes no ForjaGeek. Se o código ainda não estiver no catálogo, o servidor consulta a UPCitemdb e sugere os dados encontrados para revisão do usuário. A consulta não grava um novo modelo automaticamente.

Sem configuração adicional, o projeto usa o acesso de teste da UPCitemdb, sujeito a um limite baixo de consultas. Para uso contínuo em produção, contrate uma chave no provedor e configure somente no `.env` do servidor:

```env
UPCITEMDB_USER_KEY=sua-chave
```

## Imagens e arquivos de mídia

Arquivos dentro de `static/` pertencem ao projeto e são enviados ao GitHub. Isso inclui logotipos, estilos, scripts e os cenários predefinidos dos dioramas.

Fotos enviadas pelos usuários e dioramas gerados ficam em `media/`. Essa pasta não é versionada e deve permanecer em armazenamento persistente no servidor. No `docker-compose.yml`, ela está montada em `/var/www/forjageek/media`.

As imagens cadastradas por URL ficam registradas no banco e são carregadas diretamente da origem externa.

## Implantação com Docker

O serviço executa automaticamente, nesta ordem:

1. `python manage.py migrate`
2. `python manage.py collectstatic --noinput`
3. Gunicorn na porta 8000

Antes de iniciar, configure no servidor:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `NEON_DATABASE_URL`
- credenciais dos serviços opcionais usados pelo projeto

As pastas persistentes configuradas são:

- `/var/www/forjageek/static`
- `/var/www/forjageek/media`

## Verificações antes do envio

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test
git diff --check
```

O banco SQLite local, os backups, o `.env`, a mídia de usuários, os arquivos estáticos coletados e o modelo local de recorte de fundo estão ignorados pelo Git.
