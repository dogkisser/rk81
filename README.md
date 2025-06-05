# /rk81/

(aka /[rk9](https://github.com/dogkisser/rk9)<sup>^2</sup>/)

## Supported Sites

- `gelbooru.com`
- `e621.net`
- `rule34.xxx`

## Blacklist syntax

If a post's tags _matches_ a blacklist query, that post will **not** be sent to you. Queries are
matched like so:

| Input                   | Action                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `tag`                   | Matches posts tagged with `tag`                                                    |
| `tag1 tag2`             | Matches posts tagged with `tag1` and `tag2` (but not just `tag1`)                  |
| `tag1 -tag2`            | Matches posts tagged with `tag1` but not `tag2`                                    |
| `tag1 tag2 -tag3 -tag4` | Matches posts tagged with `tag1` and `tag2`, but not tagged with `tag3` nor `tag4` |