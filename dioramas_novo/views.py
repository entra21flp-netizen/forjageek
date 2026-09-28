from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.contrib.staticfiles import finders
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from inventario.models import ColecionavelUsuario, EstanteVirtual, ItemEstante

from .forms import ConfigurarDioramaForm
from .models import DioramaGeradoNovo, DioramaPresetNovo
from .services.diorama_ai import (
    DioramaAIError,
    DioramaAIRateLimitError,
    caminho_preview,
    compor_preset_com_colecionavel,
    gerar_diorama,
)

SESSION_PREVIEW = "diorama_novo_preview"


def _colecionavel_do_usuario(request, pk):
    return get_object_or_404(
        ColecionavelUsuario.objects.select_related("modelo", "modelo__tipo").prefetch_related("imagens"),
        pk=pk, usuario=request.user,
    )


def _estante_principal(usuario, estante_id=None):
    if estante_id:
        selecionada = EstanteVirtual.objects.filter(usuario=usuario, pk=estante_id).first()
        if selecionada:
            return selecionada
    estante = EstanteVirtual.objects.filter(usuario=usuario).order_by("ordem_exibicao", "id").first()
    if estante:
        return estante
    return EstanteVirtual.objects.create(usuario=usuario, nome_estante="Minha estante", ordem_exibicao=1)


@login_required
@require_GET
@xframe_options_sameorigin
def selecionar_colecionavel(request):
    if request.GET.get("estante"):
        estante = EstanteVirtual.objects.filter(usuario=request.user, pk=request.GET["estante"]).first()
        if estante:
            request.session["diorama_estante_id"] = estante.pk
    colecionaveis = (ColecionavelUsuario.objects.filter(usuario=request.user)
                     .select_related("modelo", "modelo__tipo").prefetch_related("imagens"))
    return render(request, "dioramas_novo/selecionar_colecionavel.html", {"colecionaveis": colecionaveis})


@login_required
@require_GET
@xframe_options_sameorigin
def configurar(request, colecionavel_id):
    colecionavel = _colecionavel_do_usuario(request, colecionavel_id)
    return render(request, "dioramas_novo/configurar.html", {"colecionavel": colecionavel, "form": ConfigurarDioramaForm()})


@login_required
@require_POST
@xframe_options_sameorigin
def gerar(request, colecionavel_id):
    colecionavel = _colecionavel_do_usuario(request, colecionavel_id)
    form = ConfigurarDioramaForm(request.POST)
    if not form.is_valid():
        return render(request, "dioramas_novo/configurar.html", {"colecionavel": colecionavel, "form": form}, status=400)
    tipo = form.cleaned_data["tipo"]
    preset = form.cleaned_data.get("preset")
    descricao = (form.cleaned_data.get("descricao") or "").strip()
    if tipo == DioramaGeradoNovo.TIPO_PREDEFINIDO:
        descricao = preset.descricao
        caminho_imagem = finders.find(f"image/dioramas_novo/{preset.slug}.png")
        if not caminho_imagem:
            form.add_error("preset", "A imagem deste cenário não foi encontrada.")
            return render(request, "dioramas_novo/configurar.html", {"colecionavel": colecionavel, "form": form}, status=500)
        try:
            imagem_composta = compor_preset_com_colecionavel(caminho_imagem, colecionavel)
        except DioramaAIError as exc:
            messages.error(request, str(exc))
            return render(request, "dioramas_novo/configurar.html", {"colecionavel": colecionavel, "form": form}, status=400)
        with transaction.atomic():
            diorama = DioramaGeradoNovo(
                usuario=request.user,
                colecionavel=colecionavel,
                preset=preset,
                tipo=DioramaGeradoNovo.TIPO_PREDEFINIDO,
                descricao=descricao,
                prompt_utilizado=preset.prompt_base,
            )
            diorama.imagem.save(f"{preset.slug}.jpg", imagem_composta, save=False)
            diorama.save()
        messages.success(request, f"O diorama {preset.nome} foi salvo na sua prateleira.")
        return redirect("dioramas_novo:posicionar", pk=diorama.pk)
    try:
        resultado = gerar_diorama(colecionavel, descricao, request.user.pk, preset)
    except (DioramaAIRateLimitError, DioramaAIError) as exc:
        messages.error(request, str(exc))
        return render(request, "dioramas_novo/configurar.html", {"colecionavel": colecionavel, "form": form}, status=503)
    anterior = request.session.get(SESSION_PREVIEW) or {}
    anterior_path = caminho_preview(request.user.pk, anterior.get("token"))
    if anterior_path and anterior_path.exists():
        anterior_path.unlink(missing_ok=True)
    request.session[SESSION_PREVIEW] = {
        "token": resultado.token, "colecionavel_id": colecionavel.pk, "tipo": tipo,
        "preset_id": preset.pk if preset else None, "descricao": descricao,
        "prompt": resultado.prompt, "modelo": resultado.modelo,
    }
    return redirect("dioramas_novo:preview")


