# RFC-0001: Deterministic Semantic Canonicalization of UTF-8 Markdown & Embedded LaTeX

- **Status:** Open Challenge (Strawman Review)
- **Author:** Aethel Protocol Working Group
- **Category:** Canonicalization / Content Addressing
- **Affects:** CTF-1 / Yellow Paper §3, §4

---

## 1. Abstract

The Permanent Ink Protocol (`pip-1`) relies on content-addressed deterministic hashing via FIPS 202 SHA3-256 (`H(label, x) = SHA3-256(u8(len(label)) || label || x)`). Under strict binary CTF-1 (Canonical Text Format 1), any alteration of byte sequence—such as converting trailing spaces into newlines, swapping `$$` for `\[`, or reflowing Markdown paragraph margins—produces a completely disjoint Merkle tree root.

Yet in academic, legal, and archival workflows, documents are re-rendered, formatted by code formatters (e.g., Prettier, Pandoc, Black-like formatters), and viewed on different client terminals. We face a classic trilemma:
1. **Strict byte immutability:** Changing a single trailing space breaks all signed attestations and citations.
2. **Naive regex stripping:** Strips syntax critical to semantic execution (e.g. Markdown code fences, LaTeX math matrices, tables).
3. **Full AST parsing:** Non-standardized Markdown dialects (CommonMark vs GFM vs Pandoc) create irreconcilable canonicalization discrepancies and security parsing bugs.

How can `pip-1` deterministically normalize UTF-8 Markdown with embedded LaTeX equations to achieve **semantic invariance** without creating parser-differential collision vulnerabilities?

---

## 2. The Provocative Baseline (Cunningham's Law Strawman)

To stimulate discussion, the working group proposes the following **Naive Canonical Normalizer (NCN-1)**:

```python
import unicodedata2
import re

def ncn1_canonicalize(raw_text: str) -> bytes:
    # Step 1: Unicode NFC normalization (Unicode 18.0.0)
    text = unicodedata2.normalize("NFC", raw_text)
    
    # Step 2: Line ending unification
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Step 3: Strip trailing whitespace per line
    lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
    
    # Step 4: Collapse multiple blank lines into a single blank line
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Step 5: LaTeX equation whitespace collapsing
    # Replace all whitespace within $...$ or $$...$$ with single spaces
    def normalize_math(match):
        inner = match.group(1)
        inner_collapsed = " ".join(inner.split())
        return f"${inner_collapsed}$"
        
    text = re.sub(r"\$([^\$]+)\$", normalize_math, text)
    
    # Step 6: Ensure single terminal LF
    return (text.rstrip("\n") + "\n").encode("utf-8")
```

---

## 3. Why This Baseline is Catastrophically Flawed

Engineers reviewing this specification will immediately recognize fatal flaws in NCN-1:

### 3.1 Markdown Semantics Destruction
- **Hard Line Breaks**: In CommonMark and GFM, two trailing spaces at the end of a line (`"  \n"`) or a trailing backslash represent a hard `<br>`. Step 3 silently collapses line breaks, altering the rendering and legal meaning of contractual lines.
- **Code Blocks & Fences**: Inside fenced code blocks (```python ... ```), whitespace, indents, and trailing blanks are syntactically significant. NCN-1 mutates code block content.
- **Ordered List Renumbering**: Does swapping `1. Foo\n2. Bar` to `1. Foo\n1. Bar` invalidate the hash? Markdown renderers produce identical HTML output, but the text digests diverge.

### 3.2 LaTeX Mathematical Ambiguity & Collisions
- **Semantic Matrix Whitespace**: In LaTeX math environments (`\begin{matrix} a & b \\ c & d \end{matrix}`), whitespace stripping causes collisions if tokens concatenate unexpectedly or macros expand differently.
- **Escaped Currency Symbols**: A raw string like `"The item costs $50 and the tax is $10."` triggers Step 5, treating ordinary currency ranges as LaTeX math and collapsing text across sentences.
- **Macro Equivalence**: In LaTeX, `\frac{a}{b}`, `{a \over b}`, and `a/b` may represent identical mathematics, but naive string transformations cannot normalize macro expansions without a Turing-complete TeX engine.

---

## 4. The Hard Engineering Questions

We solicit proposals, proofs, and pull requests addressing four core design dilemmas:

1. **AST vs. Token Stream vs. State Machine**: Can a deterministic normalizer be implemented in strict linear time ($O(N)$) and $O(1)$ memory without relying on full DOM/AST reconstruction that invites parser divergence?
2. **Formula Canonicalization Scope**: Should mathematical formulas be compiled to an intermediate canonical semantic tree (e.g. Content MathML / OpenMath), or must LaTeX be treated as opaque literal code tokens?
3. **Dual-Digest Architecture**: Should PIP-1 documents sign a **Dual Digest**:
   $$\text{Digest}_{\text{exact}} = H(\text{"exact"}, \text{bytes})$$
   $$\text{Digest}_{\text{semantic}} = H(\text{"semantic"}, \text{AST\_Normalized})$$
   If so, what are the formal rules when an attestation checks one versus both?
4. **Collision Resistance Against Homoglyphs & Confusables**: How does normalization prevent malicious spoofing where visual formatting remains identical while hidden Unicode directionality (Bidi control characters, zero-width joiners) alters token extraction?

---

## 5. Submission & Test Suite Challenge

We challenge the community to supply adversarial test vectors that break proposed normalizers. Submit your counterexamples in the discussion thread.
