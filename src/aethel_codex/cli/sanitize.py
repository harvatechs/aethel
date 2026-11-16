"""Terminal sanitization for untrusted text (cli-spec.md §1)."""

BIDI_CONTROLS = {
    0x061C,  # ARABIC LETTER MARK
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x202A,  # LEFT-TO-RIGHT EMBEDDING
    0x202B,  # RIGHT-TO-LEFT EMBEDDING
    0x202C,  # POP DIRECTIONAL FORMATTING
    0x202D,  # LEFT-TO-RIGHT OVERRIDE
    0x202E,  # RIGHT-TO-LEFT OVERRIDE
    0x2066,  # LEFT-TO-RIGHT ISOLATE
    0x2067,  # RIGHT-TO-LEFT ISOLATE
    0x2068,  # FIRST STRONG ISOLATE
    0x2069,  # POP DIRECTIONAL ISOLATE
}


def is_unsafe_terminal_char(ch: str) -> bool:
    """Return True if character is a C0/C1 control, bidi control, or tag character."""
    code = ord(ch)
    if code < 0x20 and code != 0x0A:  # C0 control (preserve linefeed)
        return True
    if 0x7F <= code <= 0x9F:  # DEL and C1 controls
        return True
    if code in BIDI_CONTROLS:  # Bidirectional formatting
        return True
    return 0xE0001 <= code <= 0xE007F  # Language tag characters


def sanitize_terminal(text: str) -> str:
    r"""Sanitize untrusted text before printing to a terminal.

    Replaces C0/C1 controls, bidi controls, and tag characters with \u{xxxx}.
    Normative reference: cli-spec.md §1.
    """
    out: list[str] = []
    for ch in text:
        if is_unsafe_terminal_char(ch):
            code = ord(ch)
            if code <= 0xFFFF:
                out.append(f"\\u{{{code:04x}}}")
            else:
                out.append(f"\\u{{{code:06x}}}")
        else:
            out.append(ch)
    return "".join(out)
