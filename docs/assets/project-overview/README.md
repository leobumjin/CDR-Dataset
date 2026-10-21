# Project overview assets

The home page now uses `../catalog-explorer.js` and `../catalog.json` to render
class/task combinations and task summaries. Instance and context browsing live on
the separate /instances/ and /task-context/ pages. The latter uses task-context.js
to show sample judgments for a selected task and context. Catalog
JSON is generated from catalog YAML by `python -m src.catalog.web_assets` and is
also refreshed after successful manual/CUB catalog generation.

`icons.svg` provides the class icons. `statistics.js` supports the separate frozen
v1 release statistics table. `config.json` and `overview.js` are retained legacy
overview assets; the home page no longer loads overview.js.

Generation scope is read from the separate catalog_generation_scripts.json and
label_generation_scripts.json assets. The catalog snapshot contains definitions,
not random feature or task judgments. Preview with `bash shells/serve.sh`.
