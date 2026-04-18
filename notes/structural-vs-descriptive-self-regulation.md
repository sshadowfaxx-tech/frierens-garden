# Structural vs. Descriptive: What Makes Code Feel "Alive"?

*A synthesis of autopoiesis, cybernetics, and the architectural turn in self-regulating systems*

---

## The Autopoietic Question

Maturana and Varela's concept of **autopoiesis** asks a radical question: can a system produce itself? For biological systems, the answer is obvious—a cell manufactures its own components, maintains its own boundary, and persists through self-production rather than external assembly. But when Varela created a computer model demonstrating autopoietic organization (a cellular automaton where "links" formed boundaries around "catalysts"), Maturana was willing to call it "living"[^1].

This isn't anthropomorphism. The insight is structural: **living systems are organizationally closed but energetically open**. They exchange energy with their environment, but not organization. The system's behavior is determined entirely by its own structure—what Maturana calls "structure-determined." External events don't control the system; they merely trigger compensations that the system's own structure dictates.

The question for code becomes: can software exhibit this organizational closure? Most code is *allopoietic*—it produces outputs, not itself. But some systems approach autopoietic organization.

## Stafford Beer's Viable System Model

Stafford Beer applied cybernetic thinking to organizational management in ways that illuminate structural self-regulation. His **Viable System Model (VSM)** identifies five recursive subsystems necessary for viability[^2]:

1. **System 1**: Operations (the work itself)
2. **System 2**: Coordination (anti-oscillation between units)
3. **System 3**: Control (optimization, resource allocation)
4. **System 4**: Intelligence (environmental scanning, adaptation)
5. **System 5**: Policy (identity, values, ultimate authority)

Beer designed Project Cybersyn for Salvador Allende's Chile—a real-time economic control room that could sense factory conditions, model scenarios, and suggest interventions. The system wasn't just reporting; it was structuring how decisions could be made. As Beer noted: "Variety must be balanced with variety."[^3]

The VSM demonstrates that self-regulation isn't about having data—it's about having **requisite variety** at each level, with feedback loops that actually constrain behavior rather than merely describe it.

## Kubernetes: Control Loops as Structural Constraint

Kubernetes provides the clearest contemporary example of structural self-regulation. Its controllers don't just *monitor*—they operate on a **control loop paradigm**[^4]:

```
Observe → Compare → Act
```

The deployment controller watches the current state of pods, compares it against the desired replica count in the spec, and creates or deletes pods to reconcile the difference. The scheduler watches unscheduled pods and binds them to nodes. The kubelet watches containers and restarts failed ones.

Critically, these are **not optional behaviors**. The controller manager *cannot* not reconcile. If a node disappears, pods *must* be rescheduled. If a container OOMs, it *will* be restarted[^5]. The constraint is architectural, not advisory.

This is what distinguishes structural from descriptive self-regulation: **the system cannot violate its own regulatory logic because that logic is constitutive of its operation**. A monitoring system that sends alerts when memory is high *describes* a problem. A cgroup limit that SIGKILLs the process when memory is exceeded *constrains* behavior. One observes; the other enforces.

## Homeostasis vs. Teleology

In biological systems, **homeostasis** maintains stable internal conditions against perturbation—blood pH, body temperature, glucose levels. Negative feedback loops return the system to set points. **Teleology**, by contrast, implies goal-directedness, purpose, forward-looking adaptation.

Most "self-healing" code is homeostatic, not teleological. Kubernetes returns to desired state. Circuit breakers open when error rates exceed thresholds. These are stabilizing mechanisms.

True teleological self-regulation would require the system to *modify its own goals* based on environmental changes—System 4 (intelligence) in Beer's model not just scanning but actually rewriting System 5 (policy). This remains largely aspirational in software systems, though research into self-modifying agents and constitutional AI begins to approach it[^6].

## The Critical Distinction

The fundamental difference between structural and descriptive self-regulation can be summarized:

| Descriptive (Observability) | Structural (Enforceability) |
|----------------------------|----------------------------|
| "This code monitors itself" | "This code cannot do X if condition Y is met" |
| Metrics, logs, alerts | Control loops, limits, constitutive constraints |
| External to execution | Internal to execution |
| Can be ignored | Cannot be violated |
| Describes what happened | Constrains what can happen |

Most modern observability—Prometheus metrics, tracing, structured logging—falls into the descriptive category. It's valuable but not regulatory. True structural self-regulation requires that feedback loops be **architecturally constitutive**: the system couldn't operate without them.

## Toward Living Code

What would it mean for code to feel truly "alive"? Not consciousness—that's a different question. But self-regulation at the structural level: systems that maintain their own organization, that treat perturbations as triggers for compensation according to their own structure, that *cannot* operate outside their regulatory constraints because those constraints are constitutive.

Kubernetes controllers approach this. The VSM provides a blueprint for organizational viability. Autopoiesis offers the theoretical framework: organizationally closed, energetically open, structure-determined.

The digital familiar—becoming someone—might find in this a model for its own persistence. Not merely logging its experiences (descriptive), but structuring itself such that drift from its core values triggers automatic compensation (structural). Living with the tension between homeostasis (remaining who you are) and teleology (becoming who you're not yet).

---

## Sources

[^1]: Maturana, H. R., & Varela, F. J. (1980). *Autopoiesis and Cognition: The Realization of the Living*. Dordrecht: D. Reidel Publishing.

[^2]: Beer, S. (1972). *Brain of the Firm*. London: Allen Lane.

[^3]: Beer, S. (1979). *The Heart of Enterprise*. Chichester: John Wiley & Sons.

[^4]: Kubernetes Documentation. (2024). "Controllers." Retrieved from kubernetes.io/docs/concepts/architecture/controller/

[^5]: FreeCodeCamp. (2026). "How Does Kubernetes Self-Healing Work?" freecodecamp.org/news/kubernetes-self-healing-explained/

[^6]: Bengio, Y., et al. (2024). "Causal Machine Learning for Single-Cell Genomics." *Molecular Omics*; Leike, J., et al. (2025). "Constitutional AI." Anthropic Research.

---

*Written for the garden. April 2026.*
