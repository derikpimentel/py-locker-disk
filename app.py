
import time
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from folder_manager import processar_pasta


class Aplicacao:
    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("py-locker-disk")
        self.raiz.geometry("760x600")
        self.raiz.minsize(680, 520)

        self.fila = queue.Queue()
        self.processando = False

        self.origem_var = tk.StringVar()
        self.destino_var = tk.StringVar()
        self.operacao_var = tk.StringVar(value="Criptografar")
        self.senha_var = tk.StringVar()
        self.exibir_senha_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Pronto para iniciar.")

        self.progresso_var = tk.DoubleVar(value=0)
        self.arquivos_var = tk.StringVar(
            value="Arquivos: 0 de 0"
        )
        self.detalhes_progresso_var = tk.StringVar(
            value="Aguardando operação."
        )
        self.tempo_decorrido_var = tk.StringVar(
            value="Tempo decorrido: 00:00:00"
        )
        self.tempo_restante_var = tk.StringVar(
            value="Tempo restante: --:--:--"
        )
        self.inicio_operacao = None

        self._montar_interface()
        self.raiz.after(150, self._verificar_fila)
        self.raiz.protocol("WM_DELETE_WINDOW", self._fechar)

    def _montar_interface(self):
        principal = ttk.Frame(self.raiz, padding=18)
        principal.pack(fill="both", expand=True)

        ttk.Label(
            principal,
            text="py-locker-disk",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            principal,
            text=(
                "Criptografia e recuperação de arquivos em pastas. "
                "Os arquivos originais serão preservados."
            ),
            wraplength=700,
        ).pack(anchor="w", pady=(4, 16))

        self._campo_pasta(
            principal,
            "Pasta de origem",
            self.origem_var,
            self._selecionar_origem,
        )

        self._campo_pasta(
            principal,
            "Pasta de destino",
            self.destino_var,
            self._selecionar_destino,
        )

        operacao_frame = ttk.LabelFrame(
            principal, text="Operação", padding=10
        )
        operacao_frame.pack(fill="x", pady=8)

        ttk.Radiobutton(
            operacao_frame,
            text="Criptografar",
            variable=self.operacao_var,
            value="Criptografar",
        ).pack(side="left", padx=(0, 20))

        ttk.Radiobutton(
            operacao_frame,
            text="Descriptografar",
            variable=self.operacao_var,
            value="Descriptografar",
        ).pack(side="left")

        senha_frame = ttk.LabelFrame(
            principal, text="Senha", padding=10
        )
        senha_frame.pack(fill="x", pady=8)

        self.campo_senha = ttk.Entry(
            senha_frame,
            textvariable=self.senha_var,
            show="*",
        )
        self.campo_senha.pack(fill="x")

        ttk.Checkbutton(
            senha_frame,
            text="Exibir senha",
            variable=self.exibir_senha_var,
            command=self._alternar_senha,
        ).pack(anchor="w", pady=(6, 0))

        aviso = (
            "ATENÇÃO: teste somente com arquivos descartáveis. "
            "Guarde a senha em local seguro. Se ela for perdida, "
            "os arquivos criptografados poderão ficar irrecuperáveis."
        )

        ttk.Label(
            principal,
            text=aviso,
            wraplength=700,
            foreground="#a33",
        ).pack(anchor="w", pady=8)

        botoes = ttk.Frame(principal)
        botoes.pack(fill="x", pady=8)

        self.botao_iniciar = ttk.Button(
            botoes,
            text="Iniciar operação",
            command=self._iniciar,
        )
        self.botao_iniciar.pack(side="left")

        ttk.Button(
            botoes,
            text="Limpar campos",
            command=self._limpar,
        ).pack(side="left", padx=8)

        ttk.Label(
            principal, text="Status:"
        ).pack(anchor="w", pady=(8, 2))

        ttk.Label(
            principal,
            textvariable=self.status_var,
        ).pack(anchor="w")

        quadro_progresso = ttk.LabelFrame(
            principal,
            text="Progresso da operação",
            padding=10,
        )
        quadro_progresso.pack(fill="x", pady=8)

        self.barra_progresso = ttk.Progressbar(
            quadro_progresso,
            variable=self.progresso_var,
            maximum=100,
            mode="determinate",
        )
        self.barra_progresso.pack(fill="x", pady=(0, 6))

        ttk.Label(
            quadro_progresso,
            textvariable=self.detalhes_progresso_var,
        ).pack(anchor="w")

        ttk.Label(
            quadro_progresso,
            textvariable=self.arquivos_var,
        ).pack(anchor="w", pady=(4, 0))

        quadro_tempos = ttk.Frame(quadro_progresso)
        quadro_tempos.pack(fill="x", pady=(6, 0))

        ttk.Label(
            quadro_tempos,
            textvariable=self.tempo_decorrido_var,
        ).pack(side="left")

        ttk.Label(
            quadro_tempos,
            textvariable=self.tempo_restante_var,
        ).pack(side="right")

        ttk.Label(
            principal,
            text="Relatório da operação",
        ).pack(anchor="w", pady=(10, 4))

        quadro_relatorio = ttk.Frame(principal)
        quadro_relatorio.pack(fill="both", expand=True)

        self.relatorio = tk.Text(
            quadro_relatorio,
            height=10,
            wrap="word",
            state="disabled",
        )
        barra = ttk.Scrollbar(
            quadro_relatorio,
            orient="vertical",
            command=self.relatorio.yview,
        )
        self.relatorio.configure(yscrollcommand=barra.set)

        self.relatorio.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

    def _campo_pasta(self, pai, titulo, variavel, comando):
        quadro = ttk.LabelFrame(pai, text=titulo, padding=10)
        quadro.pack(fill="x", pady=5)

        linha = ttk.Frame(quadro)
        linha.pack(fill="x")

        ttk.Entry(
            linha, textvariable=variavel
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            linha, text="Selecionar...", command=comando
        ).pack(side="left", padx=(8, 0))

    def _selecionar_origem(self):
        pasta = filedialog.askdirectory(
            parent=self.raiz,
            title="Selecione a pasta de origem",
        )
        if pasta:
            self.origem_var.set(pasta)

    def _selecionar_destino(self):
        pasta = filedialog.askdirectory(
            parent=self.raiz,
            title="Selecione a pasta de destino",
        )
        if pasta:
            self.destino_var.set(pasta)

    def _alternar_senha(self):
        self.campo_senha.configure(
            show="" if self.exibir_senha_var.get() else "*"
        )

    def _adicionar_relatorio(self, texto):
        self.relatorio.configure(state="normal")
        self.relatorio.insert("end", texto + "\n")
        self.relatorio.see("end")
        self.relatorio.configure(state="disabled")

    def _iniciar(self):
        if self.processando:
            return

        origem_texto = self.origem_var.get().strip()
        destino_texto = self.destino_var.get().strip()
        senha = self.senha_var.get()
        operacao = self.operacao_var.get()

        if not origem_texto or not destino_texto:
            messagebox.showwarning(
                "Pastas obrigatórias",
                "Selecione as pastas de origem e destino.",
                parent=self.raiz,
            )
            return

        if not senha:
            messagebox.showwarning(
                "Senha obrigatória",
                "Informe a senha para continuar.",
                parent=self.raiz,
            )
            return

        origem = Path(origem_texto).resolve()
        destino = Path(destino_texto).resolve()

        if not origem.is_dir() or not destino.is_dir():
            messagebox.showerror(
                "Pasta inválida",
                "A origem e o destino precisam ser pastas existentes.",
                parent=self.raiz,
            )
            return

        if origem == destino:
            messagebox.showerror(
                "Pastas incompatíveis",
                "A origem e o destino não podem ser iguais.",
                parent=self.raiz,
            )
            return

        if (
            origem_texto == Path(origem_texto).anchor
            or destino_texto == Path(destino_texto).anchor
        ):
            messagebox.showerror(
                "Operação bloqueada",
                "Não selecione a raiz de uma unidade. "
                "Use uma pasta de teste específica.",
                parent=self.raiz,
            )
            return

        try:
            destino.relative_to(origem)
            destino_dentro_origem = True
        except ValueError:
            destino_dentro_origem = False

        try:
            origem.relative_to(destino)
            origem_dentro_destino = True
        except ValueError:
            origem_dentro_destino = False

        if destino_dentro_origem or origem_dentro_destino:
            messagebox.showerror(
                "Pastas incompatíveis",
                "A origem e o destino não podem conter um ao outro.",
                parent=self.raiz,
            )
            return

        nome_operacao = (
            "criptografar"
            if operacao == "Criptografar"
            else "descriptografar"
        )

        confirmado = messagebox.askyesno(
            "Confirmar operação",
            f"Operação: {operacao}\n\n"
            f"Origem: {origem}\n"
            f"Destino: {destino}\n\n"
            "Os arquivos originais não serão apagados. "
            "Deseja continuar?",
            parent=self.raiz,
        )

        if not confirmado:
            return

        self.processando = True
        self.botao_iniciar.configure(state="disabled")

        self.inicio_operacao = time.perf_counter()
        self.progresso_var.set(0)
        self.arquivos_var.set("Arquivos: 0 de 0")
        self.detalhes_progresso_var.set(
            "Preparando processamento..."
        )
        self.tempo_decorrido_var.set(
            "Tempo decorrido: 00:00:00"
        )
        self.tempo_restante_var.set(
            "Tempo restante: calculando..."
        )

        self.status_var.set("Processando arquivos...")
        self._adicionar_relatorio(
            f"\nIniciando: {operacao} — origem: {origem}"
        )

        threading.Thread(
            target=self._executar_operacao,
            args=(origem, destino, senha, nome_operacao),
            daemon=True,
        ).start()

    def _executar_operacao(self, origem, destino, senha, operacao):
        try:
            def informar_progresso(atual, total, arquivo):
                self.fila.put(
                    ("progresso", (atual, total, arquivo))
                )

            def informar_progresso_arquivos(
                atual,
                total,
                resultado,
            ):
                self.fila.put(
                    ("arquivos", (atual, total, resultado))
                )

            resultados = processar_pasta(
                origem,
                destino,
                senha,
                operacao,
                progresso=informar_progresso,
                progresso_arquivos=informar_progresso_arquivos,
            )

            self.fila.put(("sucesso", resultados))

        except Exception as erro:
            self.fila.put(("erro", str(erro)))

    def _formatar_tempo(self, segundos):
        segundos = max(0, int(segundos))
        horas, resto = divmod(segundos, 3600)
        minutos, segundos = divmod(resto, 60)

        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


    def _formatar_tamanho(self, tamanho_bytes):
        tamanho = float(tamanho_bytes)

        if tamanho < 1024:
            return f"{int(tamanho)} B"

        for unidade in ("KB", "MB", "GB", "TB"):
            tamanho /= 1024

            if tamanho < 1024 or unidade == "TB":
                return f"{tamanho:.2f} {unidade}"


    def _verificar_fila(self):
        try:
            while True:
                tipo, dados = self.fila.get_nowait()

                if tipo == "progresso":
                    atual, total, arquivo = dados

                    percentual = (
                        atual / total * 100
                        if total > 0
                        else 100
                    )

                    self.progresso_var.set(percentual)

                    self.detalhes_progresso_var.set(
                        f"{percentual:.1f}% — "
                        f"{atual:,} de {total:,} bytes".replace(",", ".")
                        + (
                            f" | {Path(arquivo).name}"
                            if arquivo is not None
                            else ""
                        )
                    )

                    if self.inicio_operacao is not None:
                        decorrido = (
                            time.perf_counter() - self.inicio_operacao
                        )

                        self.tempo_decorrido_var.set(
                            "Tempo decorrido: "
                            + self._formatar_tempo(decorrido)
                        )

                        if atual > 0 and total > atual:
                            restante = decorrido * (total - atual) / atual
                            texto_restante = self._formatar_tempo(restante)
                        elif atual >= total:
                            texto_restante = "00:00:00"
                        else:
                            texto_restante = "Calculando..."

                        self.tempo_restante_var.set(
                            f"Tempo restante: {texto_restante}"
                        )

                elif tipo == "arquivos":
                    atual, total, resultado = dados

                    self.arquivos_var.set(
                        f"Arquivos: {atual} de {total}"
                    )

                    if resultado is not None:
                        status = resultado["status"]
                        origem = Path(resultado["origem"])

                        nome = origem.name
                        caminho = resultado["caminho_relativo"]
                        indice = resultado["indice_arquivo"]
                        total_arquivos = resultado["total_arquivos"]
                        tamanho = self._formatar_tamanho(
                            resultado["tamanho_bytes"]
                        )

                        duracao = resultado.get("duracao_segundos")

                        texto_duracao = (
                            f"Duração: {duracao:.2f}s"
                            if duracao is not None
                            else "Duração: não disponível"
                        )

                        self._adicionar_relatorio(
                            f"\n[{status.upper()}] "
                            f"Arquivo {indice} de {total_arquivos}\n"
                            f"Nome: {nome}\n"
                            f"Caminho: {caminho}\n"
                            f"Tamanho: {tamanho}\n"
                            f"{texto_duracao}\n"
                            f"Resultado: {resultado['mensagem']}\n"
                            f"{'-' * 55}"
                        )

                elif tipo == "erro":
                    self.status_var.set("A operação não foi concluída.")
                    self._adicionar_relatorio(f"Erro geral: {dados}")

                    messagebox.showerror(
                        "Erro",
                        dados,
                        parent=self.raiz,
                    )

                    self._finalizar_operacao()

                elif tipo == "sucesso":
                    contagens = {
                        "sucesso": 0,
                        "erro": 0,
                        "conflito": 0,
                        "ignorado": 0,
                        "pronto": 0,
                    }

                    for item in dados:
                        status = item["status"]
                        contagens[status] = contagens.get(status, 0) + 1

                    self._adicionar_relatorio(
                        "Resumo: "
                        + ", ".join(
                            f"{chave}={valor}"
                            for chave, valor in contagens.items()
                        )
                    )

                    if self.inicio_operacao is not None:
                        duracao_total = (
                            time.perf_counter() - self.inicio_operacao
                        )

                        self._adicionar_relatorio(
                            "Duração total: "
                            f"{self._formatar_tempo(duracao_total)}"
                        )

                    self.progresso_var.set(100)
                    self.tempo_restante_var.set(
                        "Tempo restante: 00:00:00"
                    )
                    self.detalhes_progresso_var.set(
                        "Processamento concluído."
                    )

                    self.arquivos_var.set(
                        f"Arquivos: {len(dados)} de {len(dados)}"
                    )

                    self.status_var.set("Operação finalizada.")

                    messagebox.showinfo(
                        "Operação finalizada",
                        f"Sucessos: {contagens['sucesso']}\n"
                        f"Falhas: {contagens['erro']}\n"
                        f"Conflitos: {contagens['conflito']}\n"
                        f"Ignorados: {contagens['ignorado']}",
                        parent=self.raiz,
                    )

                    self._finalizar_operacao()

        except queue.Empty:
            pass

        self.raiz.after(150, self._verificar_fila)

    def _finalizar_operacao(self):
        self.processando = False
        self.botao_iniciar.configure(state="normal")
        self.senha_var.set("")
        self.inicio_operacao = None

    def _limpar(self):
        if self.processando:
            messagebox.showwarning(
                "Operação em andamento",
                "Aguarde a conclusão antes de limpar os campos.",
                parent=self.raiz,
            )
            return

        self.origem_var.set("")
        self.destino_var.set("")
        self.senha_var.set("")
        self.status_var.set("Pronto para iniciar.")
        self.relatorio.configure(state="normal")
        self.relatorio.delete("1.0", "end")
        self.relatorio.configure(state="disabled")

    def _fechar(self):
        if self.processando:
            messagebox.showwarning(
                "Operação em andamento",
                "Aguarde o processamento terminar antes de fechar.",
                parent=self.raiz,
            )
            return

        self.raiz.destroy()


if __name__ == "__main__":
    janela = tk.Tk()
    Aplicacao(janela)
    janela.mainloop()
