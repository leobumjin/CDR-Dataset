# Project overview assets

The home page renders feature-group and task links from catalog.json using
catalog-explorer.js. The /catalog/ URL displays the Catalog with an explicit catalog version selector. Its Features and Task-Context tabs share the selected class. The separate
Task–Context page has been removed. The browser reads release_samples.json; generated source runs are never fallback
website data. Catalog mode contains definitions only, with no object list.

Run `python -m src.catalog.web_assets` after editing definitions or assembling
releases. Frozen release definitions interpret frozen feature values. icons.svg
and the separate historical v1 statistics/example assets remain available.
Preview locally with `bash tools/serve.sh`.
