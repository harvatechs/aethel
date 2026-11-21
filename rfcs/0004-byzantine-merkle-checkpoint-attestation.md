# RFC-0004: Asynchronous Post-Quantum Multi-Party State Checkpoint Attestation Without Consensus Overhead

- **Status:** Open Challenge (Strawman Review)
- **Author:** Aethel Protocol Working Group
- **Category:** Consensus-Free Cryptography / Attestation Networks
- **Affects:** Offline Verification, Yellow Paper §5, §14

---

## 1. Abstract

The Permanent Ink Protocol (`pip-1`) guarantees offline verification of documents, code packages, and legal archives using post-quantum signatures (NIST FIPS 204 ML-DSA and FIPS 205 SLH-DSA) and binary Merkle chunk proofs. In distributed archival topologies, multiple independent storage nodes, notary services, and public archives continuously verify and store Merkle roots.

To establish global temporal ordering and non-repudiation without relying on a single timestamp authority or operating an expensive proof-of-work/proof-of-stake blockchain consensus engine, the network needs an **asynchronous checkpoint attestation mechanism**.

However, combining post-quantum signatures across hundreds of independent validator nodes encounters severe cryptographic roadblocks:
- **Massive Signature Bloat**: ML-DSA-87 public keys are 2,592 bytes and signatures are 4,595 bytes. A quorum of 100 independent signatures would require ~460 KB per checkpoint manifest.
- **Lattice Aggregation Hardness**: Unlike classical BLS signatures (which allow $O(1)$ constant-size signature aggregation via elliptic curve pairings), lattice-based signatures like ML-DSA do not natively aggregate linearly without introducing complex interactive protocols or lattice lattice-trapdoor assumptions.
- **Asynchronous Network Delays**: Without a synchronized global clock or consensus leader, nodes observe checkpoints at slightly different intervals.

How can a decentralized network of heterogeneous notaries attest to periodic Merkle checkpoint states with sub-second verification times and compact (<10 KB) post-quantum multi-signatures?

---

## 2. The Provocative Baseline (Cunningham's Law Strawman)

Consider the naive **Concatenated Witness Ring (CWR-1)** baseline:

```
Checkpoint State S_t
       |
       +---> Notary 1 (ML-DSA-65) ---> Sig_1 (3,309 B)
       +---> Notary 2 (ML-DSA-65) ---> Sig_2 (3,309 B)
       +---> Notary k (ML-DSA-65) ---> Sig_k (3,309 B)
       |
Package: [ Manifest S_t ] || [ Bitmap of signers ] || [ Sig_1 || Sig_2 || ... || Sig_k ]
Size for k=64: ~212 KB per 10-minute epoch.
```

To reduce payload overhead, CWR-1 suggests:
1. Selecting a single pseudo-random "Aggregator Leader" every epoch based on $H(\text{epoch} \parallel S_{t-1})$.
2. The Leader collects individual notary approvals via an HTTP POST endpoint.
3. The Leader signs a single "Consolidated Quorum Certificate" stating: *"I have verified that 48 out of 64 notaries approved checkpoint $S_t$."*
4. Clients verify only the single Leader's signature.

---

## 3. Why This Baseline is Catastrophically Flawed

Engineers will immediately point out the glaring vulnerabilities:

### 3.1 Leader Censorship & Equivocation
The Aggregator Leader possesses unilateral authority to equivocate: it can produce two conflicting Quorum Certificates for two different versions of $S_t$, sign both, and partition the network. Clients verifying only the Leader have zero cryptographic evidence that the constituent notaries actually signed or agreed to that state.

### 3.2 Ephemeral Bandwidth & Storage Bloat
If we fall back to the unaggregated concatenated list ($212\text{ KB}$ every 10 minutes), archiving a single year of checkpoints requires over **11 GB** of raw signature bytes alone—surpassing the size of the archived data itself for moderate document repos.

### 3.3 The Verification Compute Avalanche
Verifying 64 distinct ML-DSA-65 polynomial matrix multiplications on mobile devices or embedded hardware consumes hundreds of milliseconds of compute time, defeating the lightweight offline verification mandate of PIP-1.

---

## 4. The Hard Engineering Questions

We seek concrete contributions on:

1. **Practical Post-Quantum Threshold Signatures**: Can a non-interactive, robust $(t, n)$-threshold signature scheme based on standard lattices (e.g., Module-LWE / SIS) produce a single valid ML-DSA-compatible signature without an interactive resharing phase?
2. **Recursive SNARK/STARK Compression of Lattice Signatures**: Can an untrusted prover generate a STARK proof that attests: *"I know 50 distinct valid ML-DSA signatures over Merkle root $R$ from the authorized notary set,"* with a proof size $< 30\text{ KB}$ and verification time $< 5\text{ ms}$?
3. **Byzantine Liveness Under Network Jitter**: How does an asynchronous notary network reach agreement on checkpoint inclusion when cross-border latency and BGP route leaks cause validators to receive document manifests in different orders?

---

## 5. Submit Your Attack or Architecture

Join the debate and help eliminate this bottleneck in the discussion thread.
