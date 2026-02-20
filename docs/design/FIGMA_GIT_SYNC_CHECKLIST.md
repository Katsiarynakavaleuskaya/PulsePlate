# Figma Git Sync Checklist

1. Open canonical Figma Design node (`figma.com/design`, not Make link).
2. Export locked assets (`SVG`, `PNG 1024`, `PNG 60`) from the winner node.
3. Replace canonical files only in `assets/brand/icon/core/v1.0/`.
4. Run `make icon-core-validate && make icon-silhouette-lock && make icon-silhouette-check`.
5. Update `meta.json`, lock/results/evidence docs, then commit and open PR.
