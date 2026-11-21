# [RFC-0003 Debate] Stress-Testing the Permanent Storage Endowment: What If Kryder's Law Dies?

**Category:** RFCs / Technical Debate  
**Related Spec:** [RFC-0003: Solvency Bounds & Catastrophic Deficit Stress-Testing for the Perma-Endowment Storage Pool Under Kryder Rate Stagnation](../0003-perma-endowment-storage-economics.md)

---

### The Problem in 60 Seconds
Every "perpetual storage" protocol claims you can pay once upfront and store data forever because Kryder's Law will drive storage costs down exponentially ($C(t) = C_0 (1 - \delta)^t$).
- What if silicon scaling hits quantum tunneling limits and $\delta \to 0$?
- What if energy spikes or inflation push real yields negative ($r < 0$)?
- The infinite geometric series diverges. The pool goes bankrupt in year 14.

### The Deliberately Flawed Strawman: LCEM-1
We modeled an endowment that charges a $2\times$ safety buffer upfront (\$0.0572/GB) and subsidizes shortfalls by taxing active transaction fees:

$$F_{\text{charged}} = 2 \cdot C_0 \cdot \frac{1 + r}{r + \delta}$$

### The Challenge to Economists, Actuaries & Game Theorists
1. **Under what exact macroeconomic parameter space ($\delta, r, \sigma$) does an upfront endowment pool mathematically enter a terminal bankruptcy death spiral?**
2. **Can a network dynamically scale down redundancy factors (e.g. from 50 replicas to Reed-Solomon erasure coding) without breaking permanent retrieval commitments?**
3. **If bankruptcy occurs, what is the game-theoretically fair algorithm to prune abandoned data without triggering a run on the network?**

Submit your actuarial proofs, simulations, and counter-mechanisms below.
