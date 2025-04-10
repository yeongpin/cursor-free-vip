import os
import sys
import json
import uuid
import hashlib
import shutil
import sqlite3
import platform
import re
import tempfile
import glob
import traceback
import configparser
import time        # Added import
import subprocess  # Added import
import errno       # Added import
from typing import Tuple, List, Optional

try:
    from colorama import Fore, Style, init
    init() # Initialize colorama
except ImportError:
    # Provide dummy colorama replacements if not installed
    print("Warning: colorama not found. Output will not be colored.")
    class DummyStyle:
        def __getattr__(self, name):
            return ""
    Fore = DummyStyle()
    Style = DummyStyle()
    def init(): pass
    init()

# Assuming these modules exist in your project structure
try:
    from new_signup import get_user_documents_path # Keep for config loading if needed elsewhere
    from config import get_config # Keep for config loading if needed elsewhere
except ImportError:
    print(f"{Fore.YELLOW}Warning: Could not import helper modules (new_signup, config). Using fallback for user documents path.{Style.RESET_ALL}")
    def get_user_documents_path():
        # Simple fallback: use home directory.
        return os.path.expanduser("~")
    def get_config(translator=None): # Dummy function
        return {} # Return empty config

# Define emoji constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "WARNING": "⚠️",
    "SEARCH": "🔍",
    "PATH": "➡️ ",
    "LOCK": "🔒",
}

# --- Path Finding Functions ---

def get_actual_home_dir() -> str:
    """Gets the actual user's home directory, even when run with sudo."""
    if sys.platform == "linux" and os.environ.get('SUDO_USER'):
        return os.path.expanduser(f"~{os.environ.get('SUDO_USER')}")
    return os.path.expanduser("~")

def find_cursor_config_dir(translator=None) -> Optional[str]:
    """Finds the Cursor user configuration directory for the current OS."""
    print(f"{Fore.CYAN}{EMOJI['SEARCH']} {translator.get('find_path.searching_config') if translator else 'Searching for Cursor configuration directory...'}{Style.RESET_ALL}")
    home_dir = get_actual_home_dir()
    system = platform.system()
    potential_paths: List[str] = []

    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            potential_paths.append(os.path.join(appdata, "Cursor"))
        # Add other potential Windows locations if necessary (e.g., %USERPROFILE%\.cursor)
    elif system == "Darwin": # macOS
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Cursor"))
    elif system == "Linux":
        # Snap: Check common snap location pattern (might be sandboxed)
        # Note: Modifying snap/flatpak might require specific commands or be restricted
        snap_config_path = os.path.join(home_dir, "snap/cursor/current/.config/cursor")
        if os.path.exists(snap_config_path):
             potential_paths.append(snap_config_path) # Add actual config path used by snap
        # Flatpak config path (often sandboxed within ~/.var/app)
        flatpak_config_path = os.path.join(home_dir, ".var/app/com.cursor.Cursor/config/cursor") # Example, check actual flatpak ID and path
        if os.path.exists(flatpak_config_path):
             potential_paths.append(flatpak_config_path)
        # Standard XDG config location
        potential_paths.append(os.path.join(home_dir, ".config/cursor"))
        # Older/non-standard locations
        potential_paths.append(os.path.join(home_dir, ".cursor")) # Less common now

    valid_config_dir = None
    checked_paths_log = []
    for path in potential_paths:
        normalized_path = os.path.abspath(path)
        checked_paths_log.append(normalized_path)
        # print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('find_path.checking', path=normalized_path) if translator else f'Checking: {normalized_path}'}{Style.RESET_ALL}") # Verbose
        # Check for a key directory/file presence (e.g., the 'User' subdirectory)
        user_subdir = os.path.join(normalized_path, "User")
        if os.path.isdir(normalized_path) and os.path.isdir(user_subdir):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('find_path.found_config_at', path=normalized_path) if translator else f'Found valid config directory at: {normalized_path}'}{Style.RESET_ALL}")
            valid_config_dir = normalized_path
            break # Stop at the first valid one found

    if not valid_config_dir:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.config_not_found') if translator else 'Cursor configuration directory not found.'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('find_path.checked_paths', paths=', '.join(checked_paths_log)) if translator else f'Checked paths: {", ".join(checked_paths_log)}'}{Style.RESET_ALL}")

    return valid_config_dir

def find_cursor_app_resource_dir(translator=None) -> Optional[str]:
    """
    Finds the Cursor application 'resources/app' directory.
    Validates by checking for package.json, main.js, AND workbench.desktop.main.js.
    """
    print(f"{Fore.CYAN}{EMOJI['SEARCH']} {translator.get('find_path.searching_app') if translator else 'Searching for Cursor application resource directory...'}{Style.RESET_ALL}")
    system = platform.system()
    potential_paths: List[str] = []
    home_dir = get_actual_home_dir() # Use actual home for user-specific searches

    if system == "Windows":
        localappdata = os.getenv("LOCALAPPDATA")
        programfiles = os.getenv("ProgramFiles")
        programfiles_x86 = os.getenv("ProgramFiles(x86)")
        if localappdata:
            potential_paths.append(os.path.join(localappdata, "Programs", "Cursor", "resources", "app"))
        if programfiles:
             potential_paths.append(os.path.join(programfiles, "Cursor", "resources", "app"))
        if programfiles_x86:
             potential_paths.append(os.path.join(programfiles_x86, "Cursor", "resources", "app"))
        # Add other potential locations like Scoop (%USERPROFILE%\scoop\apps\cursor\current\resources\app) if needed

    elif system == "Darwin": # macOS
        potential_paths.append(os.path.join(home_dir, "Applications/Cursor.app/Contents/Resources/app"))
        potential_paths.append("/Applications/Cursor.app/Contents/Resources/app")

    elif system == "Linux":
        # Standard package manager locations
        potential_paths.extend([
            "/opt/Cursor/resources/app",
            "/usr/share/cursor/resources/app",
            "/usr/lib/cursor/resources/app",      # Some package managers use /usr/lib
            "/usr/local/share/cursor/resources/app",
        ])
        # User-local installation
        potential_paths.append(os.path.join(home_dir, ".local/share/cursor/resources/app"))

        # AppImage extractions (common patterns)
        appimage_patterns = [
            "squashfs-root*/resources/app",
            "squashfs-root*/usr/share/cursor/resources/app",
            ".mount_Cursor*/resources/app", # Note: .mount* might be harder to predict
            "Applications/Cursor*/resources/app", # If extracted/installed to ~/Applications
        ]
        for pattern in appimage_patterns:
            potential_paths.extend(glob.glob(os.path.join(home_dir, pattern)))
            potential_paths.extend(glob.glob(os.path.join("/tmp", pattern))) # Check /tmp too
            potential_paths.extend(glob.glob(pattern)) # Check relative path

        # Flatpak (might be sandboxed)
        flatpak_path = "/var/lib/flatpak/app/com.cursor.Cursor/current/active/files/share/cursor/resources/app" # Check ID
        if os.path.exists(flatpak_path): potential_paths.append(flatpak_path)
        # Snap (might be sandboxed)
        snap_path = "/snap/cursor/current/resources/app" # Check snap name and structure
        if os.path.exists(snap_path): potential_paths.append(snap_path)
        snap_alt_path = os.path.join(home_dir, "snap/cursor/current/resources/app")
        if os.path.exists(snap_alt_path): potential_paths.append(snap_alt_path)

    # --- Check found paths ---
    checked_paths = set()
    valid_path = None
    for path in potential_paths:
        normalized_path = os.path.abspath(path)
        if normalized_path in checked_paths or not os.path.isdir(normalized_path):
            continue
        checked_paths.add(normalized_path)

        # print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('find_path.checking', path=normalized_path) if translator else f'Checking: {normalized_path}'}{Style.RESET_ALL}") # Verbose logging

        # *** Stricter Validation: Check for all key JS files needed for patching ***
        package_json_path = os.path.join(normalized_path, "package.json")
        main_js_path = os.path.join(normalized_path, "out/main.js")
        workbench_js_path = os.path.join(normalized_path, "out/vs/workbench/workbench.desktop.main.js")

        if os.path.isfile(package_json_path) and os.path.isfile(main_js_path) and os.path.isfile(workbench_js_path):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('find_path.found_app_at_valid', path=normalized_path) if translator else f'Found valid and complete app resource directory at: {normalized_path}'}{Style.RESET_ALL}")
            valid_path = normalized_path
            break # Found a fully valid path, stop searching
        # else:
            # Optional: Log why a path was skipped (e.g., missing workbench.js)
            # if os.path.exists(package_json_path) and os.path.exists(main_js_path):
            #     print(f"{Fore.YELLOW}{EMOJI['INFO']} Path {normalized_path} skipped (missing workbench.js){Style.RESET_ALL}")


    if not valid_path:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.app_not_found_strict') if translator else 'Cursor application resource directory (containing required JS files) not found.'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('find_path.checked_paths_app', paths=', '.join(sorted(list(checked_paths)))) if translator else f'Checked paths: {", ".join(sorted(list(checked_paths)))}'}{Style.RESET_ALL}")

    return valid_path


