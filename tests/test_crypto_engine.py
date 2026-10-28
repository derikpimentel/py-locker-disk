
import pytest

from crypto_engine import (
    criptografar_bytes,
    descriptografar_bytes,
)


def test_criptografar_e_recuperar():
    original = b"Arquivo de teste do py-locker-disk."
    pacote = criptografar_bytes(original, "Senha-forte-para-teste-2026!")

    assert pacote != original
    assert descriptografar_bytes(
        pacote, "Senha-forte-para-teste-2026!"
    ) == original


def test_criptografias_geram_pacotes_diferentes():
    original = b"Conteudo repetido."
    senha = "Senha-forte-para-teste-2026!"

    primeiro = criptografar_bytes(original, senha)
    segundo = criptografar_bytes(original, senha)

    assert primeiro != segundo
    assert descriptografar_bytes(primeiro, senha) == original
    assert descriptografar_bytes(segundo, senha) == original


def test_senha_incorreta():
    pacote = criptografar_bytes(b"segredo", "Senha-correta-2026!")

    with pytest.raises(ValueError, match="Senha incorreta"):
        descriptografar_bytes(pacote, "Senha-errada-2026!")


def test_dados_adulterados():
    pacote = bytearray(
        criptografar_bytes(b"conteudo protegido", "Senha-teste-2026!")
    )
    pacote[-1] ^= 1

    with pytest.raises(ValueError, match="Senha incorreta"):
        descriptografar_bytes(bytes(pacote), "Senha-teste-2026!")


def test_pacote_truncado():
    with pytest.raises(ValueError, match="incompleto"):
        descriptografar_bytes(b"PLD1", "Senha-teste-2026!")


def test_senha_vazia():
    with pytest.raises(ValueError, match="vazia"):
        criptografar_bytes(b"teste", "")
