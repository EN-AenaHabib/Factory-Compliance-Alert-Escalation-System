# Swarm Intelligence Extensions (Future Work)

## Overview

The current system **does not use Swarm Intelligence during normal execution**. All detector thresholds and severity rules are fixed values stored in `config.yaml`.

Swarm Intelligence is proposed only as a **future offline optimization step**. It would analyze previously collected and human-labeled data to recommend better configuration values. A human would review these recommendations before applying them.

This approach follows **Green AI** because optimization runs only when needed and adds **zero extra computation** during real-time factory monitoring.

---

# 1. Particle Swarm Optimization (PSO)

### Purpose

PSO can be used to automatically find better parameter values instead of manually choosing them.

### Possible uses

- Optimize severity weights
- Optimize confidence thresholds
- Optimize motion, color, and edge detection thresholds
- Improve Precision, Recall, and F1 score

### Why PSO?

PSO is designed for **continuous numerical optimization**, making it suitable for tuning values such as:

- confidence threshold
- motion threshold
- uncertainty margin
- severity weights

The optimized values can then be saved back into `config.yaml`.

---

# 2. Ant Colony Optimization (ACO)

### Purpose

ACO can be used for **decision and resource allocation problems**.

### Possible uses

- Selecting the best detector when multiple detectors are available
- Allocating more processing time to high-risk camera zones
- Optimizing resource usage in multi-camera deployments

### Why ACO?

ACO works well for **discrete decision-making problems**, where the goal is to choose the best option from several alternatives.

---

# Why Swarm Intelligence is Offline

Swarm Intelligence is intentionally **not part of the runtime pipeline** because:

- Safety systems should use stable, human-approved parameters.
- Continuous self-modification could reduce reliability.
- Offline optimization keeps runtime lightweight and energy-efficient (Green AI).
- Optimization requires human-labeled training data.

---

# Summary

Current system:
- Fixed thresholds
- Manual configuration
- Lightweight runtime
- Green AI

Future version:
- PSO automatically tunes thresholds and weights.
- ACO improves detector selection and resource allocation.
- Optimized parameters are reviewed by a human before deployment.
