
from pathlib import Path

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


def test_progresso_da_criptografia_corresponde_ao_original(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"

    conteudo = b"Conteudo para acompanhar o progresso " * 10000
    original.write_bytes(conteudo)

    incrementos = []

    criptografar_arquivo(
        original,
        cifrado,
        SENHA,
        progresso=incrementos.append,
    )

    assert sum(incrementos) == original.stat().st_size
    assert all(valor > 0 for valor in incrementos)


def test_progresso_da_descriptografia_corresponde_ao_cifrado(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"
    recuperado = tmp_path / "recuperado.txt"

    original.write_bytes(b"Conteudo para acompanhar o progresso " * 10000)
    criptografar_arquivo(original, cifrado, SENHA)

    incrementos = []

    descriptografar_arquivo(
        cifrado,
        recuperado,
        SENHA,
        progresso=incrementos.append,
    )

    assert sum(incrementos) == cifrado.stat().st_size
    assert all(valor > 0 for valor in incrementos)


def test_progresso_da_descriptografia_de_arquivo_vazio(tmp_path):
    original = tmp_path / "vazio.bin"
    cifrado = tmp_path / "vazio.pld"
    recuperado = tmp_path / "recuperado.bin"

    original.write_bytes(b"")
    criptografar_arquivo(original, cifrado, SENHA)

    incrementos = []

    descriptografar_arquivo(
        cifrado,
        recuperado,
        SENHA,
        progresso=incrementos.append,
    )

    assert sum(incrementos) == cifrado.stat().st_size
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


def test_falha_na_publicacao_limpa_temporario(
    tmp_path, monkeypatch
):
    import file_crypto

    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"

    original.write_bytes(b"Conteudo de teste")
    temporarios_antes = set(tmp_path.glob("*.tmp"))
    ocultos_antes = set(tmp_path.glob(".*.tmp"))

    def falhar_publicacao(temporario, destino):
        raise OSError("Falha simulada na publicação.")

    monkeypatch.setattr(
        file_crypto,
        "_publicar_sem_sobrescrever",
        falhar_publicacao,
    )

    with pytest.raises(
        OSError, match="Falha simulada na publicação"
    ):
        file_crypto.criptografar_arquivo(
            original, cifrado, SENHA
        )

    assert not cifrado.exists()
    assert original.read_bytes() == b"Conteudo de teste"
    assert set(tmp_path.glob("*.tmp")) == temporarios_antes
    assert set(tmp_path.glob(".*.tmp")) == ocultos_antes


def test_falha_no_bloco_final_nao_publica_destino(tmp_path):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"
    recuperado = tmp_path / "recuperado.txt"

    original.write_bytes(b"Conteudo protegido para teste")
    criptografar_arquivo(original, cifrado, SENHA)

    dados = bytearray(cifrado.read_bytes())
    dados[-1] ^= 1
    cifrado.write_bytes(dados)

    temporarios_antes = set(tmp_path.glob("*.tmp"))
    ocultos_antes = set(tmp_path.glob(".*.tmp"))

    with pytest.raises(
        ValueError, match="Senha incorreta ou dados adulterados"
    ):
        descriptografar_arquivo(cifrado, recuperado, SENHA)

    assert not recuperado.exists()
    assert original.read_bytes() == b"Conteudo protegido para teste"
    assert set(tmp_path.glob("*.tmp")) == temporarios_antes
    assert set(tmp_path.glob(".*.tmp")) == ocultos_antes


def test_detecta_dados_extras_na_leitura_da_origem(
    tmp_path, monkeypatch
):
    original = tmp_path / "original.txt"
    cifrado = tmp_path / "original.pld"
    original.write_bytes(b"Conteudo original")

    abrir_original = Path.open

    class LeitorComByteExtra:
        def __init__(self, arquivo):
            self.contexto = abrir_original(arquivo, "rb")
            self.entrada = self.contexto.__enter__()
            self.leitura_final = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.contexto.__exit__(*args)

        def read(self, tamanho=-1):
            if tamanho == 1 and not self.leitura_final:
                self.leitura_final = True
                return b"X"

            return self.entrada.read(tamanho)

    def abrir_com_byte_extra(caminho, mode="r", *args, **kwargs):
        if caminho == original and mode == "rb":
            return LeitorComByteExtra(caminho)

        return abrir_original(caminho, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", abrir_com_byte_extra)

    with pytest.raises(
        ValueError,
        match="arquivo de origem mudou durante a leitura",
    ):
        criptografar_arquivo(original, cifrado, SENHA)

    assert not cifrado.exists()
    assert original.read_bytes() == b"Conteudo original"


def test_rejeita_destino_que_e_link_simbolico(
    tmp_path,
    monkeypatch,
):
    import file_crypto

    origem = tmp_path / "origem.txt"
    destino = tmp_path / "link_quebrado"

    origem.write_text("conteudo original", encoding="utf-8")

    is_symlink_original = Path.is_symlink

    def simular_link_simbolico(caminho):
        if caminho == destino:
            return True

        return is_symlink_original(caminho)

    monkeypatch.setattr(
        Path,
        "is_symlink",
        simular_link_simbolico,
    )

    with pytest.raises(FileExistsError, match="O destino já existe"):
        file_crypto._preparar_caminhos(origem, destino)
