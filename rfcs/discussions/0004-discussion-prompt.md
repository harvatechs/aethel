# [RFC-0004 Debate] Post-Quantum State Checkpoints Without Consensus Bloat

**Category:** RFCs / Technical Debate  
**Related Spec:** [RFC-0004: Asynchronous Post-Quantum Multi-Party State Checkpoint Attestation Without Consensus Overhead](../0004-byzantine-merkle-checkpoint-attestation.md)

---

### The Problem in 60 Seconds
In PIP-1, independent archives and notaries attest to document states using post-quantum ML-DSA signatures.
- But 64 independent ML-DSA-87 signatures add up to over 200 KB per checkpoint manifest.
- Unlike classical BLS signatures on elliptic curves, lattice-based signatures cannot be aggregated natively into a compact $O(1)$ signature.
- Checkpoint history balloons to gigabytes of pure signature overhead.

### The Deliberately Flawed Strawman: CWR-1
We proposed electing an ephemeral "Aggregator Leader" every epoch who collects notary votes off-chain and signs a single summary certificate: *"48 out of 64 notaries approved this."*

### The Challenge to Systems Engineers
1. **How do we eliminate the Leader equivocation and censorship vector without dragging in a heavy Byzantine fault-tolerant consensus protocol?**
2. **Is recursive STARK/SNARK folding over ML-DSA matrix operations computationally viable for consumer desktop/mobile verifiers?**
3. **What is the minimal cryptographic footprint for an asynchronous, multi-party post-quantum checkpoint proof?**

Post your mathematical designs and critique below.