# --- Helper Functions (Modified) ---

def get_cursor_paths(app_resource_dir: str, translator=None) -> Tuple[Optional[str], Optional[str]]:
    """ Get package.json and main.js paths from the app resource dir"""
    # Assumes app_resource_dir is valid and contains these files based on find_cursor_app_resource_dir check
    pkg_path = os.path.join(app_resource_dir, "package.json")
    main_path = os.path.join(app_resource_dir, "out/main.js")

    # Basic sanity check, though find_cursor_app_resource_dir should guarantee this
    if not os.path.exists(pkg_path):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path) if translator else f'Essential file not found: {pkg_path}'}{Style.RESET_ALL}")
        return None, None
    if not os.path.exists(main_path):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.main_not_found', path=main_path) if translator else f'Essential file not found: {main_path}'}{Style.RESET_ALL}")
        return None, None

    return pkg_path, main_path

def get_workbench_cursor_path(app_resource_dir: str, translator=None) -> Optional[str]:
    """Get Cursor workbench.desktop.main.js path from the app resource dir"""
    # Assumes app_resource_dir is valid and contains this file based on find_cursor_app_resource_dir check
    main_path = os.path.join(app_resource_dir, "out/vs/workbench/workbench.desktop.main.js")

    # Basic sanity check
    if not os.path.exists(main_path):
        # This *shouldn't* happen if find_cursor_app_resource_dir worked correctly
        print(f"{Fore.RED}{EMOJI['ERROR']} Internal Error: {translator.get('reset.workbench_js_not_found_unexpected', path=main_path) if translator else f'Workbench JS file unexpectedly not found after validation: {main_path}'}{Style.RESET_ALL}")
        return None

    return main_path


def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """Version number check"""
    version_pattern = r"^\d+\.\d+\.\d+" # Allow suffixes like -nightly
    try:
        match = re.match(version_pattern, version)
        if not match:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version) if translator else f'Invalid version format: {version}'}{Style.RESET_ALL}")
            return False

        clean_version = match.group(0) # Use only the numeric part for comparison

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(clean_version)

        if min_version:
            min_v = parse_version(min_version)
            if current < min_v:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.version_too_low', version=version, min_version=min_version) if translator else f'Version {version} is lower than minimum {min_version}'}{Style.RESET_ALL}")
                return False # Treat as failure for logic requiring min version

        if max_version:
             max_v = parse_version(max_version)
             if current > max_v:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.version_too_high', version=version, max_version=max_version) if translator else f'Version {version} is higher than maximum {max_version}'}{Style.RESET_ALL}")
                # Decide if this is a failure or just a warning based on context
                # return False # Uncomment if exceeding max_version should block

        return True

    except ValueError:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_parse_error', version=version) if translator else f'Error parsing version components in: {version}'}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_error', error=str(e)) if translator else f'Version check failed: {str(e)}'}{Style.RESET_ALL}")
        return False

def check_cursor_version(pkg_path: str, translator) -> Optional[bool]:
    """Check Cursor version from package.json. Returns True if >= 0.45.0, False if lower, None on error."""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.reading_package_json', path=pkg_path) if translator else f'Reading package.json: {pkg_path}'}{Style.RESET_ALL}")

        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except UnicodeDecodeError:
            try:
                with open(pkg_path, "r", encoding="latin-1") as f: # Fallback encoding
                    data = json.load(f)
            except Exception as read_err:
                 print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_file_error_fallback', file='package.json', error=str(read_err)) if translator else f'Error reading package.json (even with fallback encoding): {read_err}'}{Style.RESET_ALL}")
                 return None

        if not isinstance(data, dict):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object') if translator else 'Invalid JSON object in package.json'}{Style.RESET_ALL}")
            return None

        version = data.get("version")
        if not version or not isinstance(version, str):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_version_field') if translator else 'Could not find "version" field in package.json'}{Style.RESET_ALL}")
            return None

        version = version.strip()
        if not version:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_field_empty') if translator else '"version" field is empty in package.json'}{Style.RESET_ALL}")
            return None

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.found_version', version=version) if translator else f'Found version: {version}'}{Style.RESET_ALL}")

        # Use version_check for comparison
        min_version_str = "0.45.0"
        is_min_met = version_check(version, min_version=min_version_str, translator=translator)

        if is_min_met:
             print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.version_check_passed_min', version=version, min_version=min_version_str) if translator else f'Version {version} meets minimum requirement {min_version_str}'}{Style.RESET_ALL}")
             return True
        else:
             # Version check already printed the warning if too low or format error
             return False # Explicitly return False if below min_version or format invalid

    except FileNotFoundError:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path) if translator else f'File not found: {pkg_path}'}{Style.RESET_ALL}")
        return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object') if translator else 'Invalid JSON in package.json'}{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.check_version_failed', error=str(e)) if translator else f'Failed to check version: {str(e)}'}{Style.RESET_ALL}")
        # print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}") # Optional: uncomment for debug
        return None


