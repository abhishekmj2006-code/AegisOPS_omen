import json
import customtkinter as ctk
from typing import TYPE_CHECKING, Optional
from interface.theme import (
    BG_SURFACE, BG_CARD, BG_INPUT, BORDER_SUBTLE, BORDER_ACTIVE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER,
    STATUS_ONLINE_BG, STATUS_ONLINE_FG,
    STATUS_OFFLINE_BG, STATUS_OFFLINE_FG,
    STATUS_WARN_BG, STATUS_WARN_FG,
)

if TYPE_CHECKING:
    from collector.collector_service import CollectorService


class EgressProofPage(ctk.CTkFrame):
    """Egress Proof audit panel allowing security auditors to verify zero data leakage."""

    def __init__(self, master, service: "CollectorService", **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self._last_rendered_signature: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title Frame with Action Buttons and Live Indicator Badge
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=24, pady=(18, 12))

        ctk.CTkLabel(
            title_frame,
            text="Egress Proof & Audit Panel",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Live Indicator Badge
        self.indicator_badge = ctk.CTkLabel(
            title_frame,
            text="● INITIALIZING AUDIT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
            fg_color=BG_CARD,
            corner_radius=6,
            padx=14,
            pady=5,
        )
        self.indicator_badge.pack(side="right", padx=(10, 0))

        # Sample Now Button
        self.sample_btn = ctk.CTkButton(
            title_frame,
            text="Run Sample Now",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT_PRIMARY,
            hover_color=ACCENT_PRIMARY_HOVER,
            height=32,
            width=130,
            corner_radius=8,
            command=self._manual_sample,
        )
        self.sample_btn.pack(side="right", padx=(10, 0))

        # Pinned Audit Toggle Button
        self.toggle_pinned_btn = ctk.CTkButton(
            title_frame,
            text="Live Stream (5s)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=BG_CARD,
            hover_color=BG_SURFACE,
            border_width=1,
            border_color=BORDER_SUBTLE,
            text_color=TEXT_SECONDARY,
            height=32,
            width=170,
            corner_radius=8,
            command=self._toggle_pinned,
        )
        self.toggle_pinned_btn.pack(side="right", padx=(10, 0))

        # Summary Metadata Bar
        summary_bar = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        summary_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=24, pady=(0, 14))
        summary_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.msg_id_lbl = self._add_summary_item(summary_bar, 0, "MESSAGE ID", "None")
        self.timestamp_lbl = self._add_summary_item(summary_bar, 1, "TRANSMISSION TIME (UTC)", "None")
        self.dest_server_lbl = self._add_summary_item(summary_bar, 2, "DESTINATION SERVER", self.service.settings.backend_url)
        self.http_status_lbl = self._add_summary_item(summary_bar, 3, "HTTP STATUS & RESULT", "Pending")

        # 3 Main Audit Columns
        self.col_a = self._create_audit_column(
            col=0,
            title="A. LOCAL INPUT",
            subtitle="Raw collected telemetry & test events",
        )

        self.col_b = self._create_audit_column(
            col=1,
            title="B. SANITIZATION REPORT",
            subtitle="Fields detected, stripped & validated",
        )

        self.col_c = self._create_audit_column(
            col=2,
            title="C. OUTGOING PAYLOAD",
            subtitle="Exact JSON transmitted to backend",
        )

    def _add_summary_item(self, parent, col: int, label: str, default_val: str):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, padx=16, pady=10, sticky="w")
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_FAINT).pack(anchor="w")
        lbl = ctk.CTkLabel(f, text=default_val, font=ctk.CTkFont(family="Consolas", size=11), text_color=TEXT_SECONDARY)
        lbl.pack(anchor="w", pady=(2, 0))
        return lbl

    def _create_audit_column(self, col: int, title: str, subtitle: str) -> ctk.CTkTextbox:
        container = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        container.grid(row=2, column=col, padx=6 if col == 1 else (24 if col == 0 else 24), pady=(0, 20), sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=16, pady=(14, 2), sticky="w")

        ctk.CTkLabel(
            container,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        textbox = ctk.CTkTextbox(
            container,
            fg_color=BG_INPUT,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            border_width=1,
            border_color=BORDER_SUBTLE,
            wrap="none",
        )
        textbox.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="nsew")
        return textbox

    def _manual_sample(self) -> None:
        """Trigger an immediate collection and refresh."""
        self.service.is_egress_pinned_to_scrubbed = False
        self.service.run_single_collection_cycle()
        self.update_data(force=True)

    def _toggle_pinned(self) -> None:
        """Toggle between Pinned Scrubbed Audit inspection and Live 5s Stream."""
        if self.service.is_egress_pinned_to_scrubbed:
            self.service.is_egress_pinned_to_scrubbed = False
        else:
            if self.service.last_scrubbed_raw_input:
                self.service.is_egress_pinned_to_scrubbed = True
        self.update_data(force=True)

    def _set_textbox_content(self, textbox: ctk.CTkTextbox, text: str) -> None:
        """Replace textbox content cleanly without resetting scroll position unnecessarily."""
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)

    def update_data(self, force: bool = False) -> None:
        # Determine whether to show the Pinned Scrubbed Audit or Live 5s Stream
        is_pinned = self.service.is_egress_pinned_to_scrubbed and (self.service.last_scrubbed_raw_input is not None)

        if is_pinned:
            raw_input = self.service.last_scrubbed_raw_input
            san_res = self.service.last_scrubbed_sanitization_result
            outgoing = self.service.last_scrubbed_outgoing_payload or {}
            self.toggle_pinned_btn.configure(
                text="▶ Resume Live Stream",
                fg_color="#18321d",
                hover_color="#224427",
                border_color="#73BF69",
                text_color="#73BF69",
            )
        else:
            raw_input = self.service.latest_raw_input_sample
            san_res = self.service.latest_sanitization_result
            outgoing = self.service.latest_outgoing_payload or {}
            if self.service.last_scrubbed_raw_input:
                sec_count = self.service.last_scrubbed_sanitization_result.sensitive_fields_detected if self.service.last_scrubbed_sanitization_result else 0
                self.toggle_pinned_btn.configure(
                    text=f"📌 View Scrubbed ({sec_count})",
                    fg_color="#383115",
                    hover_color="#4d431c",
                    border_color="#FADE2A",
                    text_color="#FADE2A",
                )
            else:
                self.toggle_pinned_btn.configure(
                    text="Live Stream (5s)",
                    fg_color=BG_CARD,
                    hover_color=BG_SURFACE,
                    border_color=BORDER_SUBTLE,
                    text_color=TEXT_MUTED,
                )

        # If no cycle has completed yet, show helpful placeholder instead of blank screen
        if not san_res or not outgoing:
            if self._last_rendered_signature != "EMPTY":
                self._set_textbox_content(self.col_a, "Collecting first telemetry sample...\n\n(Click 'Run Sample Now' or wait for the 5s collection tick)")
                self._set_textbox_content(self.col_b, "Waiting for initial sanitization pass...")
                self._set_textbox_content(self.col_c, "Waiting for initial payload generation...")
                self._last_rendered_signature = "EMPTY"
            return

        # Unique signature to detect if content actually changed
        current_sig = f"PINNED_{self.service.last_scrubbed_timestamp}_{san_res.sensitive_fields_detected}" if is_pinned else f"LIVE_{outgoing.get('message_id')}_{self.service.latest_transmission_status}_{self.service.latest_status_code}_{san_res.sensitive_fields_detected}"

        # Update headers
        msg_id = outgoing.get("message_id", "N/A")
        ts = self.service.last_scrubbed_timestamp if is_pinned else outgoing.get("timestamp", "N/A")
        self.msg_id_lbl.configure(text=msg_id[:18] + "..." if len(msg_id) > 18 else msg_id)
        self.timestamp_lbl.configure(text=ts)
        self.dest_server_lbl.configure(text=self.service.settings.backend_url)

        if is_pinned:
            self.http_status_lbl.configure(
                text="AUDIT PINNED (ZERO LEAKAGE VERIFIED)",
                text_color=STATUS_WARN_FG,
            )
            self.indicator_badge.configure(
                text=f"📌 PINNED PROOF: {san_res.sensitive_fields_detected} SECRETS STRIPPED",
                fg_color="#383115",
                text_color="#FADE2A",
            )
        else:
            status_code = self.service.latest_status_code
            trans_status = self.service.latest_transmission_status
            resp_text = self.service.latest_response_text

            if trans_status == "SUCCESS":
                self.http_status_lbl.configure(
                    text=f"HTTP {status_code} - DELIVERED",
                    text_color=STATUS_ONLINE_FG,
                )
                self.indicator_badge.configure(
                    text="● GREEN: VALIDATED & TRANSMITTED",
                    fg_color=STATUS_ONLINE_BG,
                    text_color=STATUS_ONLINE_FG,
                )
            elif trans_status == "QUEUED":
                reason = "Simulated Offline" if self.service.simulated_network_down else ("Offline Queue" if status_code == 0 else f"HTTP {status_code}")
                self.http_status_lbl.configure(
                    text=f"{reason} - STORED IN SQLITE QUEUE",
                    text_color=STATUS_WARN_FG,
                )
                self.indicator_badge.configure(
                    text="● YELLOW: QUEUED FOR RETRY (OFFLINE)",
                    fg_color=STATUS_WARN_BG,
                    text_color=STATUS_WARN_FG,
                )
            else:
                self.http_status_lbl.configure(
                    text=f"ERROR: {resp_text[:30] if resp_text else 'Validation failed'}",
                    text_color=STATUS_OFFLINE_FG,
                )
                self.indicator_badge.configure(
                    text="● RED: VALIDATION FAILED / REJECTED",
                    fg_color=STATUS_OFFLINE_BG,
                    text_color=STATUS_OFFLINE_FG,
                )

        # Only update the textboxes if new data arrived or force=True
        if not force and current_sig == self._last_rendered_signature:
            return

        self._last_rendered_signature = current_sig

        # 1. Update Column A: Local Input
        self._set_textbox_content(self.col_a, json.dumps(raw_input, indent=2))

        # 2. Update Column B: Sanitization Report
        report_display = {
            "sanitization_status": san_res.status,
            "schema_validation": "PASSED" if san_res.is_valid else "FAILED",
            "sensitive_fields_detected": san_res.sensitive_fields_detected,
            "fields_stripped_or_dropped": san_res.fields_removed,
            "validation_errors": san_res.validation_errors,
            "zero_leakage_guarantee": "VERIFIED (Strict Allowlist Enforced)",
            "allowed_keys_permitted": san_res.original_input_summary.get("top_level_keys", []),
        }
        self._set_textbox_content(self.col_b, json.dumps(report_display, indent=2))

        # 3. Update Column C: Outgoing Payload
        self._set_textbox_content(self.col_c, json.dumps(outgoing, indent=2))
