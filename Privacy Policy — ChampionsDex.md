# Privacy Policy — ChampionsDex

**Effective date:** 9 May 2026  
**App:** ChampionsDex (unofficial fan companion for Pokémon Champions)  
**Platform:** Android, iOS (where distributed)

This policy describes how ChampionsDex (“the app”, “we”) handles information when you use it. ChampionsDex is **not** affiliated with, endorsed by, or sponsored by Nintendo, The Pokémon Company, Game Freak, or Creatures Inc.

---

## Summary

- **No account** is required. There is no sign-in and no user profile stored on our servers (we do not operate user accounts for this app).
- **Saved teams, Pokémon Builder builds, match logs, settings, backup-folder preference, and cached game reference data** are stored **on your device** by default.
- The app may **download reference JSON and images** from **public GitHub-hosted URLs** (see §2) and cache them locally.
- **Typography** uses the `google_fonts` package; font files may be **fetched from Google** the first time a style is used (or when the font cache is cleared), which is a standard HTTPS request, not used for advertising or behavioral profiling inside this app.
- **Optional crash reporting** may be enabled only in **specific release builds** that are compiled with a Sentry DSN (`SENTRY_DSN`). Default builds distributed without that flag do **not** send telemetry to Sentry.
- We **do not** include third-party advertising SDKs, behavioral analytics, or sale of personal data for advertising.
- **AI Coach** (AI tab): when the feature is available in your build and you run it, **prompts, model responses, and tool-call traffic** are sent **from your device directly to Google’s Generative Language API** (Gemini, OpenAI-compatible endpoint as implemented in the app). The app **does not** operate a ChampionsDex server that proxies those conversations. **Current preview-style builds** authenticate using an **application-embedded API credential** (not a key you type into Settings). **Credits / “Preview access”** preferences used to gate runs are stored **locally** (e.g. SharedPreferences), not on our servers.

---

## 1. Information stored on your device

The app stores, among other things:

- **Saved teams and related team-builder state** (via local databases such as Hive), including **local identifiers** (UUIDs) for each team record.
- **Saved Pokémon Builder builds** (single-Pokémon loadouts / drafts and related picker state) in Hive, also keyed by **local UUIDs**.
- **Match logger entries** (match format, participating teams/build snapshots, results, notes) in Hive, for your personal history and stats inside the app.
- **App settings and preferences** (via mechanisms such as SharedPreferences), including theme, accent, AI-related toggles, and **the backup export directory you choose** (where the app is allowed to write backup files on your device).
- **Cached copies** of public reference files (Pokémon, moves, items, abilities, image manifest) and **cached images** (e.g. sprites) so the app can work offline after the initial download.

**Uninstalling the app** removes application sandbox data on your device, subject to how your operating system handles backups and residual files. **Files you exported** (for example JSON backups in a folder you picked, or content sent via Share) remain under your control outside the app sandbox.

---

## 2. Network services and third-party infrastructure

### 2.1 Game reference data and artwork (GitHub and related hosts)

To obtain and update Pokédex, move, item, and related reference data, the app requests static files over HTTPS from:

- `https://raw.githubusercontent.com/cycalo/Pokemon-Champions-serebii-Scraper/main/data/`
- `https://raw.githubusercontent.com/cycalo/Pokemon-Champions-serebii-Scraper/main/images/`

**Supplementary Pokémon artwork** may also be requested from **`https://raw.githubusercontent.com/HybridShivam/Pokemon/master/assets/imagesHQ/`** when the app maps a species sprite to a high-quality static image.

**Optional artwork overrides** may load from **`raw.githubusercontent.com/PokeAPI/sprites`** for specific bundled URL mappings. Those are ordinary image GETs, not account sign-ins.

Those requests are ordinary HTTPS downloads initiated by the app (for example on first use, when you use **Settings → Clear cache & refresh data**, or when loading images that are not yet cached). **GitHub** (and its infrastructure providers) will see standard connection metadata that any HTTPS host would see (such as IP address and TLS metadata) as part of delivering the file. This app does not send your team names, notes, match logs, or saved rosters to those repositories as part of normal reference downloads.

You can delete cached JSON reference files from **Settings → Clear cache & refresh data** (image layers may retain sprites until cleared by the system or the app’s image cache; reference JSON fetches will run again when needed).

### 2.2 Google Fonts

The app uses the `google_fonts` package for typography (e.g. Inter and Poppins). Depending on platform behavior and cache state, the app may download font files from **Google** font endpoints over HTTPS. We do not use those requests for in-app advertising or cross-app tracking. For how Google handles network requests to its services, see Google’s own policies and disclosures.

