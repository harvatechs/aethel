# Aethel Request for Comments (RFCs)

> *"The best way to get the right answer on the Internet is not to ask a question; it's to post the wrong answer."*  
> — **Cunningham's Law**

Welcome to the open engineering RFC process for the Permanent Ink Protocol (`pip-1`) and `aethel`.

Most protocol designs stall in committee because engineers rarely assemble to applaud an abstract blueprint. However, engineers cannot resist tearing apart a flawed concrete specification, proving an edge-case counterexample, or demonstrating that an algorithmic assumption fails under stress.

Every RFC in this directory represents an **unsolved, open architectural challenge** in permanent digital preservation and post-quantum cryptographic attribution. Each document deliberately includes:
1. **A Concrete Strawman Proposal**: A simple, seemingly complete baseline implementation that contains subtle mathematical, cryptographic, or operational vulnerabilities.
2. **The "Trap" / Known Failure Mode**: Explicitly highlighted failure conditions that make the naive approach fail in production.
3. **Open Challenges & Provocations**: Precise questions and test matrices awaiting formal solutions, bounds, and proofs.

---

## Active RFC Index

| RFC | Title | Domain | Status | Discussion Thread |
|---|---|---|---|---|
| [RFC-0001](0001-utf8-markdown-latex-normalization.md) | Deterministic Semantic Normalization of UTF-8 Markdown & LaTeX | Canonicalization / CTF-1 | **OPEN DEBATE** | [#101 - Markdown/LaTeX AST Invariance](discussions/0001-discussion-prompt.md) |
| [RFC-0002](0002-decentralized-qrng-entropy-sourcing.md) | Trustless QRNG Entropy Ingestion Without Centralized Oracles | Post-Quantum Cryptography | **OPEN DEBATE** | [#102 - Decentralized QRNG & Verifiable Delay](discussions/0002-discussion-prompt.md) |
| [RFC-0003](0003-perma-endowment-storage-economics.md) | Solvency Bounds for Perpetual Storage Endowments Under Kryder Stagnation | Mechanism Design & Actuarial Math | **OPEN DEBATE** | [#103 - Perma-Endowment Failure Proofs](discussions/0003-discussion-prompt.md) |
| [RFC-0004](0004-byzantine-merkle-checkpoint-attestation.md) | Asynchronous Post-Quantum Multi-Party State Checkpoint Attestation | Consensus-Free Verification | **OPEN DEBATE** | [#104 - Stateless ML-DSA Aggregation Quorums](discussions/0004-discussion-prompt.md) |

---

## How to Participate (GitHub Discussions)

1. Navigate to the matching thread under [GitHub Discussions → RFCs](../../discussions/categories/rfcs).
2. **Prove us wrong**: If you can demonstrate an AST collision in RFC-0001, an entropy manipulation attack in RFC-0002, or a bankruptcy run in RFC-0003, submit code, test vectors, or formal proofs.
3. The peer who identifies a fatal flaw or produces the canonical fix is credited directly in the Yellow Paper appendix and implementation specification.
