import os
import time
from pathlib import Path

from file_crypto import criptografar_arquivo, descriptografar_arquivo


EXTENSAO_CIFRADA = ".pld"


def _tratar_erro_varredura(erro):
    raise erro


def _validar_pastas(origem, destino):
    origem = Path(origem).resolve(strict=True)
    destino = Path(destino).resolve(strict=False)

    if origem == Path(origem.anchor):
        raise ValueError(
            "A origem não pode ser a raiz de uma unidade."
        )

    if destino == Path(destino.anchor):
        raise ValueError(
            "O destino não pode ser a raiz de uma unidade."
        )

    if not origem.is_dir():
        raise ValueError("A origem precisa ser uma pasta.")

    # Impede que origem e destino sejam iguais ou que uma
    # pasta fique dentro da outra.
    if destino == origem:
        raise ValueError(
            "Origem e destino não podem ser iguais."
        )

    if destino.is_relative_to(origem):
        raise ValueError(
            "A pasta de destino não pode ficar dentro da origem."
        )

    if origem.is_relative_to(destino):
        raise ValueError(
            "A pasta de origem não pode ficar dentro do destino."
        )

    return origem, destino


def inventariar_pasta(origem, destino, operacao):
    if operacao not in {"criptografar", "descriptografar"}:
        raise ValueError("Operação desconhecida.")

    origem, destino = _validar_pastas(origem, destino)
    inventario = []

    for pasta_atual, pastas, arquivos in os.walk(
        origem,
        followlinks=False,
        onerror=_tratar_erro_varredura,
    ):
        pasta_atual = Path(pasta_atual)

        # Não entrar em diretórios simbólicos.
        pastas[:] = [
            nome
            for nome in pastas
            if not (pasta_atual / nome).is_symlink()
        ]

        for nome in arquivos:
            arquivo = pasta_atual / nome

            if arquivo.is_symlink() or not arquivo.is_file():
                inventario.append({
                    "origem": arquivo,
                    "destino": None,
                    "status": "ignorado",
                    "mensagem": "Arquivo simbólico ou não regular.",
                })
                continue

            relativo = arquivo.relative_to(origem)

            if operacao == "criptografar":
                if arquivo.name.endswith(EXTENSAO_CIFRADA):
                    inventario.append({
                        "origem": arquivo,
                        "destino": None,
                        "status": "ignorado",
                        "mensagem": "Arquivo com extensão .pld.",
                    })
                    continue

                caminho_destino = destino / Path(
                    str(relativo) + EXTENSAO_CIFRADA
                )

            else:
                if not arquivo.name.endswith(EXTENSAO_CIFRADA):
                    inventario.append({
                        "origem": arquivo,
                        "destino": None,
                        "status": "ignorado",
                        "mensagem": "Arquivo não possui extensão .pld.",
                    })
                    continue

                nome_original = arquivo.name[:-len(EXTENSAO_CIFRADA)]
                caminho_destino = destino / relativo.with_name(nome_original)

            if caminho_destino.exists():
                status = "conflito"
                mensagem = "O destino já existe."
            else:
                status = "pronto"
                mensagem = "Pronto para processamento."

            inventario.append({
                "origem": arquivo,
                "destino": caminho_destino,
                "status": status,
                "mensagem": mensagem,
            })

    for item in inventario:
        try:
            arquivo = Path(item["origem"])

            if arquivo.is_symlink() or not arquivo.is_file():
                tamanho_bytes = 0
                peso = 1
            else:
                tamanho_bytes = arquivo.stat().st_size
                peso = max(tamanho_bytes, 1)

        except OSError:
            tamanho_bytes = 0
            peso = 1

        item["_peso_progresso"] = peso
        item["_tamanho_bytes"] = tamanho_bytes

    return inventario


def processar_pasta(
    origem,
    destino,
    senha,
    operacao,
    progresso=None,
    progresso_arquivos=None,
):
    inventario = inventariar_pasta(origem, destino, operacao)
    resultados = []

    total = sum(item["_peso_progresso"] for item in inventario)
    processados = 0
    total_arquivos = len(inventario)
    arquivos_concluidos = 0

    def notificar_progresso(arquivo=None):
        if progresso is not None:
            progresso(processados, total, arquivo)

    def notificar_arquivo(resultado=None):
        if progresso_arquivos is not None:
            progresso_arquivos(
                arquivos_concluidos,
                total_arquivos,
                resultado,
            )

    # Informa os totais antes de iniciar o processamento.
    notificar_progresso()
    notificar_arquivo()

    origem_resolvida = Path(origem).resolve(strict=True)

    for indice, item in enumerate(inventario, start=1):
        resultado = item.copy()

        resultado["indice_arquivo"] = indice
        resultado["total_arquivos"] = total_arquivos
        resultado["caminho_relativo"] = str(
            Path(item["origem"]).relative_to(origem_resolvida)
        )
        resultado["tamanho_bytes"] = item["_tamanho_bytes"]
        peso = item["_peso_progresso"]
        inicio_arquivo = time.perf_counter()
        bytes_item = 0

        if item["status"] != "pronto":
            processados += peso
            resultado["duracao_segundos"] = None
            resultados.append(resultado)

            arquivos_concluidos += 1
            notificar_progresso(item["origem"])
            notificar_arquivo(resultado)

            continue

        def atualizar_bytes(delta):
            nonlocal bytes_item, processados

            incremento = max(
                0,
                min(int(delta), peso - bytes_item),
            )

            bytes_item += incremento
            processados += incremento
            notificar_progresso(item["origem"])

        try:
            item["destino"].parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if operacao == "criptografar":
                criptografar_arquivo(
                    item["origem"],
                    item["destino"],
                    senha,
                    progresso=atualizar_bytes,
                )
            else:
                descriptografar_arquivo(
                    item["origem"],
                    item["destino"],
                    senha,
                    progresso=atualizar_bytes,
                )

            resultado["status"] = "sucesso"
            resultado["mensagem"] = "Processamento concluído."

        except FileExistsError as erro:
            resultado["status"] = "conflito"
            resultado["mensagem"] = str(erro)

        except Exception as erro:
            resultado["status"] = "erro"
            resultado["mensagem"] = str(erro)

        finally:
            resultado["duracao_segundos"] = (
                time.perf_counter() - inicio_arquivo
            )

            # Finaliza o peso do item, inclusive em caso de falha
            # ou quando o arquivo está vazio.
            processados += peso - bytes_item
            notificar_progresso(item["origem"])

        resultados.append(resultado)

        arquivos_concluidos += 1
        notificar_arquivo(resultado)

    return resultados
