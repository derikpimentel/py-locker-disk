
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
            resultados = processar_pasta(
                origem, destino, senha, operacao
            )
            self.fila.put(("sucesso", resultados))
        except Exception as erro:
            self.fila.put(("erro", str(erro)))

    def _verificar_fila(self):
        try:
            while True:
                tipo, dados = self.fila.get_nowait()

                if tipo == "erro":
                    self.status_var.set("A operação não foi concluída.")
                    self._adicionar_relatorio(f"Erro geral: {dados}")
                    messagebox.showerror(
                        "Erro",
                        dados,
                        parent=self.raiz,
                    )
                else:
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
                            f"[{status.upper()}] "
                            f"{item['origem']} — {item['mensagem']}"
                        )

                    self._adicionar_relatorio(
                        "Resumo: "
                        + ", ".join(
                            f"{chave}={valor}"
                            for chave, valor in contagens.items()
                        )
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

                self.processando = False
                self.botao_iniciar.configure(state="normal")
                self.senha_var.set("")

        except queue.Empty:
            pass

        self.raiz.after(150, self._verificar_fila)

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
