
import os
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


# Formato inicial do arquivo criptografado.
MAGIC = b"PLD1"
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32

# Parâmetros iniciais do Scrypt.
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1

HEADER_SIZE = len(MAGIC) + SALT_SIZE + NONCE_SIZE


def _derivar_chave(senha: str, salt: bytes) -> bytes:
    """Deriva uma chave AES-256 a partir da senha."""
    if not isinstance(senha, str) or not senha:
        raise ValueError("A senha não pode estar vazia.")

    if len(senha) > 1024:
        raise ValueError("A senha excede o limite permitido.")

    kdf = Scrypt(
        salt=salt,
        length=KEY_SIZE,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )

    return kdf.derive(senha.encode("utf-8"))


def criptografar_bytes(conteudo: bytes, senha: str) -> bytes:
    """Criptografa bytes e devolve um pacote autocontido."""
    if not isinstance(conteudo, bytes):
        raise TypeError("O conteúdo deve ser bytes.")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)

    chave = _derivar_chave(senha, salt)
    cabecalho = MAGIC + salt + nonce

    cifrador = AESGCM(chave)
    conteudo_cifrado = cifrador.encrypt(
        nonce,
        conteudo,
        cabecalho,
    )

    return cabecalho + conteudo_cifrado


def descriptografar_bytes(pacote: bytes, senha: str) -> bytes:
    """Valida e descriptografa um pacote produzido acima."""
    if not isinstance(pacote, bytes):
        raise TypeError("O pacote deve ser bytes.")

    if len(pacote) < HEADER_SIZE + 16:
        raise ValueError("Pacote incompleto ou inválido.")

    if pacote[:len(MAGIC)] != MAGIC:
        raise ValueError("Formato de arquivo desconhecido.")

    inicio_salt = len(MAGIC)
    inicio_nonce = inicio_salt + SALT_SIZE
    inicio_dados = inicio_nonce + NONCE_SIZE

    salt = pacote[inicio_salt:inicio_nonce]
    nonce = pacote[inicio_nonce:inicio_dados]
    cabecalho = pacote[:HEADER_SIZE]
    conteudo_cifrado = pacote[HEADER_SIZE:]

    chave = _derivar_chave(senha, salt)

    try:
        return AESGCM(chave).decrypt(
            nonce,
            conteudo_cifrado,
            cabecalho,
        )
    except InvalidTag as erro:
        raise ValueError(
            "Senha incorreta ou dados adulterados."
        ) from erro
