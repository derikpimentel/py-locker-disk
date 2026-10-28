import os
from pathlib import Path

from file_crypto import criptografar_arquivo, descriptografar_arquivo


EXTENSAO_CIFRADA = ".pld"


def _validar_pastas(origem, destino):
    origem = Path(origem).resolve(strict=True)
    destino = Path(destino).resolve(strict=False)

    if not origem.is_dir():
        raise ValueError("A origem precisa ser uma pasta.")

    if origem == destino:
        raise ValueError("Origem e destino não podem ser iguais.")

    # Impede que uma pasta fique dentro da outra.
    # Isso evita processar os próprios arquivos gerados.
    try:
        destino.relative_to(origem)
        raise ValueError(
            "A pasta de destino não pode ficar dentro da origem."
        )
    except ValueError as erro:
        if str(erro).startswith("A pasta de destino"):
            raise

    try:
        origem.relative_to(destino)
        raise ValueError(
            "A pasta de origem não pode ficar dentro do destino."
        )
    except ValueError as erro:
        if str(erro).startswith("A pasta de origem"):
            raise

    return origem, destino


def inventariar_pasta(origem, destino, operacao):
    if operacao not in {"criptografar", "descriptografar"}:
        raise ValueError("Operação desconhecida.")

    origem, destino = _validar_pastas(origem, destino)
    inventario = []

    for pasta_atual, pastas, arquivos in os.walk(
        origem, followlinks=False
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

    return inventario


def processar_pasta(origem, destino, senha, operacao):
    inventario = inventariar_pasta(origem, destino, operacao)
    resultados = []

    for item in inventario:
        resultado = item.copy()

        if item["status"] != "pronto":
            resultados.append(resultado)
            continue

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
                )
            else:
                descriptografar_arquivo(
                    item["origem"],
                    item["destino"],
                    senha,
                )

            resultado["status"] = "sucesso"
            resultado["mensagem"] = "Processamento concluído."

        except Exception as erro:
            resultado["status"] = "erro"
            resultado["mensagem"] = str(erro)

        resultados.append(resultado)

    return resultados
