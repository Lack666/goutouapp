# Phase 9A compatibility patch audit

The unchanged online `expo install --check` gate stopped full verification: first
on restricted network access, then on official SDK 57 patch recommendations.
The third attempt encountered a newly published Expo patch recommendation.
These are failed attempts, retained separately; no offline override or reduced
compatibility gate is used to claim acceptance.

Four direct dependencies move by one patch: expo57.0.27→57.0.28,
expo-crypto57.0.3→57.0.4, expo-router57.0.25→57.0.26 and
jest-expo57.0.5→57.0.6. The existing router UI peer moves57.0.22→57.0.23.
No Python dependency, new Mobile feature, SDK major, migration or model SDK is added.
The pnpm lockfile records resolved artifacts and peer graph changes.

Official registry metadata identifies all five packages as `expo/expo` monorepo
packages. SHA512 integrity values are in the committed lockfile; pnpm verified
its supply-chain policies while resolving. This is provenance and compatibility
review, not a comprehensive audit of every transitive package.

- [Expo install version validation](https://docs.expo.dev/more/expo-cli/#install)
- [pnpm exact release-age exclusions](https://pnpm.io/settings#minimumreleaseageexclude)
- [Expo package metadata](https://registry.npmjs.org/expo/57.0.28)
- [Crypto package metadata](https://registry.npmjs.org/expo-crypto/57.0.4)
- [Router package metadata](https://registry.npmjs.org/expo-router/57.0.26)
- [Jest package metadata](https://registry.npmjs.org/jest-expo/57.0.6)
- [UI peer metadata](https://registry.npmjs.org/@expo%2fui/57.0.23)

The repository already uses exact-version `minimumReleaseAgeExclude` entries.
The same mechanism permits these verified versions despite their recent
publication. `minimumReleaseAgeStrict: true`, strict peers, exact saving and
the existing build-script allowlist remain enabled. These exceptions do not
permit future versions or waive root acceptance.

Historical Phase8F native build hashes and results stay unchanged. They describe
the recorded build. Phase9A does not claim a new Android build for these patches;
current TypeScript/unit/Expo/web gates are rerun in full, and the historical native
artifact gate remains mandatory. Further native release validation remains in
the subsequent deployment scope.

Expo57.0.28 additionally requires recent monorepo versions of @expo/cli57.0.29,
@expo/fingerprint0.20.14, @expo/inline-modules0.1.8,
@expo/local-build-cache-provider57.0.9, @expo/prebuild-config57.0.18,
babel-preset-expo57.0.15, expo-modules-autolinking57.0.15,
expo-modules-core57.0.22 and expo-modules-jsi57.1.2. Official registry metadata
for each identifies the same Expo monorepo and provides SHA512 integrity; the
lockfile retains these values. Their release-age exceptions also name exact
versions. These are existing Expo internals, not new application infrastructure.
