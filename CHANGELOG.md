# Changelog

## [0.5.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.4.0...v0.5.0) (2026-09-01)


### Features

* **audio_capture:** add response for device information ([2fb7b84](https://github.com/ASM-joynnovate/buddybird-api/commit/2fb7b84b9aa8ae0ac8fa52601c9195a029af31e6))
* **audio_capture:** add response for device information ([fd3cfee](https://github.com/ASM-joynnovate/buddybird-api/commit/fd3cfeef7b7aa79929801dba0b265b2b0adbedc8))

## [0.4.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.3.1...v0.4.0) (2026-09-01)


### Features

* **audio-capture:** add AudioCapture memo API ([5bc7523](https://github.com/ASM-joynnovate/buddybird-api/commit/5bc7523ec72aa0a8fe7b0c8b73d9f10cd7def666))
* **audio-capture:** add AudioCapture memo API ([3a22ade](https://github.com/ASM-joynnovate/buddybird-api/commit/3a22adecd2ba5043f7ce2b66f6518b27de7fb4ca))

## [0.3.1](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.3.0...v0.3.1) (2026-09-01)


### Bug Fixes

* **database:** fix database migration ([8527589](https://github.com/ASM-joynnovate/buddybird-api/commit/852758954c5e961489f9db46bfd98ae983b2642d))
* **database:** fix database migration ([8556456](https://github.com/ASM-joynnovate/buddybird-api/commit/8556456d52fb740237a540383b4ad820075e9206))

## [0.3.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.2.0...v0.3.0) (2026-09-01)


### Features

* **app:** standardize API request and error contracts ([4def59d](https://github.com/ASM-joynnovate/buddybird-api/commit/4def59d092202b01b88d3588d3752b28d1182505))
* **audio_captures:** bulk migrate review ([82f9070](https://github.com/ASM-joynnovate/buddybird-api/commit/82f9070043e3d615cfa7a48c9fb520b533171f1a))
* **audio-capture:** add memo column to AudioCapture ([682f080](https://github.com/ASM-joynnovate/buddybird-api/commit/682f0801eed2174dd51e19726bff1fd88effe289))
* **audio-capture:** add review migration endpoint ([7139201](https://github.com/ASM-joynnovate/buddybird-api/commit/7139201e0a8ea46333b2c87d75855b8a73dac44d))
* **database:** alter firebase_anon_uid limit to 30 in word_entries table ([504e317](https://github.com/ASM-joynnovate/buddybird-api/commit/504e317bb67fcd228e61420f7f56d15580b75b90))
* **db:** standardize persistence and apply schema constraints ([6a0c31c](https://github.com/ASM-joynnovate/buddybird-api/commit/6a0c31c272013a2e05bf499f6b3eb26356f5ecab))
* review migration endpoint ([7541457](https://github.com/ASM-joynnovate/buddybird-api/commit/7541457274152e3dc3986a6f670438d033a34c61))


### Bug Fixes

* limit firebase_anon_uid to 128 char ([5be6768](https://github.com/ASM-joynnovate/buddybird-api/commit/5be6768eb7aa7d2ffe3fbfbadafde95c8a87c8b0))
* limit firebase_anon_uid to 128 char ([594909d](https://github.com/ASM-joynnovate/buddybird-api/commit/594909d771adae69d7d66b514fa3344ecfb1624c))


### Documentation

* **agent:** document code conventions ([456ed69](https://github.com/ASM-joynnovate/buddybird-api/commit/456ed6964c3dab47fb3079eca955262986c12141))

## [0.2.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.1.2...v0.2.0) (2026-08-29)


### Features

* **audio-capture:** add application-level duplicate validation for labels ([f171a9b](https://github.com/ASM-joynnovate/buddybird-api/commit/f171a9b289b3c0805834910c723213923c34c066))
* **audio-capture:** add capture label assignment and label target filtering ([b705164](https://github.com/ASM-joynnovate/buddybird-api/commit/b705164c5c60df77368bc9dbfebcac10aa2c45c9))
* **audio-capture:** add label reference cleanup on label deletion ([e31a5dc](https://github.com/ASM-joynnovate/buddybird-api/commit/e31a5dc221d8ef4a97f7e595d558449166d49c92))
* **audio-capture:** add LabelCategory target and capture label assignment ([f4e710e](https://github.com/ASM-joynnovate/buddybird-api/commit/f4e710ecb6458a9a80f268165de83528444ca9b1))
* **db:** remove unique constraint in label_categories table and label_options table ([dd2f545](https://github.com/ASM-joynnovate/buddybird-api/commit/dd2f5456c83bc8b4a993f029766cee10faae7f5b))


### Bug Fixes

* remove unused code and fix bug ([5990db0](https://github.com/ASM-joynnovate/buddybird-api/commit/5990db0faa6ee343ddf50fa5f1ae8024ec117f6c))


### Documentation

* **agent:** add docs for mattpocoks skill ([417c8d0](https://github.com/ASM-joynnovate/buddybird-api/commit/417c8d036fb1289f805f46c169b63ef9b21d2908))
* **agent:** add docs for mattpocoks skill ([c9ab56c](https://github.com/ASM-joynnovate/buddybird-api/commit/c9ab56c361a0fd80595651192e66f5304d4ed989))

## [0.1.2](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.1.1...v0.1.2) (2026-08-26)


### Bug Fixes

* **config:** read FRONTEND_CORS_ORIGIN from environment again ([e0105fd](https://github.com/ASM-joynnovate/buddybird-api/commit/e0105fd6c7abe25a88324b0cd8dcd8edffb424db))
* **config:** read FRONTEND_CORS_ORIGIN from environment again ([1ad28a2](https://github.com/ASM-joynnovate/buddybird-api/commit/1ad28a2f4ce5d27183262269254a554ad941bb61))
