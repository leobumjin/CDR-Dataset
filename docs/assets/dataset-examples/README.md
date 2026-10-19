# Additional interactive domain examples

Mammals, Plants, and Humans use the same card and conversation layout as Bird
and Legal Cases. Edit `examples.json` for their four context labels and prompts;
`examples.js` updates the selected card without resetting the other domains.
Initial markup and feature pills are in `docs/index.html`.

Source entities: mammal 038, plant 014, human 018. Reference codes come from the
preserved GPT-5.4 snapshot. Prompts are conversational summaries of c_1–c_4.
Feature pills display actual stored judgments; an ambiguous 0.5 is explicitly
marked ambiguous rather than converted to a boolean. The examples retain the
same illustrative-response disclaimer as Bird and Legal Cases.

The metadata records each source entity and original context ID for verification.
No dataset contents or evaluation logic are modified by these page assets.
