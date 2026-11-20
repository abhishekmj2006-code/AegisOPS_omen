import customtkinter as ctk
from typing import Dict, Optional

from collector.collector_service import CollectorService
from config.settings import get_settings
from interface.overview import OverviewPage
from interface.system_monitor_panel import SystemMonitorPage
from interface.security_panel import SecurityPanelPage
from interface.egress_panel import EgressProofPage
from interface.connection_panel import ConnectionPanelPage
from interface.settings_panel import SettingsPanelPage
from interface.theme import (
    BG_DEEP, BG_SIDEBAR, BG_SURFACE, BG_CARD, BG_HOVER,
    BORDER_SUBTLE, BORDER_ACTIVE, BORDER_ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER,
    STATUS_ONLINE_BG, STATUS_ONLINE_FG,
    STATUS_OFFLINE_BG, STATUS_OFFLINE_FG,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AegisApp(ctk.CTk):
    """Primary desktop GUI application container with enterprise dark styling."""

    def __init__(self, service: Optional[CollectorService] = None) -> None:
        super().__init__()

        self.service = service or CollectorService(get_settings())

        self.title("AegisOPS — Secure IT Monitoring Platform | Local Collector")
        self.geometry("1220x780")
        self.minsize(1050, 700)
        self.configure(fg_color=BG_DEEP)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_page_name = "overview"
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        self._init_sidebar()
        self._init_main_area()
        self._init_pages()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(500, self._periodic_refresh)

    def _init_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=250, fg_color=BG_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Brand header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=20, pady=(24, 16))

        logo_row = ctk.CTkFrame(brand_frame, fg_color="transparent")
        logo_row.pack(fill="x")

        # Visual icon pill
        icon_badge = ctk.CTkLabel(
            logo_row,
            text="AE",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT_PRIMARY,
            text_color="#ffffff",
            corner_radius=6,
            width=28,
            height=28,
        )
        icon_badge.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_box,
            text="AegisOPS",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="SECURE LOCAL COLLECTOR",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEXT_FAINT,
        ).pack(anchor="w")

        # Subtle separator
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER_SUBTLE)
        sep.pack(fill="x", padx=16, pady=(8, 14))

        # Nav items (Clean, professional labels)
        nav_items = [
            ("overview", "System Overview"),
            ("monitor", "Telemetry Graphs"),
            ("security", "Security & Sanitizer"),
            ("egress", "Egress Proof Audit"),
            ("connection", "Connection & Queue"),
            ("settings", "Collector Settings"),
        ]

        self.nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=12, pady=0)

        for page_id, label in nav_items:
            btn = ctk.CTkButton(
                self.nav_container,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
                anchor="w",
                fg_color="transparent",
                text_color=TEXT_MUTED,
                hover_color=BG_HOVER,
                height=40,
                corner_radius=8,
                command=lambda p=page_id: self.show_page(p),
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[page_id] = btn

        # Footer engine card
        footer = ctk.CTkFrame(self.sidebar, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        footer.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkLabel(
            footer,
            text="COLLECTOR ENGINE",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEXT_FAINT,
        ).pack(anchor="w", padx=14, pady=(12, 2))

        status_row = ctk.CTkFrame(footer, fg_color="transparent")
        status_row.pack(anchor="w", padx=14, pady=(0, 12))

        dot = ctk.CTkLabel(
            status_row,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color=STATUS_ONLINE_FG,
        )
        dot.pack(side="left", padx=(0, 6))

        self.engine_status_lbl = ctk.CTkLabel(
            status_row,
            text="RUNNING ACTIVE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        )
        self.engine_status_lbl.pack(side="left")

    def _init_main_area(self) -> None:
        self.main_container = ctk.CTkFrame(self, fg_color=BG_DEEP, corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header bar
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color=BG_SURFACE, height=54, corner_radius=0, border_width=1, border_color=BORDER_SUBTLE)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(1, weight=1)

        # Breadcrumbs
        crumb_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        crumb_frame.grid(row=0, column=0, padx=24, pady=12, sticky="w")

        ctk.CTkLabel(
            crumb_frame,
            text="LOCAL COLLECTOR  /  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_FAINT,
        ).pack(side="left")

        self.top_page_title = ctk.CTkLabel(
            crumb_frame,
            text="SYSTEM OVERVIEW",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self.top_page_title.pack(side="left")

        # Right badges
        right_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_frame.grid(row=0, column=2, padx=24, pady=10, sticky="e")

        self.queue_badge = ctk.CTkLabel(
            right_frame,
            text="Queue: 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=BG_DEEP,
            text_color=TEXT_MUTED,
            corner_radius=6,
            padx=12,
            pady=4,
        )
        self.queue_badge.pack(side="left", padx=(0, 10))

        self.top_conn_badge = ctk.CTkLabel(
            right_frame,
            text="● ONLINE",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=STATUS_ONLINE_BG,
            text_color=STATUS_ONLINE_FG,
            corner_radius=6,
            padx=12,
            pady=4,
        )
        self.top_conn_badge.pack(side="left")

        # Content area
        self.page_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.page_frame.grid(row=1, column=0, sticky="nsew")
        self.page_frame.grid_columnconfigure(0, weight=1)
        self.page_frame.grid_rowconfigure(0, weight=1)

    def _init_pages(self) -> None:
        self.pages: Dict[str, ctk.CTkFrame] = {
            "overview": OverviewPage(self.page_frame, self.service),
            "monitor": SystemMonitorPage(self.page_frame, self.service),
            "security": SecurityPanelPage(self.page_frame, self.service, on_navigate=self.show_page),
            "egress": EgressProofPage(self.page_frame, self.service),
            "connection": ConnectionPanelPage(self.page_frame, self.service),
            "settings": SettingsPanelPage(self.page_frame, self.service),
        }
        self.show_page("overview")

    def show_page(self, page_name: str) -> None:
        self.current_page_name = page_name

        for name, page in self.pages.items():
            if name == page_name:
                page.grid(row=0, column=0, sticky="nsew")
                page.update_data()
            else:
                page.grid_forget()

        titles = {
            "overview": "SYSTEM OVERVIEW",
            "monitor": "TELEMETRY GRAPHS",
            "security": "SECURITY & ZERO-LEAKAGE SANITIZER",
            "egress": "EGRESS PROOF AUDIT PANEL",
            "connection": "CONNECTION & OFFLINE QUEUE",
            "settings": "CONFIGURATION SETTINGS",
        }
        self.top_page_title.configure(text=titles.get(page_name, page_name.upper()))

        # Update button active state
        for name, btn in self.nav_buttons.items():
            if name == page_name:
                btn.configure(
                    fg_color=BG_CARD,
                    text_color=TEXT_PRIMARY,
                    border_width=1,
                    border_color=BORDER_ACCENT,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_MUTED,
                    border_width=0,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
                )

    def _periodic_refresh(self) -> None:
        try:
            curr = self.pages.get(self.current_page_name)
            if curr:
                curr.update_data()

            # Update top queue badge
            q_size = self.service.offline_queue.get_queue_size()
            self.queue_badge.configure(text=f"Queue: {q_size}")
            if q_size > 0:
                self.queue_badge.configure(text_color="#fbbf24", fg_color="#451a03")
            else:
                self.queue_badge.configure(text_color=TEXT_MUTED, fg_color=BG_DEEP)

            # Update top connection badge
            is_online = self.service.connection_manager.is_online
            if is_online:
                self.top_conn_badge.configure(
                    text="● ONLINE",
                    fg_color=STATUS_ONLINE_BG,
                    text_color=STATUS_ONLINE_FG,
                )
            else:
                self.top_conn_badge.configure(
                    text="● OFFLINE",
                    fg_color=STATUS_OFFLINE_BG,
                    text_color=STATUS_OFFLINE_FG,
                )
        except Exception:
            pass

        self.after(1000, self._periodic_refresh)

    def on_closing(self) -> None:
        try:
            self.service.stop()
        except Exception:
            pass
        self.destroy()
