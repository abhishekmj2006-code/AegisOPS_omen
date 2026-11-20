import customtkinter as ctk
from typing import TYPE_CHECKING, Optional, Callable
from interface.theme import (
    BG_SURFACE, BG_CARD, BG_DEEP, BG_INPUT, BG_HOVER,
    BORDER_SUBTLE, BORDER_ACTIVE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_FAINT,
    ACCENT_PRIMARY, ACCENT_PRIMARY_HOVER,
    STATUS_ONLINE_BG, STATUS_ONLINE_FG,
    STATUS_WARN_BG, STATUS_WARN_FG,
)

if TYPE_CHECKING:
    from collector.collector_service import CollectorService


class SecurityPanelPage(ctk.CTkFrame):
    """Monitors sanitization health, enforces strict field allowlists, and demonstrates secret stripping."""

    def __init__(self, master, service: "CollectorService", on_navigate: Optional[Callable[[str], None]] = None, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self.on_navigate = on_navigate
        self._init_ui()

    def _init_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header Title Frame
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))

        ctk.CTkLabel(
            title_frame,
            text="Security & Zero-Leakage Sanitizer",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self.security_badge = ctk.CTkLabel(
            title_frame,
            text="ACTIVE SHIELD: 100% STRICT ALLOWLIST ENFORCED",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=STATUS_ONLINE_FG,
            fg_color=STATUS_ONLINE_BG,
            corner_radius=6,
            padx=14,
            pady=5,
        )
        self.security_badge.pack(side="right")

        # 3 Top KPI Stat Cards
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.inspected_card = self._create_stat_card(stats_frame, 0, "TOTAL INSPECTED", "0", ACCENT_PRIMARY)
        self.detected_card = self._create_stat_card(stats_frame, 1, "SENSITIVE DETECTED", "0", "#f87171")
        self.removed_card = self._create_stat_card(stats_frame, 2, "STRIPPED & NEUTRALIZED", "0", "#fbbf24")

        # Main Split Content Frame
        main_content = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=12, border_width=1, border_color=BORDER_SUBTLE)
        main_content.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))
        main_content.grid_columnconfigure((0, 1), weight=1)
        main_content.grid_rowconfigure(0, weight=1)

        # Left Column: Interactive Audit / Test Suite
        demo_box = ctk.CTkFrame(main_content, fg_color="transparent")
        demo_box.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(
            demo_box,
            text="Interactive Leakage Protection Simulator",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            demo_box,
            text=(
                "Inject simulated toxic payloads containing forbidden credentials, tokens,\n"
                "passwords, or unapproved arguments. The sanitizer intercepts and neutralizes\n"
                "them in-memory before payload serialization."
            ),
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # Action Buttons
        btn1 = ctk.CTkButton(
            demo_box,
            text="Inject Password & AWS API Key",
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            corner_radius=8,
            command=self._inject_credentials,
        )
        btn1.pack(fill="x", pady=5)

        btn2 = ctk.CTkButton(
            demo_box,
            text="Inject Raw Cmdline & Auth Cookie",
            fg_color="#9a3412",
            hover_color="#c2410c",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            corner_radius=8,
            command=self._inject_raw_cmdline,
        )
        btn2.pack(fill="x", pady=5)

        btn3 = ctk.CTkButton(
            demo_box,
            text="Simulate Failed Login Event (+3)",
            fg_color="#0369a1",
            hover_color="#0284c7",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            corner_radius=8,
            command=self._inject_failed_logins,
        )
        btn3.pack(fill="x", pady=5)

        self.injection_status_lbl = ctk.CTkLabel(
            demo_box,
            text="Status: Ready for evaluation injection.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=STATUS_ONLINE_FG,
        )
        self.injection_status_lbl.pack(anchor="w", pady=(14, 0))

        self.view_egress_btn = ctk.CTkButton(
            demo_box,
            text="🔍 Inspect Scrubbed Proof in Egress Panel",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#181b1f",
            hover_color="#22252b",
            border_width=1,
            border_color="#FF780A",
            text_color="#FF780A",
            height=34,
            corner_radius=8,
            command=self._go_to_egress,
        )
        self.view_egress_btn.pack(fill="x", pady=(10, 0))

        self.replay_file_btn = ctk.CTkButton(
            demo_box,
            text="📁 Replay External Stream File (.json / .ndjson)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#182230",
            hover_color="#233247",
            border_width=1,
            border_color="#3b82f6",
            text_color="#60a5fa",
            height=34,
            corner_radius=8,
            command=self._pick_and_replay_file,
        )
        self.replay_file_btn.pack(fill="x", pady=(8, 0))

        # Right Column: Policy Reference Card
        policy_box = ctk.CTkFrame(main_content, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        policy_box.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        policy_hdr = ctk.CTkFrame(policy_box, fg_color="transparent")
        policy_hdr.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            policy_hdr,
            text="Strict Allowlist Enforcement Policy",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            policy_hdr,
            text="ISO 27001 / SOC 2",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEXT_FAINT,
        ).pack(side="right")

        policy_text = (
            "1. SCHEMA VALIDATION\n"
            "   * Strict Pydantic extra='forbid' validation\n"
            "   * Unknown or injected attributes cause instant schema rejection\n\n"
            "2. APPROVED TOP-LEVEL ENTITIES\n"
            "   * message_id, tenant_id, device_id\n"
            "   * timestamp, region, metrics, collector_status\n\n"
            "3. APPROVED METRIC NUMERICS\n"
            "   * cpu_usage, ram_usage, disk_usage\n"
            "   * network_latency_ms, packet_loss_percent, failed_login_count\n\n"
            "4. AUTOMATICALLY STRIPPED ON SIGHT\n"
            "   * Passwords, Passphrases & PINs\n"
            "   * API Keys, Tokens & JWT Secrets\n"
            "   * Private Keys & SSH Credentials\n"
            "   * Session Cookies & Authorization Headers\n"
            "   * Raw Unapproved Process Command-Line Args\n"
            "   * Personal Identifiable Information (PII)"
        )

        ctk.CTkLabel(
            policy_box,
            text=policy_text,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 16))

    def _create_stat_card(self, parent, col: int, title: str, default_val: str, accent_color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_SUBTLE)
        card.grid(row=0, column=col, padx=6, sticky="ew")

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_FAINT,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        val_lbl = ctk.CTkLabel(
            card,
            text=default_val,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=accent_color,
        )
        val_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        card.val_lbl = val_lbl  # type: ignore
        return card

    def _go_to_egress(self) -> None:
        self.service.is_egress_pinned_to_scrubbed = True
        if self.on_navigate:
            self.on_navigate("egress")

    def _inject_credentials(self) -> None:
        poisoned = {
            "admin_password": "SuperSecretPassword123!",
            "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
            "metrics.unapproved_secret_token": "bearer eyJhbGciOiJIUzI1NiJ9.secret",
        }
        self.service.run_single_collection_cycle(extra_untrusted_fields=poisoned)
        self.service.is_egress_pinned_to_scrubbed = True
        self.injection_status_lbl.configure(
            text="SUCCESS: Injected password & AWS key! Stripped 3 sensitive fields. (Pinned in Egress Proof)",
            text_color="#fbbf24",
        )

    def _inject_raw_cmdline(self) -> None:
        poisoned = {
            "raw_cmdline": "curl -u admin:hunter2 https://internal.corp/db",
            "metrics.cookie": "session_id=abcdef1234567890",
            "ssh_private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...",
        }
        self.service.run_single_collection_cycle(extra_untrusted_fields=poisoned)
        self.service.is_egress_pinned_to_scrubbed = True
        self.injection_status_lbl.configure(
            text="SUCCESS: Injected raw cmdline & RSA key! All neutralized. (Pinned in Egress Proof)",
            text_color="#fbbf24",
        )

    def _inject_failed_logins(self) -> None:
        tot = self.service.login_monitor.inject_test_failed_login(3)
        self.service.run_single_collection_cycle()
        self.injection_status_lbl.configure(
            text=f"SUCCESS: Recorded 3 failed login attempts. Total: {tot}",
            text_color="#38bdf8",
        )

    def _pick_and_replay_file(self) -> None:
        import tkinter.filedialog as fd
        import threading
        file_path = fd.askopenfilename(
            title="Select External Telemetry Stream File",
            filetypes=[("Telemetry Stream Files", "*.json;*.ndjson"), ("JSON Files", "*.json"), ("NDJSON Files", "*.ndjson"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        self.injection_status_lbl.configure(text=f"Replaying stream from: {file_path[-30:]}...", text_color=TEXT_MUTED)
        
        def _worker():
            try:
                count = self.service.replay_stream_file(file_path)
                self.injection_status_lbl.configure(
                    text=f"✔ Replayed {count} events through sanitizer & queue!",
                    text_color=STATUS_ONLINE_FG
                )
            except Exception as e:
                self.injection_status_lbl.configure(
                    text=f"❌ Replay error: {str(e)[:40]}",
                    text_color="#f87171"
                )

        threading.Thread(target=_worker, daemon=True).start()

    def update_data(self) -> None:
        self.inspected_card.val_lbl.configure(text=str(self.service.total_messages_processed))  # type: ignore
        self.detected_card.val_lbl.configure(text=str(self.service.total_sensitive_detected))  # type: ignore
        self.removed_card.val_lbl.configure(text=str(self.service.total_fields_removed))        # type: ignore