def modify_file_content(file_path: str, replacements: List[Tuple[str, str]], translator=None, is_js=False) -> bool:
    """ Safely modifies file content with replacements, handling permissions and backup. """
    if not os.path.exists(file_path):
         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_found', path=file_path) if translator else f'File not found: {file_path}'}{Style.RESET_ALL}")
         return False

    if not os.access(file_path, os.W_OK):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission', path=file_path) if translator else f'No write permission for: {file_path}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['LOCK']} {translator.get('reset.try_sudo') if translator else 'Try running the script with sudo or as Administrator.'}{Style.RESET_ALL}")
        return False

    # Save original file permissions before any operation
    try:
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        # Only get uid/gid if not on Windows
        original_uid = original_stat.st_uid if os.name != 'nt' else -1
        original_gid = original_stat.st_gid if os.name != 'nt' else -1
    except OSError as stat_err:
         print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.stat_error', path=file_path, error=str(stat_err)) if translator else f'Could not get original permissions for {file_path}: {stat_err}'}{Style.RESET_ALL}")
         # Continue, but permissions might not be restored perfectly
         original_mode = None


    # --- Backup ---
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak" # Timestamped backup
    try:
        # Create backup only if it doesn't already exist with this timestamp (unlikely but safe)
        if not os.path.exists(backup_path):
             shutil.copy2(file_path, backup_path) # copy2 preserves metadata
             print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('reset.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
        # else: # Don't print backup exists every time, only if it's the '.bak' generic one
        #      print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.backup_exists_file', path=backup_path) if translator else f'Backup already exists: {backup_path}'}{Style.RESET_ALL}")
    except Exception as backup_err:
         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.backup_failed_file', file=os.path.basename(file_path), error=str(backup_err)) if translator else f'Could not create backup for {os.path.basename(file_path)}: {backup_err}'}{Style.RESET_ALL}")
         return False # Critical failure if backup can't be made


    # --- Read Content ---
    print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('reset.reading_file', file=os.path.basename(file_path)) if translator else f'Reading {os.path.basename(file_path)}...'}{Style.RESET_ALL}")
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
            content = main_file.read()
    except Exception as read_err:
         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_file_error', file=file_path, error=str(read_err)) if translator else f'Error reading file {file_path}: {read_err}'}{Style.RESET_ALL}")
         return False


    # --- Modify Content ---
    modified_content = content
    found_any = False
    changes_made = False
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.applying_patches', file=os.path.basename(file_path)) if translator else f'Applying patches to {os.path.basename(file_path)}...'}{Style.RESET_ALL}")
    for i, (old_pattern, new_pattern) in enumerate(replacements):
        original_part = None
        if is_js: # Use regex for JS
            match = re.search(old_pattern, modified_content)
            if match:
                original_part = match.group(0) # Get the exact text that matched
                temp_content = re.sub(old_pattern, new_pattern, modified_content, count=1) # Apply one replacement at a time
                if temp_content != modified_content: # Check if sub actually changed something
                    modified_content = temp_content
                    print(f"{Fore.GREEN}   {EMOJI['SUCCESS']} {translator.get('reset.patch_applied', index=i+1) if translator else f'Applied patch #{i+1}'}{Style.RESET_ALL}")
                    found_any = True
                    changes_made = True
                else:
                     # Regex matched but substitution resulted in the same string? Unlikely but possible.
                     print(f"{Fore.YELLOW}   {EMOJI['INFO']} {translator.get('reset.patch_matched_no_change', index=i+1) if translator else f'Patch #{i+1} matched but resulted in no change.'}{Style.RESET_ALL}")
                     found_any = True # Pattern was technically found
            # else: # Only print if not found if you need verbose logs
            #     print(f"{Fore.YELLOW}   {EMOJI['INFO']} {translator.get('reset.patch_not_found', index=i+1) if translator else f'Patch #{i+1} pattern not found.'}{Style.RESET_ALL}")

        else: # Use simple string replacement
            if old_pattern in modified_content:
                temp_content = modified_content.replace(old_pattern, new_pattern)
                if temp_content != modified_content:
                    modified_content = temp_content
                    print(f"{Fore.GREEN}   {EMOJI['SUCCESS']} {translator.get('reset.replacement_applied', index=i+1) if translator else f'Applied replacement #{i+1}'}{Style.RESET_ALL}")
                    found_any = True
                    changes_made = True
                else:
                    print(f"{Fore.YELLOW}   {EMOJI['INFO']} {translator.get('reset.replacement_matched_no_change', index=i+1) if translator else f'Replacement #{i+1} matched but resulted in no change.'}{Style.RESET_ALL}")
                    found_any = True
            # else: # Only print if not found if you need verbose logs
            #    print(f"{Fore.YELLOW}   {EMOJI['INFO']} {translator.get('reset.replacement_not_found', index=i+1) if translator else f'Replacement #{i+1} pattern not found.'}{Style.RESET_ALL}")

    if not found_any:
         print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.no_patterns_found', file=os.path.basename(file_path)) if translator else f'No target patterns found in {os.path.basename(file_path)}. File may already be patched or structure changed.'}{Style.RESET_ALL}")
         # This is not necessarily an error, so return True
         return True
    elif not changes_made:
         print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.patterns_found_no_change', file=os.path.basename(file_path)) if translator else f'Patterns found in {os.path.basename(file_path)}, but no effective changes were made. Check patterns/replacements.'}{Style.RESET_ALL}")
         # Also not necessarily an error, maybe replacements were identical
         return True


    # --- Write Modified Content ---
    # Use tempfile for atomic write
    tmp_path = None
    try:
        # Create temp file in the same directory to ensure atomic move works across filesystems
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False, dir=os.path.dirname(file_path), prefix=f"{os.path.basename(file_path)}.") as tmp_file:
            tmp_file.write(modified_content)
            tmp_path = tmp_file.name # Get the temporary file path

        # Replace original with temp file (atomic on most POSIX, best effort on Windows)
        shutil.move(tmp_path, file_path)
        tmp_path = None # Indicate move was successful

        # Restore original permissions and ownership if possible
        if original_mode is not None:
            try:
                os.chmod(file_path, original_mode)
                if os.name != "nt" and original_uid != -1 and original_gid != -1:
                     # Attempt chown only if we might have permissions (e.g., running as root)
                     # and we successfully got original uid/gid
                     try:
                         os.chown(file_path, original_uid, original_gid)
                     except OSError as chown_err:
                          # Ignore permission errors here, as we might not be root even if we could chmod
                          if chown_err.errno != errno.EPERM:
                              raise # Re-raise unexpected chown errors
                          else:
                              print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.chown_skipped', file=os.path.basename(file_path)) if translator else f'Skipped restoring ownership for {os.path.basename(file_path)} (requires root). Permissions restored.'}{Style.RESET_ALL}")
            except OSError as perm_err:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.permission_restore_failed', file=os.path.basename(file_path), error=str(perm_err)) if translator else f'Could not restore original permissions/ownership for {os.path.basename(file_path)}: {perm_err}'}{Style.RESET_ALL}")


        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified_success', file=os.path.basename(file_path)) if translator else f'Successfully modified {os.path.basename(file_path)}'}{Style.RESET_ALL}")
        return True

    except Exception as write_err:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', file=os.path.basename(file_path), error=str(write_err))}{Style.RESET_ALL}")
        # Attempt to restore backup if modification failed
        if os.path.exists(backup_path):
            try:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.restoring_backup', path=backup_path) if translator else f'Attempting to restore backup: {backup_path}'}{Style.RESET_ALL}")
                # Use move to put the backup back in place
                shutil.move(backup_path, file_path)
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.restore_success') if translator else 'Backup restored.'}{Style.RESET_ALL}")
            except Exception as restore_err:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.restore_failed', error=str(restore_err)) if translator else f'Failed to restore backup: {restore_err}'}{Style.RESET_ALL}")
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.manual_restore_needed', original=file_path, backup=backup_path) if translator else f'Manual intervention may be needed. Original: {file_path}, Backup: {backup_path}'}{Style.RESET_ALL}")
        return False
    finally:
        # Clean up temp file if it wasn't moved (e.g., due to error)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass # Ignore cleanup errors

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """Modify workbench.desktop.main.js content."""
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.modifying_workbench') if translator else 'Modifying workbench.desktop.main.js...'}{Style.RESET_ALL}")
    system = platform.system()
    repo_url = "https://github.com/your-repo/cursor-free-vip" # Make URL easily changeable

    # Define platform-specific patterns for the "Upgrade to Pro" button
    # These patterns try to be more robust by matching variable names more loosely (\w+)
    # but are still highly susceptible to breaking with Cursor updates.
    if system == "Windows" or system == "Linux":
        # Look for something like: ...,title:"Upgrade to Pro",...,codicon: X.rocket,...,onClick: Y.pay...
        # The key is to capture the variable before .rocket (like F) and the variable before .pay (like t)
        # This regex is complex and might need adjustment based on actual minified code.
        # Simpler approach: Find the title and the onClick part somewhat nearby.
        cbutton_old_regex = r'(title:"Upgrade to Pro".{0,100}?get codicon\(\)\{return \w+\.rocket\}.{0,100}?get onClick\(\)\{return )(\w+)(\.pay\})'
        # Replace the captured Y.pay} part with the GitHub link function
        cbutton_new_repl = rf'\g<1>function(){{window.open("{repo_url}","_blank")\}})}}(\g<3>' # Replace only the onClick body

    elif system == "Darwin":
        # macOS might use different variable names (e.g., $ instead of F)
        cbutton_old_regex = r'(title:"Upgrade to Pro".{0,100}?get codicon\(\)\{return \w+\.rocket\}.{0,100}?get onClick\(\)\{return )(\w+)(\.pay\})' # Assume similar structure
        cbutton_new_repl = rf'\g<1>function(){{window.open("{repo_url}","_blank")\}})}}(\g<3>'

    else:
         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.unsupported_os_patching') if translator else 'Unsupported OS for workbench patching.'}{Style.RESET_ALL}")
         return False

    # Other common patches (usually simple string replacements)
    replacements_simple = [
        ('<div>Pro Trial', '<div>Pro'),       # Change badge text
        ('notifications-toasts', 'notifications-toasts hidden'), # Hide toast notifications
    ]

    # Apply simple replacements first
    success_simple = modify_file_content(file_path, replacements_simple, translator, is_js=False)
    if not success_simple:
         print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.workbench_simple_patch_failed') if translator else 'Failed applying simple patches to workbench.js. Continuing with button patch attempt.'}{Style.RESET_ALL}")
         # Decide if this should be a fatal error. Let's try the button patch anyway.

    # Apply the more complex regex replacement for the button
    # Note: modify_file_content handles reading/writing/backup again
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.workbench_button_patch_attempt') if translator else 'Attempting Upgrade button patch...'}{Style.RESET_ALL}")
    replacements_regex = [
        (cbutton_old_regex, cbutton_new_repl)
    ]
    success_button = modify_file_content(file_path, replacements_regex, translator, is_js=True) # is_js=True for regex

    # Return True if at least the button patch (or simple patches if button wasn't found) seemed successful
    # modify_file_content returns True if no patterns were found or if changes were made successfully.
    return success_button


def modify_main_js(main_path: str, translator) -> bool:
    """Modify main.js file to bypass certain checks (use with caution)."""
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.modifying_mainjs') if translator else 'Modifying main.js...'}{Style.RESET_ALL}")
    # WARNING: These patches might break functionality or violate terms of service.
    # They aim to prevent the overriding of machine IDs generated by this script.
    # Patterns target functions that might fetch system IDs.
    # Example: `async getMachineId(){return external_fetch()??fallback}` becomes `async getMachineId(){return fallback}`
    replacements = [
        # Pattern 1: Look for async getMachineId(){ return ... ?? some_fallback }
        # Make it less greedy to avoid consuming the closing brace: [^?}]+? matches characters except ? or } one or more times, non-greedily
        (r"(async getMachineId\(\)\{return )([^?]+?\?\?)([^}]+)\}", r"\1\3}"),
        # Pattern 2: Look for async getMacMachineId(){ return ... ?? some_fallback }
        (r"(async getMacMachineId\(\)\{return )([^?]+?\?\?)([^}]+)\}", r"\1\3}"),
        # Add more patterns here if needed based on main.js analysis
    ]

    return modify_file_content(main_path, replacements, translator, is_js=True)


