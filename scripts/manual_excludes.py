"""Vendor libraries / auto-generated / data-dump files the language-level
cloc filter can't catch, discovered by inspecting each repo's top-churn and
top-LOC files (jQuery/Bootstrap/Handlebars/Prism.js vendored in, an
ANTLR-generated parser, an auto-generated GraphQL schema dump, auto-generated
docs/timings/*.js, and various word-list/fixture data files).

Shared by gather_data.py (LOC) and lines_changed_by_day.py (per-day churn)
so both use the same exclusions. Keyed by "owner/repo", glob patterns
matched against the file's path relative to the repo root.
"""

MANUAL_EXCLUDES = {
    "parimagine/parimagine": [
        "src/main/webapp/jquery.js",
        "src/test/resources/photos*.sql",
        "parimagine-core/curl/photoURLs.txt",
        "parimagine-static/src/main/webapp/modules/avant-apres/jquery.beforeafter-*.js",
    ],
    "parimagine/parimagine.github.io": [
        "assets/jquery/*.js",
        "assets/jquery.iframe-auto-height.plugin*.js",
        "assets/handlebars/*.js",
        "assets/bootstrap/**",
        "assets/beforeafter/js/jquery.beforeafter-*.js",
    ],
    "earthlydelights/earthlydelights.github.io": [
        "assets/js/imagesloaded.pkgd*.js",
    ],
    "earthlydelights/image-server": [
        # package renamed mid-history (net.aequologica.neo.geppaequo -> garden.delights.earthly.imageserver);
        # both paths needed to catch the file across its full commit history.
        "src/test/resources/net/aequologica/neo/geppaequo/jaxrs/randomizer/dugenou.txt",
        "src/test/resources/net/aequologica/neo/geppaequo/jaxrs/randomizer/tomcat-test-uniform.txt",
        "src/test/resources/garden/delights/earthly/imageserver/randomizer/dugenou.txt",
        "src/test/resources/garden/delights/earthly/imageserver/randomizer/tomcat-test-uniform.txt",
    ],
    "usa-covid-aequologica-net/usa.covid.aequologica.net": [
        "wavetable.js",
        "todos/wavetable.js",
    ],
    "covid-aequologica-net/covid-aequologica-net.github.io": [
        "wavetable.js",
        "todos/wavetable.js",
    ],
    "sangiovannilipioni/sangiovannilipioni.github.io": [
        "schema.docs.graphql",
    ],
    "sangiovannilipioni/sangiovannilipioni.api": [
        "**/.antlr/*.java",
        "files/Sintesi_*.txt",
        "antlrparser/src/main/java/net/aequologica/sangiovannilipioni/antlr/*.java",  # ANTLR-generated, checked into src/main
    ],
    "cthiebaud/ciaccona": [
        "docs/timings/*.js",
        "docs/lib/prism-*.js",
    ],
    "musicollator/ciaccona": [
        "docs/timings/*.js",
        "docs/lib/prism-*.js",
    ],
    "cthiebaud/bookshelves": [
        "isbn-ja.txt",
        "isbn-ja2.txt",
        "isbn.txt",
        "qwe.txt",
    ],
    "cthiebaud/bookcovers": [
        "isbn-ja.txt",
    ],
    "cthiebaud/truth": [
        "src/css/bootstrap.css",
        "material/greek-name-generation-playground/_GreekMythology.txt",
        "material/greek-name-generation-playground/_PersonalAdjectives.txt",
    ],
    "cthiebaud/truth-reservoir": [
        "src/main/resources/com/cthiebaud/unique/name/greeks.txt",
        "src/main/resources/com/cthiebaud/unique/name/adjectives.txt",
    ],
    "cthiebaud/vinyl": [
        "fontello/demo.html",  # Fontello icon-font kit's auto-generated demo page (embeds vendored Bootstrap 2.2.1 CSS inline)
    ],
}
