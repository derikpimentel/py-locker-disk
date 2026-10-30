
import os
import struct
import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from crypto_engine import _derivar_chave


MAGIC = b"PLF1"

SALT_SIZE = 16
NONCE_PREFIX_SIZE = 8
TAG_SIZE = 16

CHUNK_SIZE = 1024 * 1024  # 1 MiB
MIN_CHUNK_SIZE = 4096
MAX_CHUNK_SIZE = 4 * 1024 * 1024

# magic, salt, nonce_prefix, chunk_size, original_size
HEADER = struct.Struct(">4s16s8sIQ")
MAX_CHUNKS = 0xFFFFFFFF


def _ler_exatamente(arquivo, tamanho: int) -> bytes:
    partes = bytearray()

    while len(partes) < tamanho:
        parte = arquivo.read(tamanho - len(partes))

        if not parte:
            raise ValueError("Arquivo incompleto ou truncado.")

        partes.extend(parte)

    return bytes(partes)


def _nonce(prefixo: bytes, indice: int) -> bytes:
    if not 0 <= indice <= MAX_CHUNKS:
        raise ValueError("Limite de blocos excedido.")

    return prefixo + struct.pack(">I", indice)


def _criar_temporario(destino: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=f".{destino.name}.",
        suffix=".tmp",
        dir=destino.parent,
        delete=False,
    ) as arquivo:
        return Path(arquivo.name)


def _publicar_sem_sobrescrever(
    temporario: Path,
    destino: Path,
) -> None:
    # Cria o destino atomicamente sem substituir um arquivo existente.
    # Requer suporte a hard links no sistema de arquivos.
    os.link(temporario, destino)


def _preparar_caminhos(origem, destino):
    origem = Path(origem).resolve(strict=True)

    if not origem.is_file():
        raise ValueError("A origem precisa ser um arquivo.")

    destino_informado = Path(destino)
    destino = (
        destino_informado.parent.resolve(strict=False)
        / destino_informado.name
    )

    if origem == destino:
        raise ValueError(
            "Origem e destino não podem ser iguais."
        )

    if destino.is_symlink() or destino.exists():
        raise FileExistsError(
            f"O destino já existe: {destino}"
        )

    if not destino.parent.is_dir():
        raise FileNotFoundError(
            "A pasta de destino não existe."
        )

    return origem, destino


def criptografar_arquivo(
    origem,
    destino,
    senha: str,
    progresso=None,
) -> None:
    origem, destino = _preparar_caminhos(origem, destino)

    tamanho_original = origem.stat().st_size
    quantidade_blocos = (
        tamanho_original + CHUNK_SIZE - 1
    ) // CHUNK_SIZE

    if quantidade_blocos > MAX_CHUNKS:
        raise ValueError("Arquivo excede o limite do formato.")

    salt = os.urandom(SALT_SIZE)
    prefixo_nonce = os.urandom(NONCE_PREFIX_SIZE)

    cabecalho = HEADER.pack(
        MAGIC,
        salt,
        prefixo_nonce,
        CHUNK_SIZE,
        tamanho_original,
    )

    chave = _derivar_chave(senha, salt)
    cifrador = AESGCM(chave)
    temporario = _criar_temporario(destino)

    try:
        with origem.open("rb") as entrada, temporario.open("wb") as saida:
            saida.write(cabecalho)

            for indice in range(quantidade_blocos):
                tamanho_bloco = min(
                    CHUNK_SIZE,
                    tamanho_original - indice * CHUNK_SIZE,
                )

                bloco = _ler_exatamente(entrada, tamanho_bloco)

                aad = cabecalho + struct.pack(
                    ">II", indice, tamanho_bloco
                )

                cifrado = cifrador.encrypt(
                    _nonce(prefixo_nonce, indice),
                    bloco,
                    aad,
                )

                saida.write(cifrado)

                if progresso is not None:
                    progresso(tamanho_bloco)

            if entrada.read(1):
                raise ValueError(
                    "O arquivo de origem mudou durante a leitura."
                )

            # Bloco final autenticado. Também protege arquivos vazios
            # e autentica o cabeçalho completo.
            aad_final = cabecalho + b"END" + struct.pack(
                ">I", quantidade_blocos
            )

            final = cifrador.encrypt(
                _nonce(prefixo_nonce, quantidade_blocos),
                b"",
                aad_final,
            )

            saida.write(final)
            saida.flush()
            os.fsync(saida.fileno())

        _publicar_sem_sobrescrever(temporario, destino)

    finally:
        temporario.unlink(missing_ok=True)