@login_required
@require_GET
@xframe_options_sameorigin
def preview(request):
    dados = request.session.get(SESSION_PREVIEW)
    if not dados:
        messages.info(request, "Gere um diorama para visualizar o preview.")
        return redirect("dioramas_novo:selecionar")
    colecionavel = _colecionavel_do_usuario(request, dados["colecionavel_id"])
    caminho = caminho_preview(request.user.pk, dados.get("token"))
    if not caminho or not caminho.exists():
        request.session.pop(SESSION_PREVIEW, None)
        messages.error(request, "O preview expirou. Gere o diorama novamente.")
        return redirect("dioramas_novo:configurar", colecionavel_id=colecionavel.pk)
    url = f"{settings.MEDIA_URL}diorama_previews_novo/{request.user.pk}/{dados['token']}.png"
    preset = DioramaPresetNovo.objects.filter(pk=dados.get("preset_id")).first()
    return render(request, "dioramas_novo/preview.html", {"colecionavel": colecionavel, "preview": dados, "preset": preset, "preview_url": url})


@login_required
@require_POST
@xframe_options_sameorigin
def confirmar(request):
    dados = request.session.get(SESSION_PREVIEW)
    if not dados:
        messages.error(request, "Este preview já foi confirmado ou expirou.")
        return redirect("dioramas_novo:selecionar")
    colecionavel = _colecionavel_do_usuario(request, dados["colecionavel_id"])
    caminho = caminho_preview(request.user.pk, dados.get("token"))
    if not caminho or not caminho.exists():
        messages.error(request, "A imagem temporária não foi encontrada.")
        return redirect("dioramas_novo:configurar", colecionavel_id=colecionavel.pk)
    with transaction.atomic():
        diorama = DioramaGeradoNovo(
            usuario=request.user, colecionavel=colecionavel, preset_id=dados.get("preset_id"),
            tipo=dados["tipo"], descricao=dados["descricao"], prompt_utilizado=dados["prompt"],
        )
        with caminho.open("rb") as arquivo:
            diorama.imagem.save(f"preview_{dados['token']}.png", File(arquivo), save=False)
        diorama.save()
    caminho.unlink(missing_ok=True)
    request.session.pop(SESSION_PREVIEW, None)
    messages.success(request, "Diorama salvo na sua prateleira.")
    return redirect("dioramas_novo:posicionar", pk=diorama.pk)


@login_required
@require_POST
@xframe_options_sameorigin
def cancelar(request):
    dados = request.session.pop(SESSION_PREVIEW, None) or {}
    caminho = caminho_preview(request.user.pk, dados.get("token"))
    if caminho and caminho.exists():
        caminho.unlink(missing_ok=True)
    messages.info(request, "Preview cancelado. Nenhum diorama foi salvo.")
    return redirect("dioramas_novo:selecionar")


