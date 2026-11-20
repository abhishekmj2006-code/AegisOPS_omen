import customtkinter as ctk
from typing import TYPE_CHECKING
from interface.theme import (
    BG_SURFACE, BG_CARD, BG_DEEP, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    METRIC_CPU, METRIC_RAM, METRIC_DISK, METRIC_NET,
    STATUS_ONLINE_FG, STATUS_OFFLINE_FG,
)

if TYPE_CHECKING:
    from collector.collector_service import CollectorService


class OverviewPage(ctk.CTkFrame):
    """Overview dashboard displaying host system specifications and current resource utilization."""

    def __init__(self, master, service: "CollectorService", **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self._init_ui()

    def _init_ui(self) -> None:
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=24, pady=(18, 12))

        ctk.CTkLabel(
            title_frame,
            text="System Overview & Telemetry",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="Real-time Host Telemetry Engine",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(side="right")

        # Metadata banner
        sys_info = self.service.system_monitor.get_system_info()
        info_frame = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        info_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=24, pady=(0, 16))
        info_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def add_spec(col: int, label: str, value: str):
            f = ctk.CTkFrame(info_frame, fg_color="transparent")
            f.grid(row=0, column=col, padx=18, pady=14, sticky="w")
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_FAINT).pack(anchor="w")
            ctk.CTkLabel(f, text=value, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_SECONDARY).pack(anchor="w", pady=(2, 0))

        add_spec(0, "HOST DEVICE", sys_info.get("hostname", "Unknown"))
        add_spec(1, "OPERATING SYSTEM", f"{sys_info.get('os')} {sys_info.get('os_release')}")
        add_spec(2, "SYSTEM ARCHITECTURE", sys_info.get("architecture", "x86_64"))
        add_spec(3, "SAMPLING INTERVAL", f"{self.service.settings.collection_interval:.1f}s Loop")

        # 4 Metric Cards
        self.cpu_card = self._create_metric_card("CPU USAGE", "0.0%", METRIC_CPU)
        self.cpu_card.grid(row=2, column=0, padx=(24, 8), pady=0, sticky="nsew")

        self.ram_card = self._create_metric_card("MEMORY ALLOCATION", "0.0%", METRIC_RAM)
        self.ram_card.grid(row=2, column=1, padx=8, pady=0, sticky="nsew")

        self.disk_card = self._create_metric_card("STORAGE CAPACITY", "0.0%", METRIC_DISK)
        self.disk_card.grid(row=2, column=2, padx=8, pady=0, sticky="nsew")

        self.net_card = self._create_metric_card("NETWORK LATENCY", "0.0 ms", METRIC_NET)
        self.net_card.grid(row=2, column=3, padx=(8, 24), pady=0, sticky="nsew")

        # Bottom Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        self.status_bar.grid(row=3, column=0, columnspan=4, sticky="ew", padx=24, pady=(16, 20))
        self.status_bar.grid_columnconfigure(1, weight=1)

        self.last_sync_lbl = ctk.CTkLabel(
            self.status_bar,
            text="Last Sample: Initializing...",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        )
        self.last_sync_lbl.grid(row=0, column=0, padx=18, pady=10, sticky="w")

        self.backend_indicator_lbl = ctk.CTkLabel(
            self.status_bar,
            text="Backend: Connecting...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_MUTED,
        )
        self.backend_indicator_lbl.grid(row=0, column=2, padx=18, pady=10, sticky="e")

    def _create_metric_card(self, title: str, default_val: str, accent_color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER_SUBTLE)
        card.grid_columnconfigure(0, weight=1)

        # Header tag row
        tag_frame = ctk.CTkFrame(card, fg_color="transparent")
        tag_frame.pack(fill="x", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            tag_frame,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        # Accent dot
        ctk.CTkLabel(
            tag_frame,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color=accent_color,
        ).pack(side="right")

        val_lbl = ctk.CTkLabel(
            card,
            text=default_val,
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        val_lbl.pack(anchor="w", padx=18, pady=(0, 6))

        sub_lbl = ctk.CTkLabel(
            card,
            text="Awaiting first sample...",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_FAINT,
        )
        sub_lbl.pack(anchor="w", padx=18, pady=(0, 16))

        bar = ctk.CTkProgressBar(card, progress_color=accent_color, fg_color=BG_DEEP, height=5, corner_radius=3)
        bar.set(0.0)
        bar.pack(fill="x", padx=18, pady=(0, 18))

        card.val_lbl = val_lbl  # type: ignore
        card.sub_lbl = sub_lbl  # type: ignore
        card.bar = bar          # type: ignore
        return card

    def update_data(self) -> None:
        raw = self.service.latest_raw_metrics
        if not raw:
            return

        cpu = raw.get("cpu_usage", 0.0)
        self.cpu_card.val_lbl.configure(text=f"{cpu:.1f}%")  # type: ignore
        self.cpu_card.sub_lbl.configure(text="Local multi-core load")  # type: ignore
        self.cpu_card.bar.set(min(1.0, cpu / 100.0))         # type: ignore

        ram = raw.get("ram_usage", 0.0)
        tot_ram = raw.get("ram_total_gb", 0.0)
        avail_ram = raw.get("ram_available_gb", 0.0)
        self.ram_card.val_lbl.configure(text=f"{ram:.1f}%")  # type: ignore
        self.ram_card.sub_lbl.configure(text=f"{avail_ram:.1f} GB free of {tot_ram:.1f} GB")  # type: ignore
        self.ram_card.bar.set(min(1.0, ram / 100.0))         # type: ignore

        disk = raw.get("disk_usage", 0.0)
        r_mb = raw.get("disk_read_mbs", 0.0)
        w_mb = raw.get("disk_write_mbs", 0.0)
        self.disk_card.val_lbl.configure(text=f"{disk:.1f}%")  # type: ignore
        self.disk_card.sub_lbl.configure(text=f"R: {r_mb:.1f} MB/s | W: {w_mb:.1f} MB/s")  # type: ignore
        self.disk_card.bar.set(min(1.0, disk / 100.0))        # type: ignore

        lat = raw.get("network_latency_ms", 0.0)
        loss = raw.get("packet_loss_percent", 0.0)
        self.net_card.val_lbl.configure(text=f"{lat:.1f} ms") # type: ignore
        self.net_card.sub_lbl.configure(text=f"Packet loss: {loss:.1f}%")  # type: ignore
        self.net_card.bar.set(min(1.0, lat / 200.0))          # type: ignore

        if self.service.last_collection_time:
            self.last_sync_lbl.configure(text=f"Last Collected: {self.service.last_collection_time}")

        is_online = self.service.connection_manager.is_online
        status_txt = self.service.connection_manager.status_text
        if is_online:
            self.backend_indicator_lbl.configure(
                text=f"Backend: {status_txt}",
                text_color=STATUS_ONLINE_FG,
            )
        else:
            self.backend_indicator_lbl.configure(
                text=f"Backend: {status_txt}",
                text_color=STATUS_OFFLINE_FG,
            )
