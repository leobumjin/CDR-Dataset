# Feature groups

Each flat <class>.yaml file names a feature group, not a collection of real or named objects.
The active groups are bird, human, legal_case, mammal, plant, cars, foods, garments,
smartphones and kitchenware. Each includes seven stable features in its features mapping.

Samples are constructed or imported separately as feature-value maps. They have
no catalog list entry, display name or real/synthetic grounding flag. All features
can be constructed without name-based inference. Task labels may then be generated
from those values and context, including by AI.

Feature labeling text preserves dataset-specific operational criteria; it does not
establish a universal scale. Store each source's actual value encoding separately.
The five additional feature groups retain supplied preview rubrics; this does not
import named preview entities into the active catalog. The retired named-entity import pipeline has been removed. Supplied feature
rubrics originated in the imjiyu/CDR-Dataset-v2-preview metadata.
