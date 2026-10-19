# Latest-version summary

Edit `config.json` to update the hero's latest version and categories. Add a
`versions.v2` entry with its category list, then change `latestVersion` to `v2`.
`overview.js` builds the version link and cards from that entry. Category IDs,
display names, queries, and icon symbol IDs are kept in the configuration.

Edit `icons.svg` to change or add SVG symbols. Styles are in `docs/styles.css`
under “Configurable latest-version summary”. A static v1 fallback is in the HTML
for unavailable JavaScript/network. Update that fallback when releasing a new
version if you want it to match as well.

This component updates the hero only; the detailed v1 examples and statistics
elsewhere on the page remain explicitly about v1. No dataset or evaluation files
are changed. Preview using `bash shells/serve.sh`.
