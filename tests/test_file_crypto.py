
import pytest

from file_crypto import (
    criptografar_arquivo,
    descriptografar_arquivo,
)


SENHA = "Senha-forte-para-testes-2026!"


def test_arquivo_pode_ser_recuperado(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"
    recuperado = tmp_path / "recuperado.txt"

    conteudo = b"Teste de arquivo " * 10000
    original.write_bytes(conteudo)

    criptografar_arquivo(original, cifrado, SENHA)

    assert original.read_bytes() == conteudo
    assert cifrado.read_bytes() != conteudo

    descriptografar_arquivo(cifrado, recuperado, SENHA)

    assert recuperado.read_bytes() == conteudo


def test_arquivo_vazio(tmp_path):
    original = tmp_path / "vazio.bin"
    cifrado = tmp_path / "vazio.pld"
    recuperado = tmp_path / "recuperado.bin"

    original.write_bytes(b"")

    criptografar_arquivo(original, cifrado, SENHA)
    descriptografar_arquivo(cifrado, recuperado, SENHA)

    assert recuperado.read_bytes() == b""


def test_senha_incorreta_nao_publica_destino(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"
    recuperado = tmp_path / "recuperado.txt"

    original.write_bytes(b"Conteudo protegido")
    criptografar_arquivo(original, cifrado, SENHA)

    with pytest.raises(ValueError, match="Senha incorreta"):
        descriptografar_arquivo(
            cifrado, recuperado, "Senha-errada-2026!"
        )

    assert not recuperado.exists()
    assert original.read_bytes() == b"Conteudo protegido"


def test_nao_sobrescreve_destino(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"

    original.write_bytes(b"Original")
    cifrado.write_bytes(b"Destino existente")

    with pytest.raises(FileExistsError):
        criptografar_arquivo(original, cifrado, SENHA)

    assert cifrado.read_bytes() == b"Destino existente"
    assert original.read_bytes() == b"Original"


def test_adulteracao_e_detectada(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"
    recuperado = tmp_path / "recuperado.txt"

    original.write_bytes(b"Dados que precisam ser protegidos.")
    criptografar_arquivo(original, cifrado, SENHA)

    dados = bytearray(cifrado.read_bytes())
    dados[-1] ^= 1
    cifrado.write_bytes(dados)

    with pytest.raises(ValueError):
        descriptografar_arquivo(cifrado, recuperado, SENHA)

    assert not recuperado.exists()
