# LocalSend Access (NVDA add-on)

An NVDA add-on that improves screen reader support for [LocalSend](https://localsend.org), the open-source file-sharing app for Windows.

LocalSend is built with Flutter, which leaves many controls unlabeled for screen readers. This add-on names the unlabeled buttons and check boxes, exposes the side tabs as tabs, and adds keyboard shortcuts.

## Features

- Names buttons and check boxes that NVDA otherwise reads without a name or does not read at all.
- Exposes the Receive, Send and Settings tabs as real tabs.
- Adds keyboard shortcuts for the main tasks.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| Alt+1 | Go to the Receive tab |
| Alt+2 | Go to the Send tab |
| Alt+3 | Go to the Settings tab |
| Alt+R | Scan for nearby devices |
| Alt+M | Open the send mode menu |

The shortcuts can be changed in NVDA's Input Gestures dialog, under the LocalSend category.

## Installation

1. Download `LocalSendAccess-0.2.4.nvda-addon` from this repository.
2. Open the file and choose Yes to install.
3. Restart NVDA.

Requires NVDA 2023.1 or later.

## Building from source

Zip `manifest.ini` and the `appModules` folder into an archive and rename it to `LocalSendAccess-<version>.nvda-addon`.

## Author

Mohammed Al-Fehaida

## License

GPL-2.0. See the LICENSE file.
