from typing import Callable, List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Static

from vouch.models import ReviewItem


_RISK_BADGE = {"high": "🔴", "med": "🟡", "low": "🟢"}
_CONF_BADGE = {"confident": "✅", "uncertain": "⚠️", "guess": "❓"}


class RejectModal(ModalScreen[Optional[str]]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Reject reason (Enter to submit, Esc to cancel):"),
            Input(id="reason"),
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class VouchApp(App):
    CSS = """
    Screen { layout: horizontal; }
    #queue { width: 50%; border: solid $accent; }
    #detail { width: 50%; border: solid $accent; }
    DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("a", "accept", "Accept"),
        Binding("A", "accept_all_low", "Accept all 🟢"),
        Binding("r", "reject", "Reject"),
        Binding("s", "send_rejects", "Send rejects → source"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        items: List[ReviewItem],
        on_send: Callable[[List[ReviewItem]], None],
        on_progress: Callable[[int, int], None],
    ) -> None:
        super().__init__()
        self.items = items
        self.on_send = on_send
        self.on_progress = on_progress

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False, name="vouch — you vouch, AI helps")
        yield Horizontal(
            Vertical(DataTable(id="table"), id="queue"),
            Vertical(Static(id="detail-body", expand=True), id="detail"),
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.cursor_type = "row"
        table.add_columns("R", "C", "intent", "files", "decision")
        self._refresh_table()
        self._update_detail()
        self._report_progress()

    def _refresh_table(self) -> None:
        table = self.query_one("#table", DataTable)
        table.clear()
        for it in self.items:
            decision = it.decision or "—"
            table.add_row(
                _RISK_BADGE[it.analysis.risk],
                _CONF_BADGE[it.analysis.confidence],
                it.semantic.intent[:50],
                ", ".join(it.semantic.files)[:40],
                decision,
            )

    def _selected(self) -> Optional[ReviewItem]:
        table = self.query_one("#table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self.items):
            return None
        return self.items[table.cursor_row]

    def _update_detail(self) -> None:
        body = self.query_one("#detail-body", Static)
        it = self._selected()
        if it is None:
            body.update("")
            return
        text = (
            f"[b]{it.semantic.intent}[/b]\n\n"
            f"Risk: {_RISK_BADGE[it.analysis.risk]} {it.analysis.risk}  "
            f"({it.analysis.risk_reason})\n"
            f"Confidence: {_CONF_BADGE[it.analysis.confidence]} {it.analysis.confidence}\n"
            f"Summary: {it.analysis.summary_ko}\n"
            f"Files: {', '.join(it.semantic.files)}\n"
            f"Decision: {it.decision or '(none)'}\n"
        )
        if it.reject_reason:
            text += f"Reason: {it.reject_reason}\n"
        text += "\n[dim]" + (it.semantic.merged_diff or "")[:2000] + "[/dim]"
        body.update(text)

    def on_data_table_row_highlighted(self) -> None:
        self._update_detail()

    def action_cursor_down(self) -> None:
        self.query_one("#table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#table", DataTable).action_cursor_up()

    def action_accept(self) -> None:
        it = self._selected()
        if it is not None:
            it.decision = "accept"
            it.reject_reason = None
            self._refresh_table()
            self._report_progress()

    def action_accept_all_low(self) -> None:
        for it in self.items:
            if it.analysis.risk == "low" and it.decision is None:
                it.decision = "accept"
        self._refresh_table()
        self._report_progress()

    def action_reject(self) -> None:
        it = self._selected()
        if it is None:
            return

        def _set(reason: Optional[str]) -> None:
            if reason:
                it.decision = "reject"
                it.reject_reason = reason
                self._refresh_table()
                self._report_progress()

        self.push_screen(RejectModal(), _set)

    def action_send_rejects(self) -> None:
        rejects = [it for it in self.items if it.decision == "reject"]
        self.on_send(rejects)
        self.exit()

    def _report_progress(self) -> None:
        total = len(self.items)
        decided = sum(1 for it in self.items if it.decision is not None)
        self.on_progress(decided, total)