def descriptografar_arquivo(
    origem,
    destino,
    senha: str,
    progresso=None,
) -> None:
    origem, destino = _preparar_caminhos(origem, destino)
    temporario = _criar_temporario(destino)

    try:
        with origem.open("rb") as entrada:
            cabecalho = _ler_exatamente(entrada, HEADER.size)

            if progresso is not None:
                progresso(HEADER.size)

            (
                magic,
                salt,
                prefixo_nonce,
                tamanho_bloco,
                tamanho_original,
            ) = HEADER.unpack(cabecalho)

            if magic != MAGIC:
                raise ValueError("Formato de arquivo desconhecido.")

            if not MIN_CHUNK_SIZE <= tamanho_bloco <= MAX_CHUNK_SIZE:
                raise ValueError("Tamanho de bloco inválido.")

            quantidade_blocos = (
                tamanho_original + tamanho_bloco - 1
            ) // tamanho_bloco

            if quantidade_blocos > MAX_CHUNKS:
                raise ValueError("Limite de blocos excedido.")

            tamanho_esperado = (
                HEADER.size
                + tamanho_original
                + quantidade_blocos * TAG_SIZE
                + TAG_SIZE
            )

            if origem.stat().st_size != tamanho_esperado:
                raise ValueError(
                    "Tamanho inválido ou arquivo truncado."
                )

            chave = _derivar_chave(senha, salt)
            cifrador = AESGCM(chave)
            total_recuperado = 0

            with temporario.open("wb") as saida:
                for indice in range(quantidade_blocos):
                    tamanho_plain = min(
                        tamanho_bloco,
                        tamanho_original - total_recuperado,
                    )

                    cifrado = _ler_exatamente(
                        entrada, tamanho_plain + TAG_SIZE
                    )

                    aad = cabecalho + struct.pack(
                        ">II", indice, tamanho_plain
                    )

                    try:
                        bloco = cifrador.decrypt(
                            _nonce(prefixo_nonce, indice),
                            cifrado,
                            aad,
                        )
                    except InvalidTag as erro:
                        raise ValueError(
                            "Senha incorreta ou dados adulterados."
                        ) from erro

                    saida.write(bloco)
                    total_recuperado += len(bloco)

                    if progresso is not None:
                        progresso(len(cifrado))

                final = _ler_exatamente(entrada, TAG_SIZE)

                if progresso is not None:
                    progresso(TAG_SIZE)

                aad_final = cabecalho + b"END" + struct.pack(
                    ">I", quantidade_blocos
                )

                try:
                    cifrador.decrypt(
                        _nonce(prefixo_nonce, quantidade_blocos),
                        final,
                        aad_final,
                    )
                except InvalidTag as erro:
                    raise ValueError(
                        "Senha incorreta ou dados adulterados."
                    ) from erro

                if entrada.read(1):
                    raise ValueError("Existem dados extras no arquivo.")

                if total_recuperado != tamanho_original:
                    raise ValueError(
                        "O tamanho recuperado não corresponde ao original."
                    )

                saida.flush()
                os.fsync(saida.fileno())

        _publicar_sem_sobrescrever(temporario, destino)

    finally:
        temporario.unlink(missing_ok=True)
