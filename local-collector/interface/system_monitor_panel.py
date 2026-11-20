import collections
from typing import TYPE_CHECKING, Deque
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from interface.theme import (
    BG_DEEP, BG_SURFACE, BG_CARD, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    METRIC_CPU, METRIC_RAM, METRIC_DISK, METRIC_NET,
)

if TYPE_CHECKING:
    from collector.collector_service import CollectorService


class SystemMonitorPage(ctk.CTkFrame):
    """Real-time multi-metric graph view showing CPU, RAM, Disk I/O, and Network history."""

    def __init__(self, master, service: "CollectorService", max_history: int = 30, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self.max_history = max_history

        self.cpu_history: Deque[float] = collections.deque(maxlen=max_history)
        self.ram_history: Deque[float] = collections.deque(maxlen=max_history)
        self.disk_history: Deque[float] = collections.deque(maxlen=max_history)
        self.latency_history: Deque[float] = collections.deque(maxlen=max_history)

        self._init_ui()

    def _init_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))

        ctk.CTkLabel(
            title_frame,
            text="Live Resource Telemetry Graphs",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="Real-time sliding window (last 30 samples)",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(side="right")

        # Container card for Matplotlib canvas
        chart_card = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=12, border_width=1, border_color=BORDER_SUBTLE)
        chart_card.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        chart_card.grid_columnconfigure(0, weight=1)
        chart_card.grid_rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(8.5, 5.2), dpi=96, facecolor=BG_SURFACE)
        self.fig.subplots_adjust(left=0.07, right=0.96, top=0.92, bottom=0.09, hspace=0.38, wspace=0.22)

        self.ax_cpu = self.fig.add_subplot(221)
        self.ax_ram = self.fig.add_subplot(222)
        self.ax_disk = self.fig.add_subplot(223)
        self.ax_net = self.fig.add_subplot(224)

        self._style_axis(self.ax_cpu, "CPU Utilization (%)", METRIC_CPU, (0, 100))
        self._style_axis(self.ax_ram, "Memory Allocated (%)", METRIC_RAM, (0, 100))
        self._style_axis(self.ax_disk, "Disk Utilization (%)", METRIC_DISK, (0, 100))
        self._style_axis(self.ax_net, "Latency (ms)", METRIC_NET, (0, 150))

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_card)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(bg=BG_SURFACE, highlightthickness=0)
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    def _style_axis(self, ax, title: str, color: str, ylim: tuple) -> None:
        ax.set_facecolor(BG_CARD)
        ax.set_title(title, color=TEXT_SECONDARY, fontsize=10, weight="bold", pad=8)
        ax.tick_params(colors=TEXT_FAINT, labelsize=8)
        ax.set_ylim(*ylim)
        ax.grid(True, linestyle=":", alpha=0.15, color="#64748b")
        for spine in ax.spines.values():
            spine.set_color(BORDER_SUBTLE)
            spine.set_linewidth(1.0)

    def update_data(self) -> None:
        raw = self.service.latest_raw_metrics
        if not raw:
            return

        self.cpu_history.append(raw.get("cpu_usage", 0.0))
        self.ram_history.append(raw.get("ram_usage", 0.0))
        self.disk_history.append(raw.get("disk_usage", 0.0))
        self.latency_history.append(raw.get("network_latency_ms", 0.0))

        self.ax_cpu.cla()
        self._style_axis(self.ax_cpu, f"CPU: {self.cpu_history[-1]:.1f}%", METRIC_CPU, (0, 100))
        self.ax_cpu.plot(list(self.cpu_history), color=METRIC_CPU, linewidth=1.8, antialiased=True)
        self.ax_cpu.fill_between(range(len(self.cpu_history)), list(self.cpu_history), color=METRIC_CPU, alpha=0.12)

        self.ax_ram.cla()
        self._style_axis(self.ax_ram, f"RAM: {self.ram_history[-1]:.1f}%", METRIC_RAM, (0, 100))
        self.ax_ram.plot(list(self.ram_history), color=METRIC_RAM, linewidth=1.8, antialiased=True)
        self.ax_ram.fill_between(range(len(self.ram_history)), list(self.ram_history), color=METRIC_RAM, alpha=0.12)

        self.ax_disk.cla()
        self._style_axis(self.ax_disk, f"Disk: {self.disk_history[-1]:.1f}%", METRIC_DISK, (0, 100))
        self.ax_disk.plot(list(self.disk_history), color=METRIC_DISK, linewidth=1.8, antialiased=True)
        self.ax_disk.fill_between(range(len(self.disk_history)), list(self.disk_history), color=METRIC_DISK, alpha=0.12)

        self.ax_net.cla()
        max_lat = max(100.0, max(self.latency_history) + 20)
        self._style_axis(self.ax_net, f"Latency: {self.latency_history[-1]:.1f} ms", METRIC_NET, (0, max_lat))
        self.ax_net.plot(list(self.latency_history), color=METRIC_NET, linewidth=1.8, antialiased=True)
        self.ax_net.fill_between(range(len(self.latency_history)), list(self.latency_history), color=METRIC_NET, alpha=0.12)

        try:
            self.canvas.draw_idle()
        except Exception:
            pass
