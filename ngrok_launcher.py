import os
import json
import subprocess
import re
import sys
import threading
import time
import urllib.request
import webbrowser
import tkinter as tk
import customtkinter as ctk

# Caminhos e Constantes
CONFIG_FILE = "config.json"
DEFAULT_DOMAIN = "powerful-expert-macaw.ngrok-free.app"
DEFAULT_PORTS = [80, 8082, 443]
LAUNCHER_VERSION = "dev"
GITHUB_REPO = "igormenin/NgrokLauncher"

def resource_path(relative_path):
    """Retorna o caminho absoluto do recurso, seja rodando em script ou empacotado."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Configurações do CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def get_lnk_info_via_ps():
    """Busca e extrai os argumentos dos atalhos .lnk no diretório atual via PowerShell."""
    cmd = [
        "powershell", "-Command",
        "$sh = New-Object -ComObject WScript.Shell; "
        "Get-ChildItem *.lnk 2>$null | ForEach-Object { "
        "  $lnk = $sh.CreateShortcut($_.FullName); "
        "  [PSCustomObject]@{ Name = $_.BaseName; Target = $lnk.TargetPath; Arguments = $lnk.Arguments } "
        "} | ConvertTo-Json"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                return [data]
            return data
    except Exception as e:
        print("Erro ao ler atalhos via PowerShell:", e)
    return []

def load_or_create_config():
    """Lê o arquivo config.json ou migra dados dos arquivos .lnk para criá-lo."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Erro ao ler config.json, recriando...", e)
    
    # Se não existe, tenta extrair informações dos atalhos .lnk existentes
    lnk_data = get_lnk_info_via_ps()
    ports = []
    domain = DEFAULT_DOMAIN
    
    if lnk_data:
        for item in lnk_data:
            args = item.get("Arguments", "")
            # Extrair domínio: --domain=xxx ou --url=xxx
            domain_match = re.search(r'--(?:domain|url)=([^\s]+)', args)
            if domain_match:
                domain = domain_match.group(1)
            # Extrair a porta (geralmente o número no final dos argumentos)
            port_match = re.search(r'(\d+)$', args.strip())
            if port_match:
                try:
                    ports.append(int(port_match.group(1)))
                except:
                    pass
        ports = sorted(list(set(ports)))
    
    if not ports:
        ports = DEFAULT_PORTS
        
    config = {
        "public_url": domain,
        "ports": ports
    }
    
    save_config(config)
    return config