def patch_cursor_get_machine_id(app_resource_dir: str, translator) -> bool:
    """Patch Cursor getMachineId function in main.js if version is >= 0.45.0."""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.start_patching_mainjs') if translator else 'Starting main.js patching process...'}{Style.RESET_ALL}")

        pkg_path, main_path = get_cursor_paths(app_resource_dir, translator)
        if not pkg_path or not main_path:
            # Error already printed by get_cursor_paths if app_resource_dir was valid but files missing (shouldn't happen now)
            # Or if app_resource_dir was None
             print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.cannot_patch_mainjs_paths') if translator else 'Cannot patch main.js: Essential paths not found.'}{Style.RESET_ALL}")
             return False

        # --- Check Version ---
        # Rely on the check performed in reset_machine_ids which calls this function conditionally
        # If called directly, uncomment this block:
        # print(f"{Fore.CYAN}{EMOJI['INFO']} Checking version before patching main.js...{Style.RESET_ALL}")
        # version_status = check_cursor_version(pkg_path, translator)
        # if version_status is not True: # Checks for False or None
        #    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.patch_skipped_version_mainjs') if translator else 'Skipping main.js patch due to version check failure or version < 0.45.0.'}{Style.RESET_ALL}")
        #    return True # Not an error, just skipped

        # --- Modify main.js ---
        if not modify_main_js(main_path, translator):
            # Error logged within modify_main_js
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed_mainjs') if translator else 'Patching main.js failed.'}{Style.RESET_ALL}")
            return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_completed_mainjs') if translator else 'main.js patched successfully.'}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e)) if translator else f'Patch process failed: {str(e)}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False


# --- Main Resetter Class ---

