import customtkinter as ctk
import threading
from typing import TYPE_CHECKING, Optional
from interface.theme import (
    BG_SURFACE, BG_CARD, BG_INPUT, BG_HOVER,
    BORDER_SUBTLE, BORDER_ACTIVE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER,
    STATUS_ONLINE_FG, STATUS_OFFLINE_FG, STATUS_WARN_FG,
)

if TYPE_CHECKING:
    from collector.collector_service import CollectorService


class ConnectionPanelPage(ctk.CTkFrame):
    """Monitors central backend connectivity and manages resilient offline SQLite queue delivery."""

    def __init__(self, master, service: "CollectorService", **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self._last_rendered_signature: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=24, pady=(18, 12))

        ctk.CTkLabel(
            title_frame,
            text="Connection & Resilient Offline Queue",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Top Stats Cards (4 cards)
        self.conn_card = self._create_stat_card("BACKEND CONNECTION", "CHECKING...", STATUS_WARN_FG)
        self.conn_card.grid(row=1, column=0, padx=(24, 6), pady=(0, 16), sticky="ew")

        self.pending_card = self._create_stat_card("PENDING OFFLINE QUEUE", "0", ACCENT_PRIMARY)
        self.pending_card.grid(row=1, column=1, padx=6, pady=(0, 16), sticky="ew")

        self.sent_card = self._create_stat_card("ACKNOWLEDGED & DELIVERED", "0", STATUS_ONLINE_FG)
        self.sent_card.grid(row=1, column=2, padx=6, pady=(0, 16), sticky="ew")

        self.failed_card = self._create_stat_card("RETRY ATTEMPTS", "0", STATUS_OFFLINE_FG)
        self.failed_card.grid(row=1, column=3, padx=(6, 24), pady=(0, 16), sticky="ew")

        # Main Table / Records Container
        main_box = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=12, border_width=1, border_color=BORDER_SUBTLE)
        main_box.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=24, pady=(0, 20))
        main_box.grid_columnconfigure(0, weight=1)
        main_box.grid_rowconfigure(1, weight=1)

        # Action Toolbar inside Table Box
        toolbar = ctk.CTkFrame(main_box, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(
            toolbar,
            text="Persistent SQLite Message Queue Log (At-Least-Once Delivery)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Status text for operations
        self.action_status_lbl = ctk.CTkLabel(
            toolbar,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT_PRIMARY,
        )
        self.action_status_lbl.pack(side="left", padx=16)

        # Action buttons
        self.clear_btn = ctk.CTkButton(
            toolbar,
            text="Reset Queue to 0",
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._reset_queue,
            height=30,
            width=130,
            corner_radius=6,
        )
        self.clear_btn.pack(side="right", padx=(8, 0))

        self.retry_btn = ctk.CTkButton(
            toolbar,
            text="Manual Retry Now",
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_PRIMARY_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._manual_retry,
            height=30,
            width=135,
            corner_radius=6,
        )
        self.retry_btn.pack(side="right", padx=(8, 0))

        self.outage_btn = ctk.CTkButton(
            toolbar,
            text="Simulate Disconnect",
            fg_color="#475569",
            hover_color="#334155",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_outage,
            height=30,
            width=145,
            corner_radius=6,
        )
        self.outage_btn.pack(side="right", padx=(8, 0))

        # Textbox table representing queued records
        self.queue_textbox = ctk.CTkTextbox(
            main_box,
            fg_color=BG_INPUT,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            border_width=1,
            border_color=BORDER_SUBTLE,
            wrap="none",
        )
        self.queue_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def _create_stat_card(self, title: str, default_val: str, accent_color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEXT_FAINT,
        ).pack(anchor="w", padx=16, pady=(12, 2))

        val_lbl = ctk.CTkLabel(
            card,
            text=default_val,
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=accent_color,
        )
        val_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        card.val_lbl = val_lbl  # type: ignore
        return card

    def _reset_queue(self) -> None:
        """Wipe local queue records back to 0."""
        self.service.offline_queue.clear_all()
        self.action_status_lbl.configure(text="Queue reset to 0 records", text_color=STATUS_ONLINE_FG)
        self.update_data(force=True)

    def _manual_retry(self) -> None:
        """Trigger immediate offline queue flush in background to avoid any UI freeze."""
        self.retry_btn.configure(state="disabled", text="Retrying...")
        self.action_status_lbl.configure(text="Flushing offline queue...", text_color=ACCENT_PRIMARY)

        def _worker():
            sent, failed = self.service.trigger_manual_retry()
            def _done():
                self.retry_btn.configure(state="normal", text="Manual Retry Now")
                if sent > 0:
                    self.action_status_lbl.configure(text=f"Flushed: {sent} delivered!", text_color=STATUS_ONLINE_FG)
                elif failed > 0:
                    self.action_status_lbl.configure(text=f"Offline: {failed} retained in queue", text_color=STATUS_OFFLINE_FG)
                else:
                    self.action_status_lbl.configure(text="Queue is clean (0 pending)", text_color=TEXT_MUTED)
                self.update_data(force=True)
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_outage(self) -> None:
        """Toggle simulated network outage for offline queue verification."""
        is_down = self.service.toggle_simulated_network()
        if is_down:
            self.outage_btn.configure(text="Restore Network", fg_color="#991b1b", hover_color="#7f1d1d")
            self.action_status_lbl.configure(text="Network forced OFFLINE: Messages queue to SQLite", text_color=STATUS_WARN_FG)
        else:
            self.outage_btn.configure(text="Simulate Disconnect", fg_color="#475569", hover_color="#334155")
            self.action_status_lbl.configure(text="Network RESTORED. Flushing queue...", text_color=STATUS_ONLINE_FG)
            self._manual_retry()
        self.update_data(force=True)

    def update_data(self, force: bool = False) -> None:
        """Refresh queue counts and record listings without wiping out user scroll position."""
        stats = self.service.offline_queue.get_stats()
        pending_count = stats.get("pending", 0)
        sent_count = stats.get("sent", 0)
        failed_count = stats.get("failed_attempts", 0)

        self.pending_card.val_lbl.configure(text=str(pending_count))          # type: ignore
        self.sent_card.val_lbl.configure(text=str(sent_count))                # type: ignore
        self.failed_card.val_lbl.configure(text=str(failed_count))            # type: ignore

        is_online = self.service.connection_manager.is_online
        status_txt = self.service.connection_manager.status_text
        if is_online:
            self.conn_card.val_lbl.configure(text="ONLINE", text_color=STATUS_ONLINE_FG)       # type: ignore
        else:
            self.conn_card.val_lbl.configure(text=status_txt, text_color=STATUS_OFFLINE_FG)     # type: ignore

        # Keep sync with simulated disconnect button state
        if self.service.simulated_network_down:
            if self.outage_btn.cget("text") != "Restore Network":
                self.outage_btn.configure(text="Restore Network", fg_color="#991b1b", hover_color="#7f1d1d")
        else:
            if self.outage_btn.cget("text") != "Simulate Disconnect":
                self.outage_btn.configure(text="Simulate Disconnect", fg_color="#475569", hover_color="#334155")

        # Signature of current state to avoid flickering rewrite if no records changed
        current_sig = f"{pending_count}_{sent_count}_{failed_count}_{status_txt}_{self.service.total_messages_processed}"
        if not force and current_sig == self._last_rendered_signature:
            return

        self._last_rendered_signature = current_sig

        # Populate queue log
        recent = self.service.offline_queue.get_recent_messages(limit=35)
        self.queue_textbox.configure(state="normal")
        self.queue_textbox.delete("1.0", "end")

        header = f"{'MESSAGE ID':<38} | {'STATUS':<9} | {'RETRIES':<7} | {'CREATED AT (UTC)':<24} | {'DETAILS'}\n"
        divider = "─" * 115 + "\n"
        self.queue_textbox.insert("end", header)
        self.queue_textbox.insert("end", divider)

        if not recent:
            self.queue_textbox.insert("end", "  (Queue is completely clean: 0 records in SQLite)\n")
        else:
            for item in recent:
                mid = item.get("message_id", "")
                st = item.get("status", "")
                status_display = "★ PENDING" if st == "PENDING" else st
                retries = str(item.get("retry_count", 0))
                created = item.get("created_at", "")[:19]
                err = item.get("error_message") or "Acknowledged by server"
                line = f"{mid:<38} | {status_display:<9} | {retries:<7} | {created:<24} | {err[:35]}\n"
                self.queue_textbox.insert("end", line)
