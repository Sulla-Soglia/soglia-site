# Tools

## quote-card-template.html

1080×1080 quote cards for social media (IG / 小紅書), in the journal's house style
(Cormorant Garamond, #222 ground, pink quote, burgundy kicker).

Per issue: edit the `.kicker` line (title + roman numeral), the footer issue number,
and replace `QUOTE` (supports `<em>` for white emphasis). Then render:

```sh
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --screenshot=card.png --window-size=1080,1080 --hide-scrollbars \
  --virtual-time-budget=8000 "file:///path/to/card.html"
```

First used for Issue 006 (2026-09-21).