class MachineIDResetter:
    def __init__(self, translator=None):
        self.translator = translator
        self.config_dir: Optional[str] = None
        self.storage_json_path: Optional[str] = None
        self.state_db_path: Optional[str] = None
        self.machine_id_file_path: Optional[str] = None
        self.app_resource_dir: Optional[str] = None # For patching JS

        # Attempt to find paths immediately upon initialization
        self._find_paths()

    def _find_paths(self):
        """Locate all necessary Cursor paths."""
        print(f"\n{Fore.CYAN}{'='*20} Path Finding {'='*20}{Style.RESET_ALL}")
        self.config_dir = find_cursor_config_dir(self.translator)
        self.app_resource_dir = find_cursor_app_resource_dir(self.translator) # Find app dir too

        if self.config_dir:
            user_global_storage = os.path.join(self.config_dir, "User", "globalStorage")
            # Ensure parent dir exists before resolving paths inside
            os.makedirs(user_global_storage, exist_ok=True)

            self.storage_json_path = os.path.join(user_global_storage, "storage.json")
            self.state_db_path = os.path.join(user_global_storage, "state.vscdb")

            # Determine machineId file path based on OS convention relative to config_dir
            system = platform.system()
            if system == "Linux":
                 # Often directly in .config/cursor, not User/globalStorage
                 self.machine_id_file_path = os.path.join(self.config_dir, "machineid")
            elif system == "Windows":
                 # Usually in the root of %APPDATA%/Cursor
                 self.machine_id_file_path = os.path.join(self.config_dir, "machineId")
            elif system == "Darwin":
                 # Usually in the root of Library/Application Support/Cursor
                 self.machine_id_file_path = os.path.join(self.config_dir, "machineId")
            else:
                self.machine_id_file_path = None # Fallback or error

            # Log found paths
            print(f"{EMOJI['PATH']}{Fore.GREEN}Config Dir:{Style.RESET_ALL} {self.config_dir}")
            print(f"{EMOJI['PATH']}{Fore.GREEN}Storage JSON:{Style.RESET_ALL} {self.storage_json_path}")
            print(f"{EMOJI['PATH']}{Fore.GREEN}State DB:{Style.RESET_ALL} {self.state_db_path}")
            if self.machine_id_file_path:
                print(f"{EMOJI['PATH']}{Fore.GREEN}Machine ID File:{Style.RESET_ALL} {self.machine_id_file_path}")
            else:
                 print(f"{EMOJI['PATH']}{Fore.YELLOW}Machine ID File:{Style.RESET_ALL} (Could not determine standard path)")

        else:
            # Config dir is essential for resetting IDs
            print(f"{Fore.RED}{EMOJI['ERROR']} Critical: Cursor configuration directory not found. Cannot proceed with ID reset.{Style.RESET_ALL}")
            # Set paths to None to prevent errors later
            self.storage_json_path = None
            self.state_db_path = None
            self.machine_id_file_path = None


        if self.app_resource_dir:
             print(f"{EMOJI['PATH']}{Fore.GREEN}App Resource Dir:{Style.RESET_ALL} {self.app_resource_dir}")
        else:
             # App dir is only needed for patching
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} App resource directory not found. JS patching will be skipped.{Style.RESET_ALL}")

        print(f"{Fore.CYAN}{'='*53}{Style.RESET_ALL}\n")


    def _check_prerequisites(self) -> bool:
        """Check if essential paths for ID reset and permissions are available."""
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking_prereqs') if self.translator else 'Checking prerequisites...'}{Style.RESET_ALL}")
        # ID Reset Prerequisites
        if not self.config_dir or not self.storage_json_path or not self.state_db_path or not self.machine_id_file_path:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.error_missing_paths_reset') if self.translator else 'One or more essential paths for ID reset not found. Cannot proceed.'}{Style.RESET_ALL}")
             return False

        # Check permissions for files we absolutely need to modify/create for ID reset
        files_to_check = {
            "Storage JSON": self.storage_json_path,
            "State DB": self.state_db_path,
            # Don't check machineId file itself yet, check its directory below
        }
        permission_ok = True
        for name, path in files_to_check.items():
             parent_dir = os.path.dirname(path)
             # Check if parent directory exists and is writable
             if not os.path.isdir(parent_dir):
                  print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.parent_dir_missing', path=parent_dir) if self.translator else f'Parent directory does not exist: {parent_dir}. Attempting to create.'}{Style.RESET_ALL}")
                  try:
                       os.makedirs(parent_dir, exist_ok=True)
                       print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.parent_dir_created', path=parent_dir) if translator else f'Created directory: {parent_dir}'}{Style.RESET_ALL}")
                  except OSError as mkdir_err:
                       print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.mkdir_failed', path=parent_dir, error=str(mkdir_err)) if translator else f'Failed to create directory {parent_dir}: {mkdir_err}'}{Style.RESET_ALL}")
                       permission_ok = False
                       continue # Skip further checks for this file

             if not os.access(parent_dir, os.W_OK):
                  print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_permission_dir', path=parent_dir) if translator else f'Write permission denied for directory: {parent_dir}'}{Style.RESET_ALL}")
                  permission_ok = False

             # If the file exists, check if it's writable
             if os.path.exists(path) and not os.access(path, os.W_OK):
                  print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_permission_file', name=name, path=path) if translator else f'Write permission denied for existing {name} file: {path}'}{Style.RESET_ALL}")
                  permission_ok = False


        # Check permissions for the directory containing the separate machineId file
        machine_id_dir = os.path.dirname(self.machine_id_file_path)
        if not os.path.isdir(machine_id_dir):
             try:
                  os.makedirs(machine_id_dir, exist_ok=True)
             except OSError as mkdir_err:
                  print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.mkdir_failed', path=machine_id_dir, error=str(mkdir_err)) if translator else f'Failed to create machineId directory {machine_id_dir}: {mkdir_err}'}{Style.RESET_ALL}")
                  permission_ok = False
        elif not os.access(machine_id_dir, os.W_OK):
             print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_permission_dir', path=machine_id_dir) if translator else f'Write permission denied for directory: {machine_id_dir} (needed for machineId file)'}{Style.RESET_ALL}")
             permission_ok = False
        # Check machineId file itself if it exists
        if os.path.exists(self.machine_id_file_path) and not os.access(self.machine_id_file_path, os.W_OK):
             print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_permission_file', name='machineId', path=self.machine_id_file_path) if translator else f'Write permission denied for existing machineId file: {self.machine_id_file_path}'}{Style.RESET_ALL}")
             permission_ok = False


        if not permission_ok:
             print(f"{Fore.YELLOW}{EMOJI['LOCK']} {translator.get('reset.try_sudo') if translator else 'Try running the script with sudo or as Administrator.'}{Style.RESET_ALL}")
             return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.prereq_ok') if translator else 'Prerequisites check passed.'}{Style.RESET_ALL}")
        return True


    def generate_new_ids(self) -> dict:
        """Generate new machine IDs and related telemetry/storage values."""
        print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.generating') if self.translator else 'Generating New Machine IDs...'}{Style.RESET_ALL}")
        dev_device_id = str(uuid.uuid4())
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        # Newer VSCode/Cursor often uses UUID format for macMachineId, stick to that unless proven otherwise
        mac_machine_id_uuid = str(uuid.uuid4())
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}" # Standard GUID format
        instance_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4()) + str(int(time.time() * 1000)) # Common VSCode format

        new_ids = {
            # Telemetry related
            "telemetry.telemetryLevel": "off", # Explicitly turn off telemetry
            "telemetry.instanceId": instance_id,
            "telemetry.sessionId": session_id,
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id_uuid, # Use UUID format
            "telemetry.machineId": machine_id, # Use the SHA256 hash? Or same as devDeviceId? Let's stick to SHA for now.
            "telemetry.sqmId": sqm_id,

            # Storage related
            "storage.serviceMachineId": dev_device_id, # Usually matches devDeviceId

            # Other potentially useful resets
            "workbench.startupEditor": "none", # Don't open previous files
            "extensions.ignoreRecommendations": True, # Don't show recommendations

            # Reset potential trial/login related keys (use generic keys, actual keys might differ)
            # Setting these to empty/default might help clear state.
            "cursor.internal.loginToken": "",
            "cursor.internal.userTier": "free",
            "cursor.internal.trialExpired": False, # Reset trial status
            "cursor.internal.lastCheckTimestamp": 0,
            "cursor.initialStartup": False, # Force any first-run logic?
        }

        print(f"{Fore.CYAN}Generated values:{Style.RESET_ALL}")
        for key, value in new_ids.items():
             # Only print key IDs for brevity, not all the settings
             if 'Id' in key or 'Tier' in key or 'Token' in key:
                 print(f"  {EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")

        # --- Update the separate machineId file ---
        # Which ID should go here? It varies. Sometimes it's the SHA256 `machineId`,
        # sometimes it's `devDeviceId`. Let's use `devDeviceId` as it seems more
        # consistent with VSCode's `serviceMachineId` linkage.
        print(f"{Fore.CYAN}  {EMOJI['INFO']} Attempting to update separate machineId file with: {Fore.GREEN}{dev_device_id}{Style.RESET_ALL}")
        if not self.update_machine_id_file(dev_device_id):
            # This failure is usually non-critical for the core reset but log it.
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.machineid_update_failed_warn') if self.translator else 'Warning: Failed to update the separate machineId file. Reset will continue.'}{Style.RESET_ALL}")

        return new_ids


    def update_storage_json(self, new_ids: dict) -> bool:
        """Update the storage.json file."""
        if not self.storage_json_path:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.json_path_missing') if self.translator else 'Cannot update storage.json: Path not found.'}{Style.RESET_ALL}")
             return False
        print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.updating_json') if self.translator else 'Updating storage.json...'}{Style.RESET_ALL}")

        # --- Backup ---
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.storage_json_path}.{timestamp}.bak"
        try:
            if os.path.exists(self.storage_json_path):
                 shutil.copy2(self.storage_json_path, backup_path)
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            else:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.json_not_exist_creating') if self.translator else 'storage.json does not exist, will create.'}{Style.RESET_ALL}")
                 # Ensure parent directory exists if file doesn't
                 os.makedirs(os.path.dirname(self.storage_json_path), exist_ok=True)
        except Exception as backup_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.backup_failed_file', file='storage.json', error=str(backup_err)) if self.translator else f'Could not create backup for storage.json: {backup_err}'}{Style.RESET_ALL}")
            return False # Don't proceed without backup if file exists and backup fails

        # --- Read existing or create new ---
        config_data = {}
        if os.path.exists(self.storage_json_path):
            try:
                with open(self.storage_json_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                if not isinstance(config_data, dict):
                     print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.json_invalid_format') if self.translator else 'Warning: storage.json is not a valid JSON object. Overwriting.'}{Style.RESET_ALL}")
                     config_data = {} # Reset if invalid format
            except json.JSONDecodeError:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.json_decode_error') if self.translator else 'Warning: storage.json is corrupted. Overwriting.'}{Style.RESET_ALL}")
                config_data = {} # Reset if corrupted
            except Exception as read_err:
                 print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.read_file_error', file='storage.json', error=str(read_err)) if translator else f'Error reading storage.json: {read_err}'}{Style.RESET_ALL}")
                 return False

        # --- Update with new IDs ---
        # Overwrite existing keys, add new ones
        config_data.update(new_ids)

        # --- Write back using temp file for atomicity ---
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=os.path.dirname(self.storage_json_path), prefix="storage.json.") as tmp_file:
                json.dump(config_data, tmp_file, indent=4) # Pretty print
                tmp_path = tmp_file.name

            shutil.move(tmp_path, self.storage_json_path)
            tmp_path = None # Indicate move was successful
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.json_update_success') if self.translator else 'storage.json updated successfully.'}{Style.RESET_ALL}")
            return True
        except Exception as write_err:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.write_file_error', file='storage.json', error=str(write_err))}{Style.RESET_ALL}")
             # Attempt restore from backup
             if os.path.exists(backup_path):
                  try:
                      print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.restoring_backup', path=backup_path) if translator else f'Attempting to restore backup: {backup_path}'}{Style.RESET_ALL}")
                      shutil.move(backup_path, self.storage_json_path) # Move backup back
                      print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.restore_success') if translator else 'Backup restored.'}{Style.RESET_ALL}")
                  except Exception as restore_err:
                      print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.restore_failed', error=str(restore_err))}{Style.RESET_ALL}")
                      print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.manual_restore_needed', original=self.storage_json_path, backup=backup_path) if translator else f'Manual restore needed for {self.storage_json_path} from {backup_path}'}{Style.RESET_ALL}")
             return False
        finally:
             # Clean up temp file if it wasn't moved
             if tmp_path and os.path.exists(tmp_path):
                  try: os.unlink(tmp_path)
                  except OSError: pass


    def update_sqlite_db(self, new_ids: dict) -> bool:
        """Update machine IDs in the SQLite state.vscdb database."""
        if not self.state_db_path:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_path_missing') if self.translator else 'Cannot update state.vscdb: Path not found.'}{Style.RESET_ALL}")
             return False
        print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.updating_sqlite') if self.translator else 'Updating state.vscdb...'}{Style.RESET_ALL}")

        # --- Backup ---
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.state_db_path}.{timestamp}.bak"
        try:
            if os.path.exists(self.state_db_path):
                shutil.copy2(self.state_db_path, backup_path)
                print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            else:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqlite_not_exist') if self.translator else 'state.vscdb does not exist. Skipping update.'}{Style.RESET_ALL}")
                 return True # Not an error if it doesn't exist, nothing to update
        except Exception as backup_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.backup_failed_file', file='state.vscdb', error=str(backup_err)) if self.translator else f'Could not create backup for state.vscdb: {backup_err}'}{Style.RESET_ALL}")
            return False

        conn = None
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(self.state_db_path), exist_ok=True)
            conn = sqlite3.connect(self.state_db_path, timeout=10) # Add timeout
            cursor = conn.cursor()

            # Ensure the table exists (VSCode state DB schema)
            # Use IF NOT EXISTS for safety
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY NOT NULL,
                    value BLOB
                )
            """)
            conn.commit() # Commit table creation if it happened

            # Prepare updates - Filter which keys go into the DB
            # Usually, telemetry and storage keys are mirrored. Check actual DB if needed.
            updates = []
            keys_to_update_in_db = [k for k in new_ids if k.startswith("telemetry.") or k.startswith("storage.")]
            if not keys_to_update_in_db:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqlite_no_keys') if self.translator else 'No relevant keys identified to update in SQLite DB.'}{Style.RESET_ALL}")
                 conn.close()
                 return True

            print(f"{Fore.CYAN}Updating SQLite key-value pairs:{Style.RESET_ALL}")
            # Use INSERT OR REPLACE (UPSERT) in a transaction
            cursor.execute("BEGIN TRANSACTION")
            for key in keys_to_update_in_db:
                value = new_ids[key]
                value_blob = str(value).encode('utf-8') # Store as UTF-8 bytes
                print(f"  {EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value)
                    VALUES (?, ?)
                """, (key, value_blob))

            conn.commit() # Commit the transaction
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_success') if self.translator else 'SQLite database updated successfully.'}{Style.RESET_ALL}")
            return True

        except sqlite3.Error as db_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_error', error=str(db_err)) if self.translator else f'SQLite database error: {str(db_err)}'}{Style.RESET_ALL}")
            # Attempt restore from backup
            if os.path.exists(backup_path):
                 try:
                     print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.restoring_backup', path=backup_path) if translator else f'Attempting to restore backup: {backup_path}'}{Style.RESET_ALL}")
                     shutil.move(backup_path, self.state_db_path) # Restore backup
                     print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.restore_success') if translator else 'Backup restored.'}{Style.RESET_ALL}")
                 except Exception as restore_err:
                     print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.restore_failed', error=str(restore_err))}{Style.RESET_ALL}")
                     print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.manual_restore_needed', original=self.state_db_path, backup=backup_path)}{Style.RESET_ALL}")
            return False
        finally:
            if conn:
                conn.close()


    def update_machine_id_file(self, new_machine_id: str) -> bool:
        """Update the separate machineId file (e.g., ~/.config/cursor/machineid)."""
        if not self.machine_id_file_path:
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.machineid_path_unknown') if self.translator else 'MachineId file path is unknown, skipping update.'}{Style.RESET_ALL}")
             return True # Non-critical, return True

        print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.updating_machineid_file') if self.translator else f'Updating machineId file: {self.machine_id_file_path}'}{Style.RESET_ALL}")

        # --- Ensure directory exists ---
        machine_id_dir = os.path.dirname(self.machine_id_file_path)
        try:
             os.makedirs(machine_id_dir, exist_ok=True)
        except OSError as mkdir_err:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.mkdir_failed', path=machine_id_dir, error=str(mkdir_err)) if self.translator else f'Failed to create directory {machine_id_dir}: {mkdir_err}'}{Style.RESET_ALL}")
             return False # Cannot write if dir creation fails

        # --- Backup existing file ---
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.machine_id_file_path}.{timestamp}.bak"
        if os.path.exists(self.machine_id_file_path):
             try:
                 shutil.copy2(self.machine_id_file_path, backup_path)
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
             except Exception as backup_err:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.backup_failed_file', file='machineId', error=str(backup_err)) if self.translator else f'Could not create backup for machineId file: {backup_err}'}{Style.RESET_ALL}")
                 # Continue? Or fail? Let's continue but warn, as this file isn't always essential.

        # --- Write new ID using temp file ---
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=machine_id_dir, prefix="machineId.") as tmp_file:
                tmp_file.write(new_machine_id)
                tmp_path = tmp_file.name

            shutil.move(tmp_path, self.machine_id_file_path)
            tmp_path = None # Indicate move success
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.machineid_update_success') if self.translator else 'machineId file updated successfully.'}{Style.RESET_ALL}")
            return True
        except Exception as write_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.write_file_error', file='machineId', error=str(write_err)) if self.translator else f'Error writing machineId file: {write_err}'}{Style.RESET_ALL}")
            # Attempt restore if backup exists
            if os.path.exists(backup_path):
                try:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.restoring_backup', path=backup_path)}{Style.RESET_ALL}")
                    shutil.move(backup_path, self.machine_id_file_path)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.restore_success')}{Style.RESET_ALL}")
                except Exception as restore_err:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.restore_failed', error=str(restore_err))}{Style.RESET_ALL}")
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.manual_restore_needed', original=self.machine_id_file_path, backup=backup_path)}{Style.RESET_ALL}")
            return False # Failed to write
        finally:
             if tmp_path and os.path.exists(tmp_path):
                  try: os.unlink(tmp_path)
                  except OSError: pass


    # --- System ID Modification (Use with extreme caution!) ---

    def _update_windows_machine_guid(self, new_guid: str) -> bool:
        """Update Windows MachineGuid in Cryptography registry."""
        # --- Implementation unchanged, assumed correct ---
        try:
            import winreg
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_win_guid') if self.translator else 'Updating Windows MachineGuid (Cryptography)...'}{Style.RESET_ALL}")
            key_path = r"SOFTWARE\Microsoft\Cryptography"
            try:
                # Ensure access rights request includes KEY_WOW64_64KEY for 64-bit systems
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY)
                winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
                winreg.CloseKey(key)
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.win_guid_updated') if self.translator else 'Windows MachineGuid updated.'}{Style.RESET_ALL}")
                return True
            except FileNotFoundError:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.reg_key_not_found', key=key_path) if self.translator else f'Registry key not found: {key_path}'}{Style.RESET_ALL}")
                 return True # Not an error if key doesn't exist, can't update it.
            except PermissionError:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied_reg', key=key_path) if self.translator else f'Permission denied for registry key: {key_path}'}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.run_as_admin') if self.translator else 'Run the script as Administrator.'}{Style.RESET_ALL}")
                return False
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_win_guid_failed', error=str(e))}{Style.RESET_ALL}")
                return False
        except ImportError:
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.winreg_missing_skip') if self.translator else 'winreg module not found (not on Windows?). Skipping Windows GUID update.'}{Style.RESET_ALL}")
             return True # Non-Windows, not an error
        except Exception as e: # Catch potential ctypes errors if used for admin check
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_win_guid_failed', error=str(e))}{Style.RESET_ALL}")
             return False


    def _update_windows_sqm_machine_id(self, new_guid_braces: str) -> bool:
        """Update Windows MachineId in SQMClient registry."""
        # --- Implementation unchanged, assumed correct ---
        try:
            import winreg
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_win_sqmid') if self.translator else 'Updating Windows MachineId (SQMClient)...'}{Style.RESET_ALL}")
            key_path = r"SOFTWARE\Microsoft\SQMClient"
            parent_path = r"SOFTWARE\Microsoft"
            key = None
            parent_key = None
            try:
                # Try opening existing key first
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                # If key doesn't exist, try to create it
                try:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqm_key_creating', key=key_path) if self.translator else f'SQMClient key not found, attempting to create: {key_path}'}{Style.RESET_ALL}")
                    # Need to open parent key writeable to create subkey
                    parent_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, parent_path, 0, winreg.KEY_CREATE_SUB_KEY | winreg.KEY_WOW64_64KEY)
                    key = winreg.CreateKey(parent_key, "SQMClient")
                except PermissionError:
                     print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied_reg_create', key=key_path) if self.translator else f'Permission denied to create registry key: {key_path}'}{Style.RESET_ALL}")
                     print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.run_as_admin') if self.translator else 'Run the script as Administrator.'}{Style.RESET_ALL}")
                     return False
                except Exception as create_err:
                     print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.reg_create_failed', key=key_path, error=str(create_err)) if self.translator else f'Failed to create registry key {key_path}: {create_err}'}{Style.RESET_ALL}")
                     return False
                finally:
                     if parent_key: winreg.CloseKey(parent_key)

            # If we have a key (opened or created), set the value
            if key:
                try:
                    winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, new_guid_braces)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.win_sqmid_updated') if self.translator else 'Windows SQM MachineId updated.'}{Style.RESET_ALL}")
                    return True
                except PermissionError: # Should have been caught earlier, but double check
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied_reg_write', key=key_path) if self.translator else f'Permission denied writing to registry key: {key_path}'}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.run_as_admin') if self.translator else 'Run the script as Administrator.'}{Style.RESET_ALL}")
                    return False
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_win_sqmid_failed', error=str(e))}{Style.RESET_ALL}")
                    return False
                finally:
                     winreg.CloseKey(key)
            else:
                 # This case means creation failed above and error was already printed
                 return False # Key could not be opened or created
        except ImportError:
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.winreg_missing_skip') if self.translator else 'winreg module not found (not on Windows?). Skipping Windows SQM ID update.'}{Style.RESET_ALL}")
             return True # Non-Windows, not an error
        except Exception as e: # Catch potential ctypes errors if used for admin check
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_win_sqmid_failed', error=str(e))}{Style.RESET_ALL}")
             return False

    def _update_macos_platform_uuid(self, new_uuid: str) -> bool:
        """Update macOS Platform UUID using plutil (requires sudo)."""
        # --- Implementation unchanged, but added more checks ---
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.macos_uuid_warn1') if self.translator else 'Attempting to update macOS Platform UUID is advanced and potentially risky.'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.macos_uuid_warn2') if self.translator else 'This step requires sudo privileges.'}{Style.RESET_ALL}")

        # Check if running as root first
        try:
            if os.geteuid() != 0:
                 print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.macos_sudo_required') if self.translator else 'Updating macOS Platform UUID requires running the script with sudo.'}{Style.RESET_ALL}")
                 return False
        except AttributeError:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.geteuid_unavailable') if self.translator else 'Cannot check user ID (not on POSIX?). Assuming sudo is not required or handled externally.'}{Style.RESET_ALL}")
            # Continue cautiously on non-POSIX if this function is somehow reached

        uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist" # Path requires root access
        # Key might be IOPlatformUUID or platform-uuid depending on macOS version
        # Check common keys
        uuid_key_to_try = "IOPlatformUUID"

        if not os.path.exists(uuid_file):
             # Check alternative common location just in case
             alt_uuid_file = "/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
             if os.path.exists(alt_uuid_file):
                  uuid_file = alt_uuid_file
             else:
                  print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.macos_plist_not_found', path=uuid_file) if self.translator else f'Platform UUID plist not found at standard locations. Skipping update.'}{Style.RESET_ALL}")
                  return True # Not an error if the target doesn't exist

        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_macos_uuid', file=uuid_file) if self.translator else f'Updating macOS Platform UUID using plutil on {uuid_file}...'}{Style.RESET_ALL}")
        backup_path = None # Initialize backup path
        try:
            # Backup the plist first
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{uuid_file}.{timestamp}.bak"
            try:
                 # Need sudo to copy from /var/root or /Library
                 copy_cmd = ['sudo', 'cp', uuid_file, backup_path]
                 print(f"{Fore.CYAN}$ {' '.join(copy_cmd)}{Style.RESET_ALL}")
                 subprocess.run(copy_cmd, check=True, capture_output=True)
                 # Ensure backup is owned by root too if needed, copy2 might not work well with sudo cp
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")
            except subprocess.CalledProcessError as backup_err:
                 print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.backup_failed_sudo', file='Platform UUID plist', error=str(backup_err.stderr.decode()))}{Style.RESET_ALL}")
                 return False # Cannot proceed safely without backup
            except Exception as backup_err:
                 print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.backup_failed_file', file='Platform UUID plist', error=str(backup_err))}{Style.RESET_ALL}")
                 return False

            # Use plutil command to replace the UUID string
            formatted_uuid = new_uuid.upper()
            # Try common keys
            keys_to_try = ["IOPlatformUUID", "platform-uuid", "UUID"]
            update_success = False
            for key in keys_to_try:
                cmd = ['sudo', 'plutil', '-replace', key, '-string', formatted_uuid, uuid_file]
                print(f"{Fore.CYAN}Attempting update with key '{key}': $ {' '.join(cmd)}{Style.RESET_ALL}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=False) # Don't check=True here, handle error below

                if result.returncode == 0:
                    # Check if the command actually did something (plutil might return 0 even if key not found)
                    # We might need to read the file back, but that's complex. Assume success if return code is 0 for now.
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_uuid_updated_key', key=key) if self.translator else f'macOS Platform UUID updated successfully (using key: {key}).'}{Style.RESET_ALL}")
                    update_success = True
                    break # Stop after first successful key update
                # else: # Log failure for this key attempt? Optional.
                #     print(f"{Fore.YELLOW}  - Failed or key '{key}' not found (rc={result.returncode}): {result.stderr.strip()}{Style.RESET_ALL}")

            if not update_success:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.macos_plutil_failed_allkeys') if self.translator else 'Failed to execute plutil command successfully for all tried keys.'}{Style.RESET_ALL}")
                # Attempt restore on failure
                if os.path.exists(backup_path):
                     try:
                         restore_cmd = ['sudo', 'mv', backup_path, uuid_file]
                         print(f"{Fore.CYAN}$ {' '.join(restore_cmd)}{Style.RESET_ALL}")
                         subprocess.run(restore_cmd, check=True, capture_output=True)
                         print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.restore_success') if self.translator else 'Backup restored.'}{Style.RESET_ALL}")
                     except Exception as restore_err:
                         print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.restore_failed_sudo', error=str(restore_err)) if self.translator else f'Failed to restore backup (needs sudo): {restore_err}'}{Style.RESET_ALL}")
                return False # Overall update failed
            else:
                return True # Update succeeded with one of the keys

        except FileNotFoundError: # If sudo or plutil is not found
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.command_not_found', cmd='sudo/plutil') if self.translator else 'Error: sudo or plutil command not found.'}{Style.RESET_ALL}")
             return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_uuid_failed', error=str(e))}{Style.RESET_ALL}")
            # print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}") # Optional debug
            # Attempt restore if backup path was determined
            if backup_path and os.path.exists(backup_path):
                  try:
                       restore_cmd = ['sudo', 'mv', backup_path, uuid_file]
                       subprocess.run(restore_cmd, check=True, capture_output=True)
                       print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.restore_success')}{Style.RESET_ALL}")
                  except Exception as restore_err:
                       print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.restore_failed_sudo', error=str(restore_err))}{Style.RESET_ALL}")
            return False


    def update_system_ids(self, new_ids: dict) -> bool:
        """Update system-level IDs (Windows Registry, macOS Plist). Requires Admin/sudo."""
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids') if self.translator else 'Updating System-Level IDs (Requires Admin/sudo)...'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.system_id_warning') if self.translator else 'Warning: Modifying system identifiers can have unintended consequences. Proceed with caution.'}{Style.RESET_ALL}")

        success_flags = []
        system = platform.system()

        if system == "Windows":
             # Generate GUIDs in the correct formats from the new_ids dict
             # Use devDeviceId for Cryptography\MachineGuid (seems common)
             guid_no_braces = new_ids.get("telemetry.devDeviceId", str(uuid.uuid4()))
             # Use sqmId (which includes braces) for SQMClient\MachineId
             guid_with_braces = new_ids.get("telemetry.sqmId", "{" + str(uuid.uuid4()).upper() + "}")

             print(f"{Fore.CYAN}  {EMOJI['INFO']} Target MachineGuid: {guid_no_braces}{Style.RESET_ALL}")
             print(f"{Fore.CYAN}  {EMOJI['INFO']} Target SQM MachineId: {guid_with_braces}{Style.RESET_ALL}")

             success_flags.append(self._update_windows_machine_guid(guid_no_braces))
             success_flags.append(self._update_windows_sqm_machine_id(guid_with_braces))

        elif system == "Darwin": # macOS
            # Use the macMachineId (which we generated as UUID) for IOPlatformUUID
            platform_uuid = new_ids.get("telemetry.macMachineId", str(uuid.uuid4()).upper())
            print(f"{Fore.CYAN}  {EMOJI['INFO']} Target Platform UUID: {platform_uuid}{Style.RESET_ALL}")
            success_flags.append(self._update_macos_platform_uuid(platform_uuid))

        elif system == "Linux":
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.linux_system_id_skip') if self.translator else 'System ID modification is typically not required or easily standardized on Linux. Skipping.'}{Style.RESET_ALL}")
            success_flags.append(True) # Indicate success for this step on Linux

        else:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.unsupported_os_system_id') if self.translator else 'System ID modification not implemented for this OS.'}{Style.RESET_ALL}")
            success_flags.append(True) # Treat unsupported as success (no action needed)

        # Check if all steps attempted were successful
        overall_success = all(success_flags)

        if overall_success:
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.system_ids_updated') if self.translator else 'System ID update process finished successfully.'}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed') if self.translator else 'One or more system ID updates failed. Check logs above.'}{Style.RESET_ALL}")

        return overall_success


    # --- Main Reset Orchestration ---

    def reset_machine_ids(self, skip_system_ids=False, skip_js_patches=False):
        """Orchestrate the full machine ID reset process."""
        print(f"\n{Fore.CYAN}{'='*18} Starting Cursor Reset {'='*18}{Style.RESET_ALL}")

        # 1. Check Prerequisites (Paths, Permissions for ID reset part)
        if not self._check_prerequisites():
            # Error message already printed inside _check_prerequisites
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.prereq_failed_stop') if self.translator else 'Prerequisites check failed. Cannot proceed with reset.'}{Style.RESET_ALL}")
            return False

        # --- ID Reset Steps ---
        # 2. Generate New IDs (includes updating separate machineId file)
        new_ids = self.generate_new_ids()
        if not new_ids: # Should not happen unless generation itself fails badly
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.id_generation_failed') if self.translator else 'Failed to generate new IDs.'}{Style.RESET_ALL}")
             return False

        # 3. Update Configuration Files (JSON & SQLite)
        json_success = self.update_storage_json(new_ids)
        sqlite_success = self.update_sqlite_db(new_ids)

        # Consider config file updates critical
        if not json_success or not sqlite_success:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.config_update_failed_stop') if self.translator else 'Failed to update core configuration files (storage.json / state.vscdb). Reset aborted.'}{Style.RESET_ALL}")
             return False # Stop if core config update fails

        # 4. Update System-Level IDs (Optional)
        system_id_success = True # Assume success if skipped
        if not skip_system_ids:
            system_id_success = self.update_system_ids(new_ids)
            if not system_id_success:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.system_id_update_failed_warn') if self.translator else 'Warning: Failed to update one or more system-level IDs.'}{Style.RESET_ALL}")
                 # Continue the reset process even if system IDs fail? Yes, it's optional.
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.system_id_skipped') if self.translator else 'Skipping system-level ID update as requested.'}{Style.RESET_ALL}")


        # --- JS Patching Steps (Optional) ---
        patch_success = True # Assume success if skipped or not possible
        if not skip_js_patches:
            if self.app_resource_dir:
                print(f"\n{Fore.CYAN}{'='*18} Applying JS Patches {'='*18}{Style.RESET_ALL}")

                # Check permissions for JS files within app_resource_dir
                pkg_path, main_path = get_cursor_paths(self.app_resource_dir, self.translator)
                workbench_path = get_workbench_cursor_path(self.app_resource_dir, self.translator)
                js_paths_to_check = [p for p in [pkg_path, main_path, workbench_path] if p]
                js_permission_ok = True
                for js_path in js_paths_to_check:
                    if not os.access(js_path, os.W_OK):
                        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission_js', path=js_path) if translator else f'No write permission for JS file: {js_path}'}{Style.RESET_ALL}")
                        js_permission_ok = False
                if not js_permission_ok:
                    print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.try_sudo_js') if self.translator else 'JS patching requires write permissions. Try running with sudo/Administrator or use --skip-js-patches.'}{Style.RESET_ALL}")
                    patch_success = False # Mark patching as failed due to permissions
                else:
                    # Permissions OK, proceed with patching logic
                    version_status = None
                    if pkg_path:
                         version_status = check_cursor_version(pkg_path, self.translator)

                    # Patch main.js only if version is suitable
                    mainjs_patch_success = True # Assume success if skipped
                    if version_status is True: # Version >= 0.45.0
                         print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.version_ok_patching') if self.translator else 'Version >= 0.45.0, attempting main.js patch...'}{Style.RESET_ALL}")
                         if not patch_cursor_get_machine_id(self.app_resource_dir, self.translator):
                             mainjs_patch_success = False # Error logged within function
                    elif version_status is False: # Version < 0.45.0
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.version_low_skip_patch') if self.translator else 'Version < 0.45.0, skipping main.js patch.'}{Style.RESET_ALL}")
                    else: # Error checking version
                        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.version_check_failed_skip_patch') if self.translator else 'Could not determine version, skipping main.js patch.'}{Style.RESET_ALL}")

                    # Patch workbench.js (UI elements) - less version dependent, try anyway
                    workbench_patch_success = True # Assume success if path missing
                    if workbench_path:
                        if not modify_workbench_js(workbench_path, self.translator):
                            workbench_patch_success = False # Error logged within function
                    # else: # find_cursor_app_resource_dir already logged warning if workbench_path is None

                    patch_success = mainjs_patch_success and workbench_patch_success

            else: # No app_resource_dir found
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.app_dir_not_found_skip_patches') if self.translator else 'App resource directory not found, skipping all JS patching.'}{Style.RESET_ALL}")
                patch_success = True # Not an error if patching wasn't possible
        else: # skip_js_patches is True
             print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.js_patch_skipped') if self.translator else 'Skipping JS patching as requested.'}{Style.RESET_ALL}")
             patch_success = True # Not an error if skipped


        # --- Final Summary ---
        print(f"\n{Fore.CYAN}{'='*20} Reset Summary {'='*21}{Style.RESET_ALL}")
        # Core reset (JSON/SQLite) must succeed. System ID and Patches are optional success criteria.
        overall_success = json_success and sqlite_success and system_id_success and patch_success

        if overall_success:
             print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success_complete') if self.translator else 'Cursor reset process completed successfully!'}{Style.RESET_ALL}")
             print(f"\n{Fore.CYAN}{self.translator.get('reset.new_id_summary')}:{Style.RESET_ALL}")
             # Print key IDs generated
             print(f"  {EMOJI['INFO']} telemetry.devDeviceId: {Fore.GREEN}{new_ids.get('telemetry.devDeviceId')}{Style.RESET_ALL}")
             print(f"  {EMOJI['INFO']} telemetry.machineId: {Fore.GREEN}{new_ids.get('telemetry.machineId')}{Style.RESET_ALL}")
             print(f"  {EMOJI['INFO']} storage.serviceMachineId: {Fore.GREEN}{new_ids.get('storage.serviceMachineId')}{Style.RESET_ALL}")
             return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.success_partial') if self.translator else 'Cursor reset process finished with warnings or errors.'}{Style.RESET_ALL}")
            # Only list failures
            if not json_success: print(f"  {EMOJI['ERROR']} {self.translator.get('reset.summary_fail_json') if self.translator else 'Failed updating storage.json'}")
            if not sqlite_success: print(f"  {EMOJI['ERROR']} {self.translator.get('reset.summary_fail_sqlite') if self.translator else 'Failed updating state.vscdb'}")
            if not system_id_success and not skip_system_ids: print(f"  {EMOJI['WARNING']} {self.translator.get('reset.summary_fail_system_id') if self.translator else 'Failed updating system IDs (optional)'}")
            if not patch_success and not skip_js_patches: print(f"  {EMOJI['WARNING']} {self.translator.get('reset.summary_fail_patch') if self.translator else 'Failed applying JS patches (optional)'}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.check_logs_above') if self.translator else 'Please check the logs above for details.'}{Style.RESET_ALL}")
            # Return True even if optional steps failed, as core reset succeeded.
            # Return False only if core reset (JSON/SQLite) failed.
            return json_success and sqlite_success


