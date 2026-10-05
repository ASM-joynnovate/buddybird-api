# Changelog

## [2.0.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.5.0...v2.0.0) (2026-10-05)


### Miscellaneous Chores

* sync the lockfile project version ([#88](https://github.com/ASM-joynnovate/buddybird-api/issues/88)) ([1dfae38](https://github.com/ASM-joynnovate/buddybird-api/commit/1dfae38967e46bb5fce862d74d004d63f7f1d97f))

## [1.5.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.4.0...v1.5.0) (2026-10-05)


### Features

* **backoffice:** move backoffice APIs and add localized, scheduled notifications [BB-601] ([#87](https://github.com/ASM-joynnovate/buddybird-api/issues/87)) ([25e131a](https://github.com/ASM-joynnovate/buddybird-api/commit/25e131a9dde260ee786defa6135aa748471e42eb))
* **devices:** remove logged-out devices and add a device delete API ([#85](https://github.com/ASM-joynnovate/buddybird-api/issues/85)) ([13ccf13](https://github.com/ASM-joynnovate/buddybird-api/commit/13ccf135c523a0123c4ee0f6c05eaf0006f05f1d))

## [1.4.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.3.0...v1.4.0) (2026-10-05)


### Features

* **sessions:** measure active time from the session period ([#84](https://github.com/ASM-joynnovate/buddybird-api/issues/84)) ([eb5d340](https://github.com/ASM-joynnovate/buddybird-api/commit/eb5d340ed6319e7844e6abb26248e6309bd8d478))


### Bug Fixes

* **users:** accept standalone Hangul jamo in nicknames ([#82](https://github.com/ASM-joynnovate/buddybird-api/issues/82)) ([2478ba7](https://github.com/ASM-joynnovate/buddybird-api/commit/2478ba783bd2f15bcc6a644c92a8914cb20abf6a))

## [1.3.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.2.0...v1.3.0) (2026-10-04)


### Features

* **preset-words:** add backoffice API to manage word presets ([a379ae8](https://github.com/ASM-joynnovate/buddybird-api/commit/a379ae8d21bee2fbcbe332461f05ae3a54ed0392))
* **preset-words:** add backoffice API to manage word presets ([cbd165f](https://github.com/ASM-joynnovate/buddybird-api/commit/cbd165f0dcab9d6de8d37008a7e282ada63f6bba))

## [1.2.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.1.1...v1.2.0) (2026-10-04)


### Features

* apply app change requests and Sentry review fixes ([b976b9b](https://github.com/ASM-joynnovate/buddybird-api/commit/b976b9baaf39b48268539b75d284ab697247bfc1))
* **consumer:** back off receive failures and trace queue messages ([acc655c](https://github.com/ASM-joynnovate/buddybird-api/commit/acc655ca478e567a187e27b42079b43f34523ae0))
* **sessions:** filter session sounds by mimicry ([63ee49d](https://github.com/ASM-joynnovate/buddybird-api/commit/63ee49d4ed4528e97a8bc46b9e993782149dffb0))
* **settings:** store the marketing notification setting in user settings ([a30ce5d](https://github.com/ASM-joynnovate/buddybird-api/commit/a30ce5d2f6f90733ab66e53752a4ce90e20ac23e))
* **words:** add recording display order and return the new recording id ([1137919](https://github.com/ASM-joynnovate/buddybird-api/commit/1137919341d7c073c8be7d2f6dff9633bed9e90c))


### Bug Fixes

* **errors:** report 5xx custom errors to Sentry once ([e860249](https://github.com/ASM-joynnovate/buddybird-api/commit/e860249cda70b6b134d0b5aad030750d283a2d2d))
* **queues:** log failed enqueues with the exception ([3df9756](https://github.com/ASM-joynnovate/buddybird-api/commit/3df97568728a0552cfc1881da138b70777c67cf2))


### Performance Improvements

* **auth:** cache JWKS signing keys per key id ([5464f3e](https://github.com/ASM-joynnovate/buddybird-api/commit/5464f3eaefdf5e43a7a337f860c2b33ad651c60c))

## [1.1.1](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.1.0...v1.1.1) (2026-10-03)


### Bug Fixes

* **legacy:** restore the capture list pagination meta ([4e7cc64](https://github.com/ASM-joynnovate/buddybird-api/commit/4e7cc64531273de5b43b765b56ebb7bd2ec3f63d))
* **legacy:** restore the capture list pagination meta ([77eb28e](https://github.com/ASM-joynnovate/buddybird-api/commit/77eb28e6e23ebe643ec13e48c33bc22dca449c7d))

## [1.1.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.0.1...v1.1.0) (2026-10-03)


### Features

* **api:** apply API changes requested by the mobile app ([fd3c025](https://github.com/ASM-joynnovate/buddybird-api/commit/fd3c0252e68461cc36d4909a98d127036ec9f013))
* **api:** apply API changes requested by the mobile app ([8c69117](https://github.com/ASM-joynnovate/buddybird-api/commit/8c6911782d9653cf921a7804e357aa8495b503be))
* **devices:** replace fixed device role with session-based role ([4c9f830](https://github.com/ASM-joynnovate/buddybird-api/commit/4c9f8300e36b2714bf673ab84a883b9d1ccb9d24))
* **devices:** replace fixed device role with session-based role ([999500e](https://github.com/ASM-joynnovate/buddybird-api/commit/999500e8b66cdf7e7f756cd30d620333028a5a16))
* **legacy:** restore the clip batch upload API ([5f79196](https://github.com/ASM-joynnovate/buddybird-api/commit/5f791963687636cb5bd5adb571998583754577ea))
* **legacy:** restore the clip batch upload API ([093c7a1](https://github.com/ASM-joynnovate/buddybird-api/commit/093c7a1bdcbac36dd8442eb6cbc1ade7d5e30f96))
* **sentry:** add error, tracing, and log monitoring ([1da08fa](https://github.com/ASM-joynnovate/buddybird-api/commit/1da08fa05e0d97b2f0301b42c14871c393c45d4d))
* **sentry:** add error, tracing, and log monitoring ([a37a997](https://github.com/ASM-joynnovate/buddybird-api/commit/a37a997c6fabbb78766965582bb57cfb4dbb8036))


### Bug Fixes

* **api:** send no-store on every response and remove the ETag middleware ([2bfa0d9](https://github.com/ASM-joynnovate/buddybird-api/commit/2bfa0d99006ed30547803e8cfb91fffdc7172030))


### Performance Improvements

* **db:** fill joined relationships with contains_eager ([972b555](https://github.com/ASM-joynnovate/buddybird-api/commit/972b555b3a901c5e6e35e44c4120fb7336cbbc82))
* **s3:** make the storage dependency async ([bed322f](https://github.com/ASM-joynnovate/buddybird-api/commit/bed322fe2a0ec24010128a4a92acf2ba358e60e3))

## [1.0.1](https://github.com/ASM-joynnovate/buddybird-api/compare/v1.0.0...v1.0.1) (2026-09-19)


### Bug Fixes

* **consumer:** exit cleanly on SIGTERM ([9927b43](https://github.com/ASM-joynnovate/buddybird-api/commit/9927b435b28768b868286fe48c9c848f656dd192))
* **deploy:** run migration without the consumer container ([54ee365](https://github.com/ASM-joynnovate/buddybird-api/commit/54ee365b68fab303ea93655215e516722090617f))

## [1.0.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.6.0...v1.0.0) (2026-09-19)


### ⚠ BREAKING CHANGES

* **backoffice:** remove the VAD endpoint and replace BUDDYBIRD_ENV with ENV.

### Features

* **api:** add idempotency middleware and pagination params ([204b2f4](https://github.com/ASM-joynnovate/buddybird-api/commit/204b2f4e6cac9dc4e3e9b9ff75b16bb11a3d8243))
* **api:** add v2 API with absence sessions and presigned uploads ([bcc70e7](https://github.com/ASM-joynnovate/buddybird-api/commit/bcc70e7fc124655f941b2ab85803cceca263bcdd))
* **auth:** add Supabase login and user profile ([#48](https://github.com/ASM-joynnovate/buddybird-api/issues/48)) ([d430b2e](https://github.com/ASM-joynnovate/buddybird-api/commit/d430b2e6f5371845c4cfc4a6d22f77b373478784))
* **auth:** add withdrawal API and split app into legacy and role-based packages ([6d8cba4](https://github.com/ASM-joynnovate/buddybird-api/commit/6d8cba48167988d09de89573efd592eae81a825b))
* **auth:** change withdrawal endpoint to DELETE ([efbc8d5](https://github.com/ASM-joynnovate/buddybird-api/commit/efbc8d5aa52176ae15fbb15c5c48c80e8876daeb))
* **auth:** preserve user data and files on withdrawal ([e955358](https://github.com/ASM-joynnovate/buddybird-api/commit/e9553582d0fb37915d7fdda39da0d9c191660a32))
* **consent:** add consent documents table and backoffice API ([ba962ef](https://github.com/ASM-joynnovate/buddybird-api/commit/ba962ef2adfa1a823885ece3086b84f95c26f614))
* **consent:** add user consents API ([1526643](https://github.com/ASM-joynnovate/buddybird-api/commit/1526643a7f4de3ae9396bf3b04f2620f8f524091))
* **database:** add absence session tables and move enums to app/enums.py ([a88f8de](https://github.com/ASM-joynnovate/buddybird-api/commit/a88f8de0d84d6cac497f33b60c040dd87c6bd2f8))
* **device:** add device registration API ([87b0b32](https://github.com/ASM-joynnovate/buddybird-api/commit/87b0b32ed1bf9ea0dba702b0a7152599ec5c0ea7))
* **feedback:** add feedback API ([f13b800](https://github.com/ASM-joynnovate/buddybird-api/commit/f13b8009a0a8d18a982cfd7ca885456494a63526))
* **notice:** add notice API with images and read state ([1889d2e](https://github.com/ASM-joynnovate/buddybird-api/commit/1889d2e2a726ece1b18b3e293be5145083c772fc))
* **notification:** add push notification API with FCM delivery ([c13cbea](https://github.com/ASM-joynnovate/buddybird-api/commit/c13cbea31a708edbf40b38ce1575e7a7e63bcc2b))
* **parrot:** add parrot profile API ([2a02132](https://github.com/ASM-joynnovate/buddybird-api/commit/2a021322ec66b5eaf5015d34418ec119979a56ae))
* **session:** add absence session API ([6e3ec32](https://github.com/ASM-joynnovate/buddybird-api/commit/6e3ec32c4c519b0f876ac1341d76dcc444685e7a))
* **settings:** add user settings API ([8b5fc54](https://github.com/ASM-joynnovate/buddybird-api/commit/8b5fc545d82475fcac6fb094880f93322bd43ec1))
* **upload:** replace multipart uploads with presigned PUT URLs and SQS upload confirmation ([058015e](https://github.com/ASM-joynnovate/buddybird-api/commit/058015eda3aebb8f1bbd153d54d4fba7db78e708))
* **word:** add word and recording API ([6298d0b](https://github.com/ASM-joynnovate/buddybird-api/commit/6298d0b5c6a2e46f1068cbf5fe644e148a62750e))


### Bug Fixes

* **audio-segment:** preserve files on uncertain commits ([c7f3c76](https://github.com/ASM-joynnovate/buddybird-api/commit/c7f3c76b0a7bd8a317e9913a0f0712e67720b761))
* **auth:** detect new users from the insert result instead of the candidate id ([07b7bd4](https://github.com/ASM-joynnovate/buddybird-api/commit/07b7bd49c40b8113bfc0ca0b9142a07a14f8780c))


### Code Refactoring

* **backoffice:** simplify application structure ([10453a6](https://github.com/ASM-joynnovate/buddybird-api/commit/10453a6cc49195dc6f25fc8031c89a3d52f04500))

## [0.6.0](https://github.com/ASM-joynnovate/buddybird-api/compare/v0.5.0...v0.6.0) (2026-09-13)


### Features

* **audio_capture:** add species and device filters to capture list ([331d454](https://github.com/ASM-joynnovate/buddybird-api/commit/331d454229d520183aeddf515443ce1b6b1f61cf))
* **audio_capture:** add species and device info to capture list ([0d0ba7c](https://github.com/ASM-joynnovate/buddybird-api/commit/0d0ba7cb88739a0b5f6cd7a560d9ce0fd3212d75))
* **audio_capture:** expand capture responses and filters ([3df7b78](https://github.com/ASM-joynnovate/buddybird-api/commit/3df7b78d9839ba20bbd27b21ee033b69ee23b09a))
* **audio_capture:** return nested word data in capture responses ([266b98c](https://github.com/ASM-joynnovate/buddybird-api/commit/266b98ca885b6da737f862ca936bb085c596e02d))

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
