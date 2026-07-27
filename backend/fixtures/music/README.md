# Betty Stock Beds v1

Eight packaging BGM presets used by `compose_final_video`:

`soft` · `upbeat` · `cinematic` · `drama` · `corporate` · `energetic` · `chill` · `hype`

On API boot, beds are copied to `$STORAGE_PATH/bgm/` and resolved as public URLs
(`PUBLIC_BASE_URL/api/v1/media/bgm/{preset}.wav`) when `BGM_URL_*` is unset.

See `LICENSE.md` for usage terms. Override with licensed tracks via env.
