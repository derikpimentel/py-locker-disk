
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


def test_falha_na_varredura_e_reportada(tmp_path, monkeypatch):
    import folder_manager

    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    def walk_com_erro(*args, **kwargs):
        callback = kwargs.get("onerror")

        if callback is None:
            pytest.fail(
                "A varredura precisa definir um tratamento de erros."
            )

        erro = PermissionError("Acesso negado à subpasta.")
        callback(erro)

        return iter(())

    monkeypatch.setattr(folder_manager.os, "walk", walk_com_erro)

    with pytest.raises(PermissionError, match="Acesso negado"):
        folder_manager.inventariar_pasta(
            origem, destino, "criptografar"
        )


def test_rejeita_raiz_de_unidade_como_origem(tmp_path):
    from pathlib import Path

    raiz = Path(Path.cwd().anchor)
    destino = tmp_path / "destino"

    with pytest.raises(ValueError, match="raiz de uma unidade"):
        inventariar_pasta(
            raiz, destino, "criptografar"
        )


def test_rejeita_raiz_de_unidade_como_destino(tmp_path):
    from pathlib import Path

    origem = tmp_path / "origem"
    origem.mkdir()
    destino = Path(Path.cwd().anchor)

    with pytest.raises(ValueError, match="raiz de uma unidade"):
        inventariar_pasta(
            origem, destino, "criptografar"
        )


def test_nao_sobrescreve_destino_criado_apos_inventario(
    tmp_path, monkeypatch
):
    import folder_manager
    from file_crypto import criptografar_arquivo as criptografar_original

    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    arquivo_origem = origem / "documento.txt"
    arquivo_origem.write_text("Conteudo original", encoding="utf-8")

    arquivo_destino = destino / "documento.txt.pld"
    conteudo_existente = "NAO ALTERAR ESTE CONTEUDO"

    def criar_conflito_antes_de_criptografar(
        caminho_origem, caminho_destino, senha, progresso=None
    ):
        arquivo_destino.parent.mkdir(parents=True, exist_ok=True)
        arquivo_destino.write_text(
            conteudo_existente, encoding="utf-8"
        )

        criptografar_original(
            caminho_origem, caminho_destino, senha, progresso=progresso,
        )

    monkeypatch.setattr(
        folder_manager,
        "criptografar_arquivo",
        criar_conflito_antes_de_criptografar,
    )

    resultados = folder_manager.processar_pasta(
        origem, destino, "senha-de-teste", "criptografar"
    )

    assert arquivo_destino.read_text(encoding="utf-8") == conteudo_existente
    assert resultados[0]["status"] == "conflito"
    assert "já existe" in resultados[0]["mensagem"]


def test_progresso_da_criptografia_de_pasta(tmp_path):
    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    arquivo = origem / "documento.txt"
    arquivo.write_bytes(b"Conteudo para testar o progresso " * 100)

    # Deve ser contabilizado, mas ignorado na criptografia.
    (origem / "ja_cifrado.pld").write_bytes(b"Arquivo ignorado")

    eventos = []

    resultados = processar_pasta(
        origem,
        destino,
        SENHA,
        "criptografar",
        progresso=lambda atual, total, nome: eventos.append(
            (atual, total, nome)
        ),
    )

    assert resultados[0]["status"] == "sucesso"
    assert resultados[1]["status"] == "ignorado"

    valores = [evento[0] for evento in eventos]
    totais = [evento[1] for evento in eventos]

    assert valores == sorted(valores)
    assert all(0 <= atual <= total for atual, total, _ in eventos)
    assert len(set(totais)) == 1
    assert eventos[0] == (0, totais[0], None)
    assert valores[-1] == totais[0]


def test_progresso_da_descriptografia_de_pasta(tmp_path):
    from file_crypto import criptografar_arquivo

    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    fonte = tmp_path / "documento.txt"
    fonte.write_bytes(b"Conteudo para testar a recuperacao " * 100)

    cifrado = origem / "documento.txt.pld"
    criptografar_arquivo(fonte, cifrado, SENHA)

    # Deve ser ignorado na descriptografia.
    (origem / "outro_arquivo.txt").write_bytes(b"Arquivo ignorado")

    eventos = []

    resultados = processar_pasta(
        origem,
        destino,
        SENHA,
        "descriptografar",
        progresso=lambda atual, total, nome: eventos.append(
            (atual, total, nome)
        ),
    )

    assert resultados[0]["status"] == "sucesso"
    assert resultados[1]["status"] == "ignorado"

    valores = [evento[0] for evento in eventos]
    totais = [evento[1] for evento in eventos]

    assert valores == sorted(valores)
    assert all(0 <= atual <= total for atual, total, _ in eventos)
    assert len(set(totais)) == 1
    assert eventos[0] == (0, totais[0], None)
    assert valores[-1] == totais[0]


def test_progresso_de_pasta_vazia(tmp_path):
    origem = tmp_path / "origem"
    destino = tmp_path / "destino"
    origem.mkdir()

    eventos = []

    resultados = processar_pasta(
        origem,
        destino,
        SENHA,
        "criptografar",
        progresso=lambda atual, total, nome: eventos.append(
            (atual, total, nome)
        ),
    )

    assert resultados == []
    assert eventos == [(0, 0, None)]
