# ForjaGeek — projeto Django

Recriação do banco de dados que você desenhou, agora como um projeto Django
de verdade (models + admin), testado ponta a ponta neste ambiente antes de
te entregar.

## Estrutura

```
forjageek_django/
├── manage.py
├── requirements.txt
├── forjageek/          # configuração do projeto (settings, urls raiz)
├── usuarios/           # Usuario (autenticação)
├── catalogo/           # TipoColecionavel, ModeloColecionavel, Caracteristica, ModeloCaracteristica
├── inventario/         # ColecionavelUsuario, EstanteVirtual, ItemEstante
├── transacoes/         # TransacaoVenda
├── core/               # app de "cola" — vai receber as views/templates das páginas do site
├── static/             # css/ e js/ do projeto (ainda vazios — próximo passo)
└── templates/          # templates Django (ainda vazio — próximo passo)
```

Cada app corresponde a uma seção do seu diagrama DBML, pra ficar fácil de
navegar o código do mesmo jeito que você navega o diagrama.

## Como cada tabela do seu diagrama virou um app

| Tabela no DBML | App Django | Model |
|---|---|---|
| `usuarios` | `usuarios` | `Usuario` |
| `transacoes_venda` | `transacoes` | `TransacaoVenda` |
| `tipos_colecionaveis` | `catalogo` | `TipoColecionavel` |
| `modelos_colecionaveis` | `catalogo` | `ModeloColecionavel` |
| `caracteristicas` | `catalogo` | `Caracteristica` |
| `modelos_caracteristicas` | `catalogo` | `ModeloCaracteristica` |
| `colecionaveis_usuario` | `inventario` | `ColecionavelUsuario` |
| `estantes_virtuais` | `inventario` | `EstanteVirtual` |
| `itens_estante` | `inventario` | `ItemEstante` |

## 3 decisões que mudam levemente o diagrama original (e por quê)

**1. Campo `senha` → sistema de autenticação do Django**
Como combinamos: em vez do campo `senha varchar(255)` guardando texto puro,
`Usuario` estende o `AbstractUser` do Django. A senha é automaticamente
guardada com hash seguro (nunca em texto legível), e você ganha de graça
login, logout, recuperação de senha e permissões. Os campos extras do seu
diagrama (`cpf`, `telefone_whatsapp`, `whatsapp_validado`) continuam lá.

**2. `modelos_caracteristicas`: chave composta → `UniqueConstraint`**
O diagrama definia `(modelo_id, caracteristica_id)` como chave primária
composta. O Django trabalha melhor com um `id` numérico normal — troquei a
chave composta por uma restrição de unicidade (`UniqueConstraint`), que
garante exatamente a mesma regra (não duplicar característica no mesmo
modelo), só que de um jeito mais fácil de usar no ORM e no admin.

**3. `transacoes_venda.colecionavel_usuario_id`: agora é uma referência de verdade**
No DBML original, essa coluna existia mas não tinha uma linha `Ref:`
ligando ela à tabela de colecionáveis. Criei essa ligação de verdade (com
`on_delete=PROTECT`), porque sem ela o Django não sabe navegar de uma
transação até o item vendido — e o `PROTECT` garante que ninguém consiga
apagar um item que já tem histórico de venda.

Se alguma dessas 3 decisões não for o que você imaginou, me fala que eu
ajusto.

## Como rodar

```bash
# 1. Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Crie o banco (SQLite, não precisa instalar nada a mais)
python manage.py migrate

# 4. Popule com os 3 usuários de demonstração + catálogo de exemplo
python manage.py seed_demo

# 5. Crie um usuário admin pra você mesmo acessar o painel
python manage.py createsuperuser

# 6. Rode o servidor
python manage.py runserver
```

Depois disso:
- Site: http://127.0.0.1:8000/ (ainda sem páginas — ver "Próximos passos")
- Painel admin: http://127.0.0.1:8000/admin/

## Os 3 usuários de demonstração

O comando `seed_demo` cria exatamente o que planejamos lá no início do
projeto — 3 usuários prontos, sem precisar de tela de cadastro pra
demonstração:

| Login | Senha | Perfil |
|---|---|---|
| `rafageek` | `demo12345` | Tem item à venda (Optimus Prime) + item só de exibição |
| `colecionasp` | `demo12345` | Tem item pra venda/troca + item à venda |
| `mesageek` | `demo12345` | Tem item só de exibição + item pra troca |

Cada um já vem com uma estante virtual e itens no catálogo (Transformers,
Batman, Pokémon, Gundam, Senhor dos Anéis, Jurassic Park), prontos pra
mostrar nas telas de prateleira, busca e produto.

Quer recriar do zero? `python manage.py seed_demo --limpar`

## O que já está pronto

- Todos os models do diagrama, migrados e testados
- Painel admin completo (você já pode cadastrar/editar tudo por lá)
- Comando de seed com os 3 usuários de demonstração
- **Home (`/`)** — mesmo visual escuro/laranja do projeto original, com filtro
  por categoria (chips) funcionando de verdade contra o banco de dados
- **Login (`/entrar/`)** — autenticação real do Django, mesmo visual, com os
  3 usuários de demonstração já prontos pra usar
- CSS reaproveitado 100% do projeto estático (`static/css/base.css`,
  `layout.css`, `componentes.css`) — nenhuma cor nova foi criada

## Próximos passos (ainda não feitos)

Faltam as demais páginas como views + templates: busca com filtros, produto,
prateleira, wishlist, chat, checkout. Posso seguir com elas a partir daqui,
uma de cada vez, do mesmo jeito que fizemos até agora — qual você quer que
eu faça primeiro?