@login_required
@require_GET
@xframe_options_sameorigin
def detalhe(request, pk):
    diorama = get_object_or_404(DioramaGeradoNovo.objects.select_related("colecionavel__modelo", "preset"), pk=pk, usuario=request.user)
    posicionamento = ItemEstante.objects.filter(diorama_novo=diorama).select_related("estante").first()
    linha_posicionamento = ((posicionamento.posicao_slot - 1) // 4) + 1 if posicionamento else None
    return render(request, "dioramas_novo/detalhe.html", {
        "diorama": diorama,
        "posicionamento": posicionamento,
        "linha_posicionamento": linha_posicionamento,
    })


@login_required
@xframe_options_sameorigin
def posicionar(request, pk):
    diorama = get_object_or_404(DioramaGeradoNovo.objects.select_related("colecionavel__modelo", "preset"), pk=pk, usuario=request.user)
    estante = _estante_principal(request.user, request.session.get("diorama_estante_id"))
    def montar_linhas():
        posicoes = set(
            ItemEstante.objects.filter(estante=estante, posicao_slot__isnull=False)
            .exclude(diorama_novo=diorama)
            .values_list("posicao_slot", flat=True)
        )
        return [
            {"numero": numero, "inicio": inicio, "disponivel": not any(slot in posicoes for slot in range(inicio, inicio + 4))}
            for numero, inicio in enumerate((1, 5, 9), start=1)
        ]
    linhas = montar_linhas()
    if request.method == "POST":
        try:
            numero_linha = int(request.POST.get("linha", ""))
        except (TypeError, ValueError):
            numero_linha = 0
        if numero_linha not in (1, 2, 3):
            messages.error(request, "Escolha uma linha válida.")
        else:
            destino = (numero_linha - 1) * 4 + 1
            with transaction.atomic():
                conflito = (ItemEstante.objects.select_for_update()
                            .filter(estante=estante, posicao_slot__range=(destino, destino + 3))
                            .exclude(diorama_novo=diorama).exists())
                if conflito:
                    messages.error(request, "Esta linha possui colecionáveis. Libere todos os quatro espaços antes de adicionar o diorama.")
                else:
                    item, _ = ItemEstante.objects.select_for_update().get_or_create(
                        diorama_novo=diorama,
                        defaults={"estante": estante},
                    )
                    item.estante = estante
                    item.posicao_slot = destino
                    item.save(update_fields=["estante", "posicao_slot"])
                    messages.success(request, f"Diorama adicionado à Linha {numero_linha}.")
                    return redirect("core:prateleira")
        linhas = montar_linhas()
    if not any(linha["disponivel"] for linha in linhas):
        messages.warning(request, "Seu diorama foi criado e salvo. Neste momento não existe uma linha completamente livre na sua prateleira. Você poderá adicioná-lo depois em Meus Dioramas.")
    return render(request, "dioramas_novo/posicionar.html", {"diorama": diorama, "estante": estante, "linhas": linhas})


@login_required
@require_POST
def remover_prateleira(request, pk):
    diorama = get_object_or_404(DioramaGeradoNovo, pk=pk, usuario=request.user)
    removidos, _ = ItemEstante.objects.filter(diorama_novo=diorama).delete()
    if removidos:
        messages.success(request, "Diorama removido da prateleira. A imagem e o diorama continuam salvos.")
    return redirect("core:prateleira")


@login_required
@xframe_options_sameorigin
def excluir(request, pk):
    diorama = get_object_or_404(DioramaGeradoNovo.objects.select_related("colecionavel__modelo"), pk=pk, usuario=request.user)
    if request.method == "POST":
        imagem = diorama.imagem
        with transaction.atomic():
            diorama.delete()
        if imagem:
            imagem.delete(save=False)
        messages.success(request, "Diorama excluído com sucesso.")
        return redirect("core:prateleira")
    return render(request, "dioramas_novo/confirmar_exclusao.html", {"diorama": diorama})
