<div align="center">

# CDR-Dataset

### Contextual Default Retraction Dataset

A dataset for evaluating contextual default reasoning and belief retraction in language models.

[![GitHub](https://img.shields.io/badge/GitHub-leobumjin%2FCDR--Dataset-181717?logo=github)](https://github.com/leobumjin/CDR-Dataset)
![Task](https://img.shields.io/badge/Task-Default%20Reasoning-2563EB)
![Focus](https://img.shields.io/badge/Focus-Belief%20Retraction-7C3AED)

---

**Reason with defaults. Reconsider with context.**

</div>

## Overview

Language models often need to draw reasonable conclusions from incomplete information. Those conclusions should remain open to revision when new context introduces an exception.

**CDR-Dataset** (Contextual Default Retraction Dataset) is designed to evaluate this ability, with a focus on two connected aspects of reasoning:

| Capability | Evaluation focus |
| :--- | :--- |
| **Contextual default reasoning** | Drawing defeasible conclusions from the available context. |
| **Belief retraction** | Withdrawing a previously supported conclusion when new context defeats its justification. |

## Motivation

A plausible default is useful only when a model can recognize its limits. Evaluating both the initial inference and its subsequent retraction helps assess whether a model can adapt its conclusions to changing evidence.

> **Illustrative example — not a dataset record**
>
> **Default:** Birds typically fly.
>
> **Initial context:** Pip is a bird.
>
> **Default conclusion:** Pip can fly.
>
> **New context:** Pip is a penguin, and penguins cannot fly.
>
> **Retraction:** The default conclusion that Pip can fly no longer holds.

## Repository

The dataset repository is hosted at [**leobumjin/CDR-Dataset**](https://github.com/leobumjin/CDR-Dataset).

```bash
git clone https://github.com/leobumjin/CDR-Dataset.git
cd CDR-Dataset
```

## Release information

Dataset files, format documentation, evaluation instructions, and citation details will be documented here as they become available.