def save_config(config):
    """Salva a configuração atual no arquivo config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Erro ao salvar config.json:", e)

def sanitize_domain(domain):
    """Remove o protocolo (http:// ou https://) e caminhos adicionais do domínio."""
    if not domain:
        return ""
    domain = re.sub(r'^https?://', '', domain.strip())
    domain = domain.split('/')[0]
    return domain

class CTkMessageboxCustom(ctk.CTkToplevel):
    """Caixa de diálogo de mensagem personalizada e estilizada em CustomTkinter."""
    def __init__(self, parent, title, message, icon="info", option_type="ok"):
        super().__init__(parent)
        self.title(title)
        self.geometry("380x250")
        self.resizable(False, False)
        
        # Carrega o ícone se existir
        icon_path = resource_path("launcher_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        # Garante foco modal
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        
        # Centralizar a janela em relação ao pai
        self.update_idletasks()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        
        x = parent_x + (parent_width - 380) // 2
        y = parent_y + (parent_height - 250) // 2
        self.geometry(f"380x250+{x}+{y}")
        
        color = "#1f538d"
        icon_char = "ℹ"
        if icon == "warning":
            color = "#e67e22"  # Laranja
            icon_char = "⚠"
        elif icon == "error":
            color = "#e74c3c"  # Vermelho
            icon_char = "❌"
        elif icon == "question":
            color = "#3498db"  # Azul
            icon_char = "❓"

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=15)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.lbl_icon = ctk.CTkLabel(content_frame, text=icon_char, font=("Segoe UI Symbol", 32), text_color=color)
        self.lbl_icon.pack(pady=(5, 5))
        
        self.lbl_msg = ctk.CTkLabel(content_frame, text=message, font=("Segoe UI", 12), wraplength=320)
        self.lbl_msg.pack(pady=10, fill="both", expand=True)
        
        if option_type == "yesno":
            btn_yes = ctk.CTkButton(
                btn_frame, 
                text="Sim", 
                width=100, 
                fg_color="#1f538d",
                command=lambda: self.on_click(True)
            )
            btn_yes.pack(side="left", padx=(70, 10))
            
            btn_no = ctk.CTkButton(
                btn_frame, 
                text="Não", 
                width=100, 
                fg_color="#333333",
                hover_color="#444444",
                command=lambda: self.on_click(False)
            )
            btn_no.pack(side="left", padx=10)
        else:
            btn_ok = ctk.CTkButton(
                btn_frame, 
                text="OK", 
                width=120, 
                fg_color="#1f538d",
                command=lambda: self.on_click(True)
            )
            btn_ok.pack(pady=5)
            
        self.protocol("WM_DELETE_WINDOW", lambda: self.on_click(False))
        
    def on_click(self, value):
        self.result = value
        self.grab_release()
        self.destroy()

def show_custom_messagebox(parent, title, message, icon="info", option_type="ok"):
    """Exibe um pop-up customizado com bloqueio síncrono e retorna o resultado."""
    dialog = CTkMessageboxCustom(parent, title, message, icon, option_type)
    parent.wait_window(dialog)
    return dialog.result


class SettingsWindow(ctk.CTkToplevel):
    """Janela de Configurações secundária (pop-up modal)."""
    def __init__(self, parent, config, on_save_callback):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.on_save_callback = on_save_callback
        
        self.title("Configurações")
        self.geometry("380x480")
        self.resizable(False, False)
        
        # Carrega o ícone se existir
        icon_path = resource_path("launcher_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        # Garante foco modal
        self.transient(parent)
        self.grab_set()
        
        self.ports_list = list(self.config.get("ports", []))
        
        # Intercepta o fechamento pelo [X] do título da janela para salvar
        self.protocol("WM_DELETE_WINDOW", self.save_and_close)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Título da janela
        lbl_title = ctk.CTkLabel(self, text="Gerenciador de Configurações", font=('Segoe UI', 16, 'bold'))
        lbl_title.pack(pady=15)
        
        # Seção do Domínio
        domain_frame = ctk.CTkFrame(self)
        domain_frame.pack(fill="x", padx=20, pady=5)
        
        lbl_domain = ctk.CTkLabel(domain_frame, text="Domínio Principal (URL Única):", font=('Segoe UI', 12, 'bold'))
        lbl_domain.pack(anchor="w", padx=10, pady=5)
        
        self.domain_entry = ctk.CTkEntry(domain_frame, width=320)
        self.domain_entry.insert(0, self.config.get("public_url", DEFAULT_DOMAIN))
        self.domain_entry.pack(padx=10, pady=5)
        
        # Seção de Portas
        ports_section = ctk.CTkLabel(self, text="Gerenciar Portas Cadastradas:", font=('Segoe UI', 12, 'bold'))
        ports_section.pack(anchor="w", padx=20, pady=(15, 5))
        
        # Frame de rolagem das portas
        self.ports_scroll_frame = ctk.CTkScrollableFrame(self, height=180)
        self.ports_scroll_frame.pack(fill="both", padx=20, pady=5)
        
        # Seção para Adicionar Porta
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        self.add_port_entry = ctk.CTkEntry(add_frame, placeholder_text="Ex: 8080", width=120)
        self.add_port_entry.pack(side="left", padx=(10, 5), pady=10)
        self.add_port_entry.bind("<Return>", lambda e: self.add_port())
        
        btn_add = ctk.CTkButton(add_frame, text="+ Adicionar", width=100, command=self.add_port)
        btn_add.pack(side="left", padx=5, pady=10)
        
        # Botões de Ação Inferiores
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        btn_close = ctk.CTkButton(actions_frame, text="Salvar e Fechar", command=self.save_and_close, fg_color="#1f538d")
        btn_close.pack(fill="x", pady=5)
        
        # Preencher a lista de portas
        self.refresh_ports_list()
        
    def refresh_ports_list(self):
        for widget in self.ports_scroll_frame.winfo_children():
            widget.destroy()
            
        for port in self.ports_list:
            row = ctk.CTkFrame(self.ports_scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            lbl = ctk.CTkLabel(row, text=f"Porta {port}", font=('Segoe UI', 12))
            lbl.pack(side="left", padx=10)
            
            # Botão de remover (X)
            btn_del = ctk.CTkButton(
                row, 
                text="X", 
                width=28, 
                height=24, 
                fg_color="#d9534f", 
                hover_color="#c9302c",
                command=lambda p=port: self.remove_port(p)
            )
            btn_del.pack(side="right", padx=10)
            
    def remove_port(self, port):
        if port in self.ports_list:
            self.ports_list.remove(port)
            self.refresh_ports_list()
            
    def add_port(self):
        val = self.add_port_entry.get().strip()
        if not val:
            return
        if not val.isdigit():
            show_custom_messagebox(self, "Erro", "A porta deve ser um número inteiro!", icon="error")
            return
        port = int(val)
        if port <= 0 or port > 65535:
            show_custom_messagebox(self, "Erro", "Porta inválida (deve ser entre 1 e 65535)!", icon="error")
            return
        if port in self.ports_list:
            show_custom_messagebox(self, "Aviso", "Esta porta já está cadastrada!", icon="warning")
            return
            
        self.ports_list.append(port)
        self.ports_list.sort()
        self.add_port_entry.delete(0, "end")
        self.refresh_ports_list()
        
    def save_and_close(self):
        domain = self.domain_entry.get().strip()
        if not domain:
            show_custom_messagebox(self, "Erro", "O domínio não pode ficar vazio!", icon="error")
            return
            
        domain = sanitize_domain(domain)
        self.config["public_url"] = domain
        self.config["ports"] = self.ports_list
        
        save_config(self.config)
        self.on_save_callback()
        self.destroy()


class NgrokLauncherApp(ctk.CTk):
    """Janela Principal (Lançador do NGROK)."""
    def __init__(self):
        super().__init__()
        
        self.config = load_or_create_config()
        self.selected_port = None
        self.ngrok_process = None
        self.is_running = False
        self.log_thread = None
        self.update_highlighted = False
        self.tunnels_api_url = "http://127.0.0.1:4040/api/tunnels"
        self.check_api_url_attempts = 0
        
        self.title(f"NGROK Launcher ({LAUNCHER_VERSION})")
        self.geometry("1000x600")
        self.resizable(False, False)
        
        # Carrega o ícone se existir
        icon_path = resource_path("launcher_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        
        self.setup_ui()
        self.create_port_buttons()
        self.set_offline_url_preview()
        
        # Protocolo para fechar a aplicação de forma limpa
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Agenda verificação do executável ngrok.exe e atualizações do launcher
        self.after(100, self.check_ngrok_executable)
        self.after(1500, lambda: self.check_for_launcher_updates(manual=False))
        
    def setup_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        lbl_title = ctk.CTkLabel(header_frame, text="NGROK Launcher", font=('Segoe UI', 20, 'bold'))
        lbl_title.pack(side="left")
        
        # Botão de Configurações (Engrenagem)
        btn_settings = ctk.CTkButton(
            header_frame, 
            text="⚙", 
            width=36, 
            height=36, 
            fg_color="transparent", 
            hover_color="#333333",
            font=('Segoe UI', 18),
            command=self.open_settings
        )
        btn_settings.pack(side="right")

        # Botão de Atualização (ao lado do botão de configuração)
        self.update_btn = ctk.CTkButton(
            header_frame, 
            text="⟳", 
            width=36, 
            height=36, 
            fg_color="transparent", 
            hover_color="#333333",
            font=('Segoe UI', 18),
            command=self.update_ngrok
        )
        self.update_btn.pack(side="right", padx=(0, 5))
        
        if LAUNCHER_VERSION == "dev":
            self.test_update_btn = ctk.CTkButton(
                header_frame,
                text="Testar Update",
                width=95,
                height=36,
                font=('Segoe UI', 11),
                fg_color="#2c3e50",
                hover_color="#34495e",
                command=lambda: self.check_for_launcher_updates(manual=True, force=True)
            )
            self.test_update_btn.pack(side="right", padx=(0, 10))
        
        # 2. Seção de Seleção de Porta
        lbl_select = ctk.CTkLabel(self, text="Selecione a Porta:", font=('Segoe UI', 12, 'bold'))
        lbl_select.pack(anchor="w", padx=25, pady=(10, 5))
        
        self.ports_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ports_frame.pack(fill="x", padx=20, pady=5)
        
        # 3. Status da Conexão
        self.status_lbl = ctk.CTkLabel(self, text="● Inativo", font=('Segoe UI', 13, 'bold'), text_color="#95a5a6")
        self.status_lbl.pack(pady=10)
        
        # 4. Botão Principal Iniciar/Parar (No máximo 40% da largura = 400px, centralizado)
        self.start_btn = ctk.CTkButton(
            self, 
            text="INICIAR NGROK", 
            font=('Segoe UI', 14, 'bold'),
            height=45,
            width=400,
            fg_color="#2ecc71", 
            hover_color="#27ae60",
            command=self.toggle_ngrok
        )
        self.start_btn.pack(anchor="center", pady=10)
        
        # 5. URL Pública (Visualização, Cópia e Navegador)
        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=5)
        
        lbl_url = ctk.CTkLabel(url_frame, text="Public URL:", font=('Segoe UI', 11, 'bold'))
        lbl_url.pack(anchor="w", padx=5)
        
        self.url_entry = ctk.CTkEntry(url_frame, font=('Segoe UI', 11))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=5)
        self.url_entry.configure(state="readonly")
        
        self.copy_btn = ctk.CTkButton(url_frame, text="📋", width=36, height=28, command=self.copy_url, hover_color="#333333")
        self.copy_btn.pack(side="left", padx=2, pady=5)
        
        self.open_btn = ctk.CTkButton(url_frame, text="🌐", width=36, height=28, command=self.open_url, hover_color="#333333")
        self.open_btn.pack(side="left", padx=2, pady=5)
        
        # 6. Console de Logs em Tempo Real
        lbl_console = ctk.CTkLabel(self, text="Console de Logs (NGROK Output):", font=('Segoe UI', 11, 'bold'))
        lbl_console.pack(anchor="w", padx=25, pady=(10, 2))
        
        self.console_text = ctk.CTkTextbox(
            self, 
            height=160, 
            font=('Consolas', 10), 
            fg_color="#101010", 
            text_color="#e0e0e0"
        )
        self.console_text.pack(fill="both", expand=True, padx=20, pady=(5, 15))
        self.console_text.configure(state="disabled")

    def create_port_buttons(self):
        """Desenha os botões dinâmicos de seleção de porta em uma única linha."""
        for widget in self.ports_frame.winfo_children():
            widget.destroy()
            
        ports = self.config.get("ports", [])
        self.port_buttons = {}
        
        if not ports:
            no_ports_lbl = ctk.CTkLabel(self.ports_frame, text="Nenhuma porta cadastrada. Clique em ⚙.", font=('Segoe UI', 11, 'italic'))
            no_ports_lbl.pack(pady=5)
            return

        # Calcular a largura dinâmica para caber tudo em uma única linha
        num_ports = len(ports)
        # Espaço disponível: 1000 (largura da janela) - 40 (padding) = 960
        available_width = 960
        # Descontar margem entre os botões (10px por botão de padding acumulado)
        spacing = 10
        total_spacings = spacing * (num_ports - 1)
        
        calc_width = (available_width - total_spacings) // num_ports
        max_button_width = 150  # Tamanho máximo para poucos botões
        button_width = min(max_button_width, calc_width)
        
        if button_width < 50:
            button_width = 50

        # Sub-container centralizado
        buttons_container = ctk.CTkFrame(self.ports_frame, fg_color="transparent")
        buttons_container.pack(anchor="center")

        for port in ports:
            btn = ctk.CTkButton(
                buttons_container,
                text=f"Porta {port}",
                width=button_width,
                height=32,
                corner_radius=6,
                fg_color="#333333" if port != self.selected_port else "#1f538d",
                command=lambda p=port: self.select_port(p)
            )
            btn.pack(side="left", padx=5)
            self.port_buttons[port] = btn
            
        # Seleciona a primeira porta por padrão se nenhuma estiver selecionada ou se a anterior sumiu
        if self.selected_port not in ports and ports:
            self.select_port(ports[0])
        elif self.selected_port in ports:
            self.select_port(self.selected_port)

    def select_port(self, port):
        """Altera a porta selecionada e atualiza os botões."""
        if self.is_running:
            # Não deixa alterar a porta enquanto está executando
            show_custom_messagebox(self, "Aviso", "Pare o NGROK ativo antes de mudar de porta!", icon="warning")
            return
            
        self.selected_port = port
        for p, btn in self.port_buttons.items():
            if p == port:
                btn.configure(fg_color="#1f538d")
            else:
                btn.configure(fg_color="#333333")

    def toggle_ngrok(self):
        """Inicia ou encerra o túnel do NGROK."""
        if self.is_running:
            self.stop_ngrok()
        else:
            self.start_ngrok()

    def is_ngrok_running_on_system(self):
        """Verifica se o ngrok.exe está rodando no sistema fora da aplicação."""
        try:
            cmd = ["tasklist", "/NH", "/FI", "IMAGENAME eq ngrok.exe"]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return "ngrok.exe" in res.stdout.lower()
        except Exception:
            return False

    def kill_all_system_ngrok(self):
        """Força o encerramento de todos os processos ngrok.exe rodando no sistema."""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False

    def start_ngrok(self):
        if not self.selected_port:
            show_custom_messagebox(self, "Aviso", "Selecione uma porta primeiro!", icon="warning")
            return

        # Verificar se já existe outra instância do NGROK rodando no sistema
        if self.is_ngrok_running_on_system():
            if show_custom_messagebox(
                self,
                "NGROK em Execução", 
                "Outra instância do NGROK já está em execução no sistema.\n\n"
                "Deseja encerrar todos os processos ativos do NGROK para iniciar este novo túnel?",
                icon="question",
                option_type="yesno"
            ):
                self.kill_all_system_ngrok()
                # Pequeno delay para o encerramento do processo ser concluído pelo sistema
                time.sleep(0.5)
            else:
                self.clear_console()
                self.append_log("[Erro] Inicialização abortada. Já existe um processo NGROK ativo no sistema.\n")
                return

        domain = self.config.get("public_url", DEFAULT_DOMAIN)
        port = self.selected_port

        self.clear_console()
        self.append_log(f"[App] Iniciando NGROK na porta {port} com o domínio {domain}...\n")

        # Configura o comando e oculta o console do CMD no Windows
        cmd = ["ngrok.exe", "http", f"--url=https://{domain}", str(port)]
        
        try:
            self.ngrok_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.is_running = True
            self.update_status_ui()

            # Inicia thread paralela para leitura de logs
            self.log_thread = threading.Thread(target=self.read_logs_loop, args=(self.ngrok_process,), daemon=True)
            self.log_thread.start()

            # Inicia thread paralela para buscar requisições recebidas pelo NGROK
            self.req_poll_thread = threading.Thread(target=self.poll_requests_loop, daemon=True)
            self.req_poll_thread.start()

            # Inicia a busca pela URL pública gerada
            self.check_api_url_attempts = 0
            self.after(1000, self.fetch_public_url)

        except Exception as e:
            self.append_log(f"[Erro] Falha ao iniciar NGROK: {e}\n")
            self.ngrok_process = None
            self.is_running = False
            self.update_status_ui()

    def stop_ngrok(self):
        self.is_running = False
        if self.ngrok_process:
            try:
                self.append_log("\n[App] Encerrando processo do NGROK...\n")
                self.ngrok_process.terminate()
                try:
                    self.ngrok_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.ngrok_process.kill()
            except Exception as e:
                print("Erro ao matar processo NGROK:", e)
            self.ngrok_process = None
            
        self.update_status_ui()
        self.set_offline_url_preview()

    def read_logs_loop(self, process):
        """Thread paralela para escutar a saída do terminal do NGROK."""
        while self.is_running and process.poll() is None:
            try:
                line = process.stdout.readline()
                if not line:
                    break
                log_text = line.decode('utf-8', errors='ignore')
                self.append_log(log_text)
                
                # Parser inteligente para alertas de atualizações do NGROK
                if "update" in log_text.lower() and "available" in log_text.lower():
                    self.after(0, self.trigger_update_warning)
            except Exception as e:
                print("Erro ao ler logs:", e)
                break
                
        exit_code = process.poll()
        if exit_code is not None and self.is_running:
            self.is_running = False
            self.ngrok_process = None
            self.after(0, self.on_process_unexpected_exit, exit_code)

    def on_process_unexpected_exit(self, exit_code):
        self.append_log(f"\n[App] NGROK encerrou de forma inesperada (Código de saída: {exit_code}).\n")
        self.update_status_ui()

    def poll_requests_loop(self):
        """Thread paralela para consultar a API local do NGROK e capturar as requisições."""
        seen_ids = set()
        while self.is_running and self.ngrok_process and self.ngrok_process.poll() is None:
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:4040/api/requests/http",
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=1) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    requests_list = data.get("requests", [])
                    new_requests = []
                    for r in requests_list:
                        req_id = r.get("id")
                        if req_id and req_id not in seen_ids:
                            new_requests.append(r)
                    
                    if new_requests:
                        # Ordena cronologicamente pelo campo 'start'
                        new_requests.sort(key=lambda x: x.get("start", ""))
                        for r in new_requests:
                            req_id = r.get("id")
                            seen_ids.add(req_id)
                            
                            req_info = r.get("request", {})
                            method = req_info.get("method", "GET")
                            path = req_info.get("uri", "/")
                            
                            resp = r.get("response")
                            status = ""
                            if resp:
                                status = resp.get("status", "")
                                if not status:
                                    status_code = resp.get("status_code")
                                    if status_code:
                                        status = str(status_code)
                            
                            duration = r.get("duration", 0)  # em microssegundos
                            duration_ms = duration / 1000.0
                            if duration_ms >= 1000.0:
                                duration_str = f"{duration_ms/1000.0:.2f}s"
                            else:
                                duration_str = f"{duration_ms:.1f}ms"
                                
                            start_time = r.get("start", "")
                            match = re.search(r'T(\d{2}:\d{2}:\d{2})', start_time)
                            if match:
                                time_str = f"[{match.group(1)}]"
                            else:
                                time_str = f"[{time.strftime('%H:%M:%S')}]"
                                
                            status_part = f" -> {status}" if status else ""
                            log_msg = f"{time_str} HTTP {method} {path}{status_part} ({duration_str})\n"
                            
                            self.after(0, self.append_log, log_msg)
            except Exception:
                pass
            time.sleep(1.0)

    def fetch_public_url(self):
        """Consulta a API local do NGROK para capturar a URL gerada."""
        if not self.is_running or not self.ngrok_process or self.ngrok_process.poll() is not None:
            return
            
        try:
            req = urllib.request.Request(
                self.tunnels_api_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=1) as response:
                data = json.loads(response.read().decode('utf-8'))
                tunnels = data.get("tunnels", [])
                if tunnels:
                    # Busca preferencialmente pelo túnel HTTPS
                    public_url = None
                    for t in tunnels:
                        if t.get("proto") == "https" or t.get("public_url", "").startswith("https"):
                            public_url = t.get("public_url")
                            break
                    if not public_url:
                        public_url = tunnels[0].get("public_url")
                        
                    if public_url:
                        self.after(0, self.set_public_url, public_url)
                        return
        except Exception:
            pass
            
        # Tenta novamente a cada 1 segundo por até 15 vezes
        self.check_api_url_attempts += 1
        if self.check_api_url_attempts < 15:
            self.after(1000, self.fetch_public_url)
        else:
            # Fallback caso a API demore demais ou não suba (e o processo ainda esteja ativo)
            if self.ngrok_process.poll() is None:
                domain = self.config.get("public_url", DEFAULT_DOMAIN)
                domain = sanitize_domain(domain)
                self.set_public_url(f"https://{domain}")

    def update_status_ui(self):
        """Atualiza o botão e texto de status."""
        if self.is_running:
            self.status_lbl.configure(
                text=f"● Ativo na Porta {self.selected_port}",
                text_color="#2ecc71"
            )
            self.start_btn.configure(
                text="PARAR NGROK",
                fg_color="#d9534f",
                hover_color="#c9302c"
            )
        else:
            self.status_lbl.configure(
                text="● Inativo",
                text_color="#95a5a6"
            )
            self.start_btn.configure(
                text="INICIAR NGROK",
                fg_color="#2ecc71",
                hover_color="#27ae60"
            )

    def set_public_url(self, url):
        self.url_entry.configure(state="normal")
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)
        self.url_entry.configure(state="readonly")

    def copy_url(self):
        url = self.url_entry.get().strip()
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.copy_btn.configure(text="✔")
            self.after(1500, lambda: self.copy_btn.configure(text="📋"))

    def open_url(self):
        url = self.url_entry.get().strip()
        if url and "http" in url:
            url = url.split(" ")[0]
            webbrowser.open(url)

    def trigger_update_warning(self):
        """Destaca o botão de atualizar caso encontre alertas nos logs."""
        if not self.update_highlighted:
            self.update_highlighted = True
            self.append_log("\n[Aviso] Nova versão do NGROK identificada nos logs! Clique no ícone de atualização (⟳) no cabeçalho para aplicar.\n")
            self.update_btn.configure(fg_color="#ff9900", hover_color="#cc7a00")

    def update_ngrok(self):
        """Dispara o comando ngrok update em segundo plano."""
        if self.is_running:
            show_custom_messagebox(self, "Aviso", "Pare o NGROK antes de atualizar!", icon="warning")
            return

        if not show_custom_messagebox(self, "Atualizar NGROK", "Deseja verificar e atualizar o NGROK executável agora?", icon="question", option_type="yesno"):
            return

        self.clear_console()
        self.append_log("[App] Executando verificação de atualizações...\n")
        self.update_btn.configure(state="disabled", text="...")
        self.update_btn.configure(fg_color="transparent", hover_color="#333333")  # Reseta cor de destaque
        self.update_highlighted = False

        def run_update():
            cmd = ["ngrok.exe", "update"]
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in iter(process.stdout.readline, b''):
                    self.append_log(line.decode('utf-8', errors='ignore'))
                process.wait()
                
                if process.returncode == 0:
                    self.after(0, lambda: show_custom_messagebox(self, "Atualização", "Verificação finalizada com sucesso!", icon="info"))
                else:
                    self.after(0, lambda: show_custom_messagebox(self, "Erro", f"Erro no comando de atualização. Código: {process.returncode}", icon="error"))
            except Exception as e:
                self.after(0, lambda: show_custom_messagebox(self, "Erro", f"Erro ao executar update: {e}", icon="error"))
            finally:
                self.after(0, self.reset_update_button)

        threading.Thread(target=run_update, daemon=True).start()

    def reset_update_button(self):
        self.update_btn.configure(state="normal", text="⟳", fg_color="transparent", hover_color="#333333")

    def append_log(self, text):
        self.console_text.configure(state="normal")
        self.console_text.insert("end", text)
        self.console_text.see("end")
        self.console_text.configure(state="disabled")

    def clear_console(self):
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")

    def open_settings(self):
        """Abre o pop-up de configurações."""
        if self.is_running:
            show_custom_messagebox(self, "Aviso", "Pare o NGROK antes de acessar as configurações!", icon="warning")
            return
        SettingsWindow(self, self.config, self.on_settings_saved)

    def set_offline_url_preview(self):
        """Define o campo public_url com o domínio atual indicando modo Offline."""
        domain = self.config.get("public_url", DEFAULT_DOMAIN)
        domain = sanitize_domain(domain)
        self.set_public_url(f"https://{domain} (Offline)")

    def on_settings_saved(self):
        """Callback acionado ao salvar configurações no pop-up."""
        self.config = load_or_create_config()
        self.create_port_buttons()
        self.set_offline_url_preview()

    def check_ngrok_executable(self):
        """Verifica se o ngrok.exe existe no diretório atual. Se não, inicia o download automático."""
        ngrok_path = "ngrok.exe"
        if not os.path.exists(ngrok_path):
            if show_custom_messagebox(
                self,
                "ngrok.exe Não Encontrado",
                "O executável do ngrok.exe não foi encontrado na pasta atual.\n\nDeseja realizar o download automático da versão mais recente?",
                icon="question",
                option_type="yesno"
            ):
                self.download_ngrok_auto()
            else:
                self.append_log("[Aviso] ngrok.exe não encontrado. Você não poderá iniciar o túnel até colocar o ngrok.exe na pasta.\n")
        else:
            # Se o executável já existe, valida se está registrado
            self.check_and_register_ngrok()

    def download_ngrok_auto(self):
        """Inicia uma thread em segundo plano para buscar e baixar o ngrok.exe mais recente."""
        self.start_btn.configure(state="disabled", text="BAIXANDO NGROK...")
        self.clear_console()
        self.append_log("[App] Buscando a versão mais recente do ngrok...\n")
        
        def run_download():
            import zipfile
            import io
            
            choco_api_url = "https://community.chocolatey.org/api/v2/Packages()?$filter=Id%20eq%20%27ngrok%27%20and%20IsLatestVersion"
            fallback_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
            download_url = None
            
            # 1. Tentar buscar dinamicamente
            try:
                req = urllib.request.Request(choco_api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as response:
                    xml_data = response.read().decode('utf-8')
                    match = re.search(r'(https://bin\.(?:ngrok\.com|equinox\.io)/[a-zA-Z0-9/._\-]+windows-amd64\.zip)', xml_data)
                    if match:
                        download_url = match.group(1).replace("^", "")
                        self.after(0, self.append_log, f"[App] Versão mais recente encontrada dinamicamente!\n")
            except Exception as e:
                self.after(0, self.append_log, f"[Aviso] Falha ao consultar API dinâmica: {e}. Usando link de fallback.\n")
            
            if not download_url:
                download_url = fallback_url
            
            self.after(0, self.append_log, f"[App] Baixando de: {download_url}\n")
            
            # 2. Efetuar o download
            try:
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    total_size = int(response.info().get('Content-Length', 0))
                    data = io.BytesIO()
                    downloaded = 0
                    block_size = 1024 * 64
                    
                    last_update_time = time.time()
                    while True:
                        block = response.read(block_size)
                        if not block:
                            break
                        data.write(block)
                        downloaded += len(block)
                        
                        current_time = time.time()
                        if current_time - last_update_time > 0.5:
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                self.after(0, self.append_log, f"[App] Download: {percent:.1f}% ({downloaded//1024} KB / {total_size//1024} KB)\n")
                            else:
                                self.after(0, self.append_log, f"[App] Baixando: {downloaded//1024} KB...\n")
                            last_update_time = current_time
                    
                    self.after(0, self.append_log, "[App] Download concluído! Extraindo executável...\n")
                    
                    # 3. Descompactar
                    with zipfile.ZipFile(data) as z:
                        ngrok_exe_name = None
                        for name in z.namelist():
                            if name.endswith("ngrok.exe"):
                                ngrok_exe_name = name
                                break
                        
                        if ngrok_exe_name:
                            with open("ngrok.exe", "wb") as f_out:
                                f_out.write(z.read(ngrok_exe_name))
                            self.after(0, self.append_log, "[App] ngrok.exe extraído e instalado com sucesso!\n")
                            self.after(0, lambda: show_custom_messagebox(self, "Sucesso", "O ngrok foi baixado e extraído com sucesso!", icon="info"))
                            # Verifica e solicita registro do token
                            self.after(500, self.check_and_register_ngrok)
                        else:
                            raise Exception("ngrok.exe não foi encontrado no pacote zip baixado.")
                            
            except Exception as e:
                self.after(0, self.append_log, f"[Erro] Falha ao baixar ou extrair o ngrok: {e}\n")
                self.after(0, lambda: show_custom_messagebox(self, "Erro", f"Falha ao baixar o ngrok: {e}", icon="error"))
            finally:
                self.after(0, self.reset_start_button)
                
        threading.Thread(target=run_download, daemon=True).start()

    def reset_start_button(self):
        """Restaura o estado do botão iniciar após download."""
        self.start_btn.configure(state="normal")
        self.update_status_ui()

    def is_ngrok_registered(self):
        """Verifica se o ngrok tem um authtoken configurado."""
        try:
            res = subprocess.run(
                ["ngrok.exe", "config", "check"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # Extrai o caminho do arquivo de configuração
            match = re.search(r'configuration file at\s+(.+)', res.stdout)
            if match:
                config_path = match.group(1).strip()
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Procura por authtoken na configuração (excluindo comentários)
                        for line in content.splitlines():
                            line_strip = line.strip()
                            if line_strip.startswith("authtoken:") and len(line_strip.split(":", 1)[1].strip()) > 0:
                                return True
        except Exception:
            pass
        return False

    def check_and_register_ngrok(self):
        """Verifica o registro do ngrok e solicita o token se necessário."""
        if not self.is_ngrok_registered():
            if show_custom_messagebox(
                self,
                "ngrok Não Registrado",
                "O ngrok não possui um Authtoken configurado nesta máquina. O token é necessário para iniciar os túneis.\n\nDeseja registrar o seu Authtoken agora?",
                icon="question",
                option_type="yesno"
            ):
                dialog = ctk.CTkInputDialog(text="Cole o seu Authtoken do ngrok:", title="Registro do ngrok")
                token = dialog.get_input()
                if token:
                    token = token.strip()
                    try:
                        cmd = ["ngrok.exe", "config", "add-authtoken", token]
                        res = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        if res.returncode == 0:
                            show_custom_messagebox(self, "Sucesso", "Authtoken registrado com sucesso!", icon="info")
                        else:
                            show_custom_messagebox(self, "Erro", f"Falha ao registrar token:\n{res.stderr.strip()}", icon="error")
                    except Exception as e:
                        show_custom_messagebox(self, "Erro", f"Falha ao executar o registro: {e}", icon="error")

    def check_for_launcher_updates(self, manual=False, force=False):
        """Verifica se há atualizações do launcher no GitHub."""
        def run_check():
            try:
                url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    latest_tag = data.get("tag_name", "").strip()
                    # Remove 'v' do início se existir
                    clean_latest = latest_tag.lstrip('v')
                    clean_current = LAUNCHER_VERSION.lstrip('v')
                    
                    if (clean_latest != clean_current and clean_current != "dev") or force:
                        # Encontra o asset do ZIP (ou EXE se não encontrar o ZIP)
                        assets = data.get("assets", [])
                        download_url = None
                        for asset in assets:
                            if asset.get("name") == "ngrok_launcher.zip":
                                download_url = asset.get("browser_download_url")
                                break
                        if not download_url:
                            for asset in assets:
                                if asset.get("name") == "ngrok_launcher.exe":
                                    download_url = asset.get("browser_download_url")
                                    break
                                
                        if download_url:
                            self.after(0, lambda: self.prompt_launcher_update(latest_tag, download_url))
                            return
                            
                if manual:
                    self.after(0, lambda: show_custom_messagebox(self, "Atualização", "Você já está usando a versão mais recente do launcher!", icon="info"))
            except Exception as e:
                if manual:
                    self.after(0, lambda: show_custom_messagebox(self, "Erro", f"Erro ao verificar atualizações: {e}", icon="error"))
                    
        threading.Thread(target=run_check, daemon=True).start()

    def prompt_launcher_update(self, latest_version, download_url):
        """Pergunta ao usuário se deseja atualizar o launcher."""
        if show_custom_messagebox(
            self,
            "Atualização do Launcher",
            f"Uma nova versão do launcher está disponível ({latest_version}).\n\nDeseja baixar e aplicar a atualização agora?",
            icon="question",
            option_type="yesno"
        ):
            self.apply_launcher_update(download_url)

    def apply_launcher_update(self, download_url):
        """Faz o download da nova versão e cria o script de auto-atualização."""
        self.clear_console()
        self.append_log("[Update] Iniciando atualização automática do launcher...\n")
        self.start_btn.configure(state="disabled", text="ATUALIZANDO LAUNCHER...")
        
        def run_update():
            try:
                is_frozen = getattr(sys, 'frozen', False)
                if not is_frozen:
                    self.after(0, self.append_log, "[Update] Executando em modo script. Atualização automática disponível apenas para a versão empacotada (.exe).\n")
                    self.after(0, lambda: show_custom_messagebox(self, "Atualização", "Você está rodando o launcher a partir do script Python. Baixe a nova versão .exe diretamente do GitHub.", icon="info"))
                    return

                exe_path = sys.executable
                exe_dir = os.path.dirname(exe_path)
                current_exe_name = os.path.basename(exe_path)
                zip_path = os.path.join(exe_dir, "last_version.zip")
                bat_path = os.path.join(exe_dir, "update_temp.bat")

                # 1. Download do ZIP
                self.after(0, self.append_log, "[Update] Baixando a nova versão em arquivo ZIP...\n")
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    new_zip_data = response.read()
                    
                # Grava o ZIP
                with open(zip_path, "wb") as f:
                    f.write(new_zip_data)
                    
                self.after(0, self.append_log, "[Update] Download concluído! Iniciando processo de substituição...\n")
                
                # 2. Criar script de atualização temporário (batch)
                bat_content = f"""@echo off
cd /d "{exe_dir}"
timeout /t 2 /nobreak >nul
taskkill /F /IM "{current_exe_name}" >nul 2>&1
powershell -Command "Expand-Archive -Path 'last_version.zip' -DestinationPath '.' -Force"
if exist "last_version.zip" del "last_version.zip"
powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Atualizacao concluida com sucesso!' + [char]10 + [char]10 + 'Voce ja pode iniciar o aplicativo novamente.', 'NGROK Launcher')"
del "%~f0"
"""
                with open(bat_path, "w", encoding="ansi") as f:
                    f.write(bat_content)
                    
                # 3. Executar o batch e fechar a aplicação atual
                subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
                self.after(0, self.on_closing)
                
            except Exception as e:
                self.after(0, self.append_log, f"[Erro] Falha ao atualizar o launcher: {e}\n")
                self.after(0, lambda: show_custom_messagebox(self, "Erro", f"Falha na atualização: {e}", icon="error"))
                self.after(0, self.reset_start_button)
                
        threading.Thread(target=run_update, daemon=True).start()

    def on_closing(self):
        """Encerra com segurança o processo do NGROK antes de fechar a janela."""
        if self.is_running:
            self.stop_ngrok()
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = NgrokLauncherApp()
    app.mainloop()
