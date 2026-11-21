# [RFC-0001 Debate] Deterministic Markdown & LaTeX Normalization: Why NCN-1 is Broken and How to Fix It

**Category:** RFCs / Technical Debate  
**Related Spec:** [RFC-0001: Deterministic Semantic Canonicalization of UTF-8 Markdown & Embedded LaTeX](../0001-utf8-markdown-latex-normalization.md)

---

### The Problem in 60 Seconds
In `pip-1`, every document gets a cryptographic tree hash ($H(\text{label}, x) = \text{SHA3-256}$). But in legal, scientific, and markdown authoring:
- Adding a single trailing space or switching a line break completely breaks the hash.
- Yet naive regex stripping breaks CommonMark `<br>` semantics, ruins Python indentation inside code fences, and treats `"$50 and $10"` like a LaTeX math block.

### The Deliberately Flawed Strawman: NCN-1
We proposed a 6-step normalizer in [RFC-0001](../0001-utf8-markdown-latex-normalization.md) that uses regex substitution on lines, Unicode NFC, and math block collapsing:

```python
# From RFC-0001
def normalize_math(match):
    return f"${' '.join(match.group(1).split())}$"
text = re.sub(r"\$([^\$]+)\$", normalize_math, text)
```

### The Challenge to Engineers & Language Nerds
1. **How do we parse CommonMark + LaTeX in $O(N)$ streaming time without dragging in a massive, nondeterministic AST engine?**
2. **Can LaTeX math be canonicalized into a single invariant representation (e.g. Content MathML or an AST) without breaking macro expansions?**
3. **Show us your best counterexample input that produces an accidental collision or corrupts document meaning.**

Post your failing inputs, benchmarks, or replacement algorithms below.
