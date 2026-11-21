# [RFC-0002 Debate] Sourcing QRNG Entropy Without Centralized Oracles or Miner Lookahead

**Category:** RFCs / Technical Debate  
**Related Spec:** [RFC-0002: Decentralized, Publicly Verifiable QRNG Entropy Ingestion Without Centralized Oracles](../0002-decentralized-qrng-entropy-sourcing.md)

---

### The Problem in 60 Seconds
Post-quantum signing and decentralized state attestation need fresh, unbiasable physical entropy. But:
- Public QRNG beacons (NIST, Cloudflare LavaRand, ANU) are centralized single points of failure.
- On-chain blockhashes suffer from miner lookahead bias.
- Commit-reveal protocols suffer from the last-revealer withholding attack.

### The Deliberately Flawed Strawman: FQTB-1
We proposed a 7-node academic consortium that signs raw QRNG outputs and XORs them:
$$E^{(t)} = \text{SHA3-256}\left(\bigoplus_{j=1}^{4} e_{i_j}^{(t)}\right)$$

### The Challenge to Cryptographers
1. **How does a light client prove that a hardware node provided genuine quantum measurement data rather than `ChaCha20(seed)` without expensive Bell-test photon coincidence counters?**
2. **Can an asynchronous Verifiable Delay Function (VDF) completely eliminate the last-revealer advantage without requiring synchronous network rounds?**
3. **What is the most communication-efficient lattice-based post-quantum randomness beacon scheme that avoids the quadratic message explosion of standard $(t, n)$ multi-signatures?**

Rip our strawman apart and propose a real architecture below.
