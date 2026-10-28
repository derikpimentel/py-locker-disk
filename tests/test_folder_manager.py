
import pytest

from folder_manager import inventariar_pasta, processar_pasta


SENHA = "Senha-forte-para-testes-2026!"


def test_inventaria_arquivos_e_subpastas(tmp_path):
    origem = tmp_path / "origem"
    destino = tmp_path / "destino"

    subpasta = origem / "documentos"
    subpasta.mkdir(parents=True)
    (origem / "arquivo.txt").write_text("Teste", encoding="utf-8")
    (subpasta / "relatorio.txt").write_text("Relatório", encoding="utf-8")

    inventario = inventariar_pasta(origem, destino, "criptografar")

    prontos = [item for item in inventario if item["status"] == "pronto"]

    assert len(prontos) == 2


def test_criptografa_pasta_preservando_originais(tmp_path):
    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    arquivo = origem / "teste.txt"
    arquivo.write_text("Conteúdo de teste", encoding="utf-8")

    resultados = processar_pasta(
        origem, destino, SENHA, "criptografar"
    )

    assert resultados[0]["status"] == "sucesso"
    assert arquivo.read_text(encoding="utf-8") == "Conteúdo de teste"
    assert (destino / "teste.txt.pld").is_file()


def test_descriptografa_pasta_preservando_cifrados(tmp_path):
    origem = tmp_path / "origem"
    cifrados = tmp_path / "cifrados"
    recuperados = tmp_path / "recuperados"
    origem.mkdir()

    arquivo = origem / "teste.txt"
    arquivo.write_text("Conteúdo original", encoding="utf-8")

    assert processar_pasta(
        origem, cifrados, SENHA, "criptografar"
    )[0]["status"] == "sucesso"

    resultados = processar_pasta(
        cifrados, recuperados, SENHA, "descriptografar"
    )

    assert resultados[0]["status"] == "sucesso"
    assert (cifrados / "teste.txt.pld").is_file()
    assert (
        recuperados / "teste.txt"
    ).read_text(encoding="utf-8") == "Conteúdo original"


def test_nao_sobrescreve_destino_existente(tmp_path):
    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()
    destino.mkdir()

    (origem / "teste.txt").write_text("Original", encoding="utf-8")
    existente = destino / "teste.txt.pld"
    existente.write_bytes("Não sobrescrever".encode("utf-8"))

    resultados = processar_pasta(
        origem, destino, SENHA, "criptografar"
    )

    assert resultados[0]["status"] == "conflito"
    assert existente.read_bytes() == "Não sobrescrever".encode("utf-8")


def test_rejeita_pasta_de_destino_dentro_da_origem(tmp_path):
    origem = tmp_path / "origem"
    destino = origem / "destino"
    origem.mkdir()

    with pytest.raises(ValueError):
        inventariar_pasta(origem, destino, "criptografar")


def test_rejeita_operacao_desconhecida(tmp_path):
    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    with pytest.raises(ValueError):
        inventariar_pasta(origem, destino, "excluir")
