# GitHub-based Trial Reset Feature

## Changes
- Added new GitHub-based trial reset functionality
- Improved code organization by separating GitHub reset logic into its own module
- Enhanced authentication data extraction and handling
- Added secure credential storage using keyring
- Improved error handling and user feedback
- Added automatic re-login after trial reset

## New Features
- GitHub authentication integration
- Secure credential management
- Automated trial reset process
- Session persistence
- Improved user experience with clear status messages

## Technical Details
- Uses DrissionPage for browser automation
- Implements secure credential storage with keyring
- Handles both cookie and localStorage token formats
- Supports automatic re-login after reset
- Maintains session persistence across resets

## Testing
- Tested on Windows 10, macOS, and Linux
- Verified with multiple GitHub accounts
- Confirmed successful trial reset and re-login
- Validated credential storage and retrieval