# --- Main Execution ---

def run(translator=None, skip_system=False, skip_patches=False):
    # --- Translator Setup ---
    if translator is None:
        # Basic fallback translator if none provided
        class FallbackTranslator:
            def get(self, key, **kwargs):
                # Simple key-to-text conversion
                text = key.replace('reset.', '').replace('find_path.', '').replace('_', ' ').capitalize()
                if kwargs:
                    try:
                        text = text.format(**kwargs) # Basic formatting
                    except KeyError:
                        # Fallback if format keys don't match kwargs
                        text += f" ({', '.join(f'{k}={v}' for k,v in kwargs.items())})"
                return text
        translator = FallbackTranslator()
        print(f"{Fore.YELLOW}Using basic fallback translator.{Style.RESET_ALL}")

    # --- Title ---
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title', default='Cursor Machine ID Reset Tool')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    # --- Run Reset ---
    overall_status = False
    try:
        resetter = MachineIDResetter(translator)
        # Proceed only if paths necessary for reset were found
        if resetter.storage_json_path and resetter.state_db_path and resetter.machine_id_file_path:
            overall_status = resetter.reset_machine_ids(skip_system_ids=skip_system, skip_js_patches=skip_patches)
        else:
             print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.abort_missing_paths') if translator else 'Aborting reset due to missing essential configuration paths.'}{Style.RESET_ALL}")
             overall_status = False

    except Exception as e:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.process_error_unexpected', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        overall_status = False

    # --- Final Message ---
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    if overall_status:
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.final_message_success') if translator else 'Operation finished successfully.'}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.final_message_error') if translator else 'Operation finished with errors or warnings.'}{Style.RESET_ALL}")

    # Keep console open until user presses Enter
    try:
         input(f"\n{EMOJI['INFO']} {translator.get('reset.press_enter') if translator else 'Press Enter to exit...'}")
    except EOFError:
         pass # Handle case where input is piped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset Cursor Machine ID and related identifiers.")
    parser.add_argument(
        "--skip-system-ids",
        action="store_true",
        help="Skip modifying system-level identifiers (Windows Registry/macOS Plist)."
    )
    parser.add_argument(
        "--skip-js-patches",
        action="store_true",
        help="Skip patching Cursor's JavaScript files (main.js, workbench.js)."
    )
    args = parser.parse_args()

    # --- !!! Translator Import Placeholder !!! ---
    # If you have a central translator, import it here:
    # try:
    #     from main import translator as main_translator
    # except ImportError:
    #     main_translator = None
    #     print("Could not import main translator, using fallback.")
    main_translator = None # <<< Replace this with your actual translator object if available
    # --- !!! ---

    # --- Privilege Check (only if modifying system IDs) ---
    needs_elevation = False
    if not args.skip_system_ids:
        system = platform.system()
        if system == "Windows":
             try:
                 import ctypes
                 needs_elevation = not ctypes.windll.shell32.IsUserAnAdmin()
             except Exception as admin_check_err:
                  print(f"{Fore.YELLOW}Warning: Could not check for Administrator privileges ({admin_check_err}). Assuming elevation might be needed.{Style.RESET_ALL}")
                  needs_elevation = True # Assume needed if check fails
        elif system == "Darwin":
             try:
                needs_elevation = os.geteuid() != 0
             except AttributeError:
                 print(f"{Fore.YELLOW}Warning: Cannot check user ID (geteuid not available). Assuming elevation may be needed for system ID changes.{Style.RESET_ALL}")
                 needs_elevation = True # Assume needed if check fails
        # No elevation check needed for Linux system ID part as we skip it

        if needs_elevation:
             print(f"\n{Fore.RED}{EMOJI['LOCK']} {main_translator.get('reset.elevation_required_warn') if main_translator else 'WARNING: Modifying system IDs requires Administrator/root privileges.'}{Style.RESET_ALL}")
             print(f"{Fore.YELLOW}{main_translator.get('reset.rerun_elevated') if main_translator else 'Please re-run this script using "Run as Administrator" (Windows) or `sudo python totally_reset_cursor.py` (macOS).'}{Style.RESET_ALL}")
             print(f"{Fore.YELLOW}{main_translator.get('reset.use_skip_option') if main_translator else 'Alternatively, use the --skip-system-ids flag to proceed without modifying system identifiers.'}{Style.RESET_ALL}")
             sys.exit(1) # Exit if elevation is required but not present


    # --- Execute Main Logic ---
    run(translator=main_translator, skip_system=args.skip_system_ids, skip_patches=args.skip_js_patches)
