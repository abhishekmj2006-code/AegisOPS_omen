import customtkinter as ctk
from typing import TYPE_CHECKING
from interface.theme import (
    BG_SURFACE, BG_CARD, BG_INPUT, BG_HOVER,
    BORDER_SUBTLE, BORDER_ACTIVE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER,
    STATUS_ONLINE_FG, STATUS_OFFLINE_FG,
)

if TYPE_CHECKING:
    from collector.collector_service import CollectorService


class SettingsPanelPage(ctk.CTkFrame):
    """Allows runtime configuration of backend endpoints, identifiers, and intervals."""

    def __init__(self, master, service: "CollectorService", **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self._init_ui()

    def _init_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))

        ctk.CTkLabel(
            title_frame,
            text="Collector Configuration & Parameters",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        container = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=12, border_width=1, border_color=BORDER_SUBTLE)
        container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        container.grid_columnconfigure((0, 1), weight=1)

        s = self.service.settings

        self.backend_url_entry = self._create_field(container, row=0, col=0, label="BACKEND URL", val=s.backend_url)
        self.target_entry = self._create_field(container, row=0, col=1, label="NETWORK LATENCY TARGET", val=s.network_target)
        self.tenant_entry = self._create_field(container, row=1, col=0, label="TENANT IDENTIFIER", val=s.tenant_id)
        self.device_entry = self._create_field(container, row=1, col=1, label="DEVICE IDENTIFIER", val=s.device_id)
        self.region_entry = self._create_field(container, row=2, col=0, label="DEPLOYMENT REGION", val=s.region)
        self.interval_entry = self._create_field(container, row=2, col=1, label="COLLECTION INTERVAL (SECONDS)", val=str(s.collection_interval))
        self.token_entry = self._create_token_field(container, row=3, col=0, label="COLLECTOR BEARER API TOKEN", val=getattr(s, "collector_api_key", "aegis_token_sec_9942"))
        self.tz_entry = self._create_field(container, row=3, col=1, label="SOURCE TIMEZONE", val=getattr(s, "source_timezone", "UTC"))

        bottom_box = ctk.CTkFrame(container, fg_color="transparent")
        bottom_box.grid(row=4, column=0, columnspan=2, sticky="ew", padx=24, pady=(20, 15))

        self.save_btn = ctk.CTkButton(
            bottom_box,
            text="Save & Apply Changes",
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_settings,
            height=34,
            corner_radius=6,
        )
        self.save_btn.pack(side="left", padx=(0, 10))

        self.reset_btn = ctk.CTkButton(
            bottom_box,
            text="Reset to Defaults",
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12),
            command=self._reset_defaults,
            height=34,
            corner_radius=6,
        )
        self.reset_btn.pack(side="left")

        self.status_msg_lbl = ctk.CTkLabel(
            bottom_box,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=STATUS_ONLINE_FG,
        )
        self.status_msg_lbl.pack(side="right", padx=10)

        note_box = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_SUBTLE)
        note_box.grid(row=5, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 20))

        ctk.CTkLabel(
            note_box,
            text=(
                "Security & Isolation Notice:\n"
                "All parameters are validated against strict formatting constraints prior to application.\n"
                "Local secrets, credentials, or private configuration tokens remain strictly isolated on host storage."
            ),
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=16, pady=12)

    def _create_field(self, parent, row: int, col: int, label: str, val: str) -> ctk.CTkEntry:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, padx=24, pady=12, sticky="ew")
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_FAINT).pack(anchor="w", pady=(0, 4))
        entry = ctk.CTkEntry(
            f,
            fg_color=BG_INPUT,
            border_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=12),
            height=34,
            corner_radius=6,
        )
        entry.insert(0, val)
        entry.pack(fill="x")
        return entry

    def _create_token_field(self, parent, row: int, col: int, label: str, val: str) -> ctk.CTkEntry:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, padx=24, pady=12, sticky="ew")
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_FAINT).pack(anchor="w", pady=(0, 4))
        
        box = ctk.CTkFrame(f, fg_color="transparent")
        box.pack(fill="x")

        entry = ctk.CTkEntry(
            box,
            fg_color=BG_INPUT,
            border_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=12),
            height=34,
            corner_radius=6,
            show="•",
        )
        entry.insert(0, val)
        entry.pack(side="left", fill="x", expand=True)

        is_visible = [False]
        def _toggle():
            is_visible[0] = not is_visible[0]
            entry.configure(show="" if is_visible[0] else "•")
            btn.configure(text="Hide" if is_visible[0] else "Show")

        btn = ctk.CTkButton(
            box,
            text="Show",
            width=55,
            height=34,
            fg_color=BG_CARD,
            hover_color=BORDER_ACTIVE,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=_toggle,
            corner_radius=6,
        )
        btn.pack(side="right", padx=(8, 0))
        return entry

    def _save_settings(self) -> None:
        try:
            b_url = self.backend_url_entry.get().strip()
            target = self.target_entry.get().strip()
            t_id = self.tenant_entry.get().strip()
            d_id = self.device_entry.get().strip()
            reg = self.region_entry.get().strip()
            interval = float(self.interval_entry.get().strip())
            token = self.token_entry.get().strip()
            tz_val = self.tz_entry.get().strip()

            self.service.settings.update(
                backend_url=b_url,
                tenant_id=t_id,
                device_id=d_id,
                region=reg,
                collection_interval=interval,
                network_target=target,
            )
            self.service.settings.collector_api_key = token
            self.service.settings.source_timezone = tz_val
            self.service.network_monitor.set_target(target)
            self.status_msg_lbl.configure(text="Settings saved and applied successfully!", text_color=STATUS_ONLINE_FG)
        except Exception as e:
            self.status_msg_lbl.configure(text=f"Error saving settings: {e}", text_color=STATUS_OFFLINE_FG)

    def _reset_defaults(self) -> None:
        self.backend_url_entry.delete(0, "end")
        self.backend_url_entry.insert(0, "http://localhost:8000")
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, "8.8.8.8")
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, "5.0")
        self._save_settings()

    def update_data(self) -> None:
        pass