### 2.3 Optional error reporting (Sentry)

Some **release** builds may be compiled with a build-time flag that enables [Sentry](https://sentry.io/) error monitoring. In those builds only:

- Uncaught errors and limited performance traces may be reported to **Sentry** under our project configuration.
- Our integration sets `sendDefaultPii` to **false**, disables screenshot attachment, and uses a **10%** sample rate for performance traces (`tracesSampleRate`) in the default bootstrap configuration.
- **Debug** builds do not enable Sentry in the default configuration, even if a DSN string were present.

Diagnostic reports can still include **technical context** that Sentry’s SDKs typically attach to help fix crashes (for example app version, device type, operating system version, and stack traces). They are **not** intended to collect free-text personal identifiers you type into the app.

If your build **does not** ship with a Sentry DSN, **no data is sent to Sentry** from that mechanism.

### 2.4 AI Coach (Google Gemini)

The **AI Coach** feature (AI tab) is optional. When it is enabled in your build and you start a flow, the app sends **prompts, model responses, and tool-call traffic** **directly from your device to Google’s Generative Language API** (Gemini, using the OpenAI-compatible surface implemented in the app).

- **Authentication:** preview-style builds may ship with an **embedded application credential** in the binary (obfuscation is not a substitute for secrecy—treat preview builds accordingly). The app **does not** require you to paste an API key into Settings for that path today.
- **Content:** traffic includes your interview answers, summaries of teams/builds you ask the Coach to work on, and structured tool results derived from the local dataset so the model can answer. It can include **Pokémon / move / item identifiers and stats** drawn from the same public reference data the app already downloads.
- **No proxy:** ChampionsDex does **not** host a server that relays Coach traffic; your device talks to Google’s endpoints.
- **Gating:** “Preview access”, credit balance, and related flags are stored **on-device** (SharedPreferences) for UX and abuse mitigation; they are not a cloud account.

See Google’s terms and privacy documentation for **Google AI / Gemini API** usage.

### 2.5 Backup and restore

**Settings → Backup & Restore** asks you to **choose a folder** (via the platform file/folder picker) where **Create backup** may write a **JSON export** of your saved **teams and Pokémon Builder builds**. On some Android versions the app may request **storage-related permissions** so it can write to the location you selected. **Match logs** are **not** included in that backup format.

If you use **Share** on a backup file, the **destination app you pick** receives that file.

### 2.6 Sharing features

If you use **Share** or export features (including team cards, text exports, or backup files), content is passed to the **share sheet or target app you choose** (for example Messages, email, or cloud storage). We do not control how those third-party apps process data.

---

## 3. What we do not do (by design)

- No **behavioral advertising** or ad mediation SDKs in the dependency set described for this open-source project.
- No requirement to provide your **name, email, phone number, or contacts**.
- No collection of **precise location** for advertising.
- No use of **advertising ID** for profiling inside this app’s own code paths described above.

---

## 4. Children’s privacy

ChampionsDex is a companion tool for planning teams in a video game. If you are a parent or guardian and have questions about your child’s use of the app, please review this policy together with them. If you believe we should remove project-side content tied to a support channel you control, contact us using the details below.

---

## 5. Your choices and rights

Because the app is **local-first** and does not operate a mandatory cloud account:

- **Export / delete “server-side” data:** There is typically **no server-side user database** maintained by the app authors for core functionality. Primary control is **on-device** (clear cache, delete teams in-app, change backup folder, or uninstall).
- **Regional rights:** Depending on where you live, privacy laws may give you additional rights regarding personal data. Much of what the app processes is **device-local** or **ephemeral HTTPS traffic** to third-party infrastructure as described above.

---

## 6. International users

If you use the app outside the country where the maintainer resides, your information may be processed in accordance with this policy and the practices of infrastructure providers you connect to (for example GitHub, Google Fonts, Google AI when you use AI Coach, or Sentry when enabled).

---

## 7. Changes to this policy

We may update this policy from time to time. The **effective date** at the top will change when we do. Material changes are reflected in the in-app **Settings → Privacy Policy** text when the app is updated, and in this file used for store listings.

---

## 8. Open-source project

Source code for ChampionsDex may be available in a public repository. **This policy governs the distributed app**, not necessarily every fork or unofficial build. Only builds from sources you trust should be installed.

---

## 9. Contact

For questions about this Privacy Policy:

- Open an issue on the **project’s public issue tracker** (replace with your repository URL when publishing), or  
- Contact the maintainer at **[your contact email or support URL]**.

---

*This document is provided for convenience and transparency. It is not legal advice. Have qualified counsel review store disclosures if you publish under a company name or in regulated jurisdictions.*
