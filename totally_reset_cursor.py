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
        # Add other potential Windows locations if necessary
    elif system == "Darwin": # macOS
        potential_paths.append(os.path.join(home_dir, "Library/Application Support/Cursor"))
    elif system == "Linux":
        # Snap: Check common snap location pattern (might be sandboxed)
        snap_path = os.path.join(home_dir, "snap/cursor/current/.config/cursor")
        if os.path.exists(snap_path):
             potential_paths.append(snap_path)
        # Standard XDG config location
        potential_paths.append(os.path.join(home_dir, ".config/cursor"))
        # Older/non-standard locations
        potential_paths.append(os.path.join(home_dir, ".cursor"))


    for path in potential_paths:
        normalized_path = os.path.abspath(path)
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('find_path.checking', path=normalized_path) if translator else f'Checking: {normalized_path}'}{Style.RESET_ALL}")
        # Check for a key file/directory presence
        if os.path.isdir(normalized_path) and os.path.exists(os.path.join(normalized_path, "User")):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('find_path.found_config_at', path=normalized_path) if translator else f'Found valid config directory at: {normalized_path}'}{Style.RESET_ALL}")
            return normalized_path

    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.config_not_found') if translator else 'Cursor configuration directory not found.'}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('find_path.checked_paths', paths=', '.join(potential_paths)) if translator else f'Checked paths: {", ".join(potential_paths)}'}{Style.RESET_ALL}")
    return None

def find_cursor_app_resource_dir(translator=None) -> Optional[str]:
    """Finds the Cursor application 'resources/app' directory."""
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
        # Add scoop, winget locations if needed

    elif system == "Darwin": # macOS
        potential_paths.append("/Applications/Cursor.app/Contents/Resources/app")
        potential_paths.append(os.path.join(home_dir, "Applications/Cursor.app/Contents/Resources/app"))

    elif system == "Linux":
        # Standard package manager locations
        potential_paths.extend([
            "/opt/Cursor/resources/app",
            "/usr/share/cursor/resources/app",
            "/usr/local/share/cursor/resources/app",
        ])
        # User-local installation
        potential_paths.append(os.path.join(home_dir, ".local/share/cursor/resources/app"))

        # AppImage extractions (common patterns)
        # Look in home directory
        potential_paths.extend(glob.glob(os.path.join(home_dir, "squashfs-root*/resources/app")))
        potential_paths.extend(glob.glob(os.path.join(home_dir, "squashfs-root*/usr/share/cursor/resources/app")))
        potential_paths.extend(glob.glob(os.path.join(home_dir, ".mount_Cursor*/resources/app"))) # Some AppImage mount points
        # Look in /tmp
        potential_paths.extend(glob.glob("/tmp/squashfs-root*/resources/app"))
        potential_paths.extend(glob.glob("/tmp/.mount_Cursor*/resources/app"))
        # Look relative to current dir (if script is run from near extraction)
        potential_paths.extend(glob.glob("squashfs-root*/resources/app"))
        potential_paths.extend(glob.glob("squashfs-root*/usr/share/cursor/resources/app"))
        # Flatpak (might be sandboxed)
        potential_paths.append("/var/lib/flatpak/app/com.cursor.Cursor/current/active/files/share/cursor/resources/app")


    # Filter out duplicates and non-directories before checking contents
    checked_paths = set()
    valid_path = None
    for path in potential_paths:
        normalized_path = os.path.abspath(path)
        if normalized_path in checked_paths or not os.path.isdir(normalized_path):
            continue
        checked_paths.add(normalized_path)

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('find_path.checking', path=normalized_path) if translator else f'Checking: {normalized_path}'}{Style.RESET_ALL}")
        # Check for essential files within the 'app' directory
        package_json_path = os.path.join(normalized_path, "package.json")
        main_js_path = os.path.join(normalized_path, "out/main.js")
        if os.path.exists(package_json_path) and os.path.exists(main_js_path):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('find_path.found_app_at', path=normalized_path) if translator else f'Found valid app resource directory at: {normalized_path}'}{Style.RESET_ALL}")
            valid_path = normalized_path
            break # Found a valid path, stop searching

    if not valid_path:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.app_not_found') if translator else 'Cursor application resource directory not found.'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('find_path.checked_paths_app', paths=', '.join(sorted(list(checked_paths)))) if translator else f'Checked paths: {", ".join(sorted(list(checked_paths)))}'}{Style.RESET_ALL}")

    return valid_path


# --- Helper Functions (Modified) ---

def get_cursor_paths(app_resource_dir: str, translator=None) -> Tuple[Optional[str], Optional[str]]:
    """ Get package.json and main.js paths from the app resource dir"""
    pkg_path = os.path.join(app_resource_dir, "package.json")
    main_path = os.path.join(app_resource_dir, "out/main.js")

    if not os.path.exists(pkg_path):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path) if translator else f'Essential file not found: {pkg_path}'}{Style.RESET_ALL}")
        return None, None
    if not os.path.exists(main_path):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.main_not_found', path=main_path) if translator else f'Essential file not found: {main_path}'}{Style.RESET_ALL}")
        return None, None

    return pkg_path, main_path

def get_workbench_cursor_path(app_resource_dir: str, translator=None) -> Optional[str]:
    """Get Cursor workbench.desktop.main.js path from the app resource dir"""
    main_path = os.path.join(app_resource_dir, "out/vs/workbench/workbench.desktop.main.js")

    if not os.path.exists(main_path):
        # Log the specific error leading to this message
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.workbench_js_not_found', path=main_path) if translator else f'Workbench JS file not found: {main_path}'}{Style.RESET_ALL}")
        # This error is triggered because the find_cursor_app_resource_dir function failed
        # Reiterate the core problem message
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.app_not_found_critical') if translator else 'Critical Error: Cursor application resource directory could not be located. Cannot proceed with patching.'}{Style.RESET_ALL}")

        # Print the detailed traceback for debugging
        # print(f"{Fore.YELLOW}Traceback:\n{traceback.format_exc()}{Style.RESET_ALL}") # Optional: uncomment for deep debug

        return None # Indicate failure clearly

    return main_path


def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """Version number check"""
    version_pattern = r"^\d+\.\d+\.\d+" # Allow suffixes like -nightly
    try:
        match = re.match(version_pattern, version)
        if not match:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False

        clean_version = match.group(0) # Use only the numeric part for comparison

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(clean_version)

        if min_version:
            min_v = parse_version(min_version)
            if current < min_v:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.version_too_low', version=version, min_version=min_version)}{Style.RESET_ALL}")
                return False # Treat as failure for logic requiring min version

        if max_version:
             max_v = parse_version(max_version)
             if current > max_v:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.version_too_high', version=version, max_version=max_version)}{Style.RESET_ALL}")
                # Decide if this is a failure or just a warning
                # return False

        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_error', error=str(e))}{Style.RESET_ALL}")
        return False

def check_cursor_version(pkg_path: str, translator) -> Optional[bool]:
    """Check Cursor version from package.json. Returns True if >= 0.45.0, False if lower, None on error."""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.reading_package_json', path=pkg_path)}{Style.RESET_ALL}")

        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except UnicodeDecodeError:
            with open(pkg_path, "r", encoding="latin-1") as f: # Fallback encoding
                data = json.load(f)

        if not isinstance(data, dict):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
            return None

        version = data.get("version")
        if not version or not isinstance(version, str):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_version_field')}{Style.RESET_ALL}")
            return None

        version = version.strip()
        if not version:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_field_empty')}{Style.RESET_ALL}")
            return None

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.found_version', version=version)}{Style.RESET_ALL}")

        # Use version_check for comparison
        min_version_str = "0.45.0"
        is_min_met = version_check(version, min_version=min_version_str, translator=translator)

        if is_min_met:
             print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.version_check_passed_min', version=version, min_version=min_version_str)}{Style.RESET_ALL}")
             return True
        else:
             # Version check already printed the warning if too low or format error
             return False # Explicitly return False if below min_version

    except FileNotFoundError:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path)}{Style.RESET_ALL}")
        return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.check_version_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
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

    try:
        # Save original file permissions
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # Read original content
        print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('reset.reading_file', file=os.path.basename(file_path)) if translator else f'Reading {os.path.basename(file_path)}...'}{Style.RESET_ALL}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()
        except Exception as read_err:
             print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_file_error', file=file_path, error=str(read_err)) if translator else f'Error reading file {file_path}: {read_err}'}{Style.RESET_ALL}")
             return False


        # --- Backup ---
        backup_path = file_path + ".bak" # Consistent backup extension
        try:
            if not os.path.exists(backup_path):
                 shutil.copy2(file_path, backup_path) # copy2 preserves metadata
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('reset.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            else:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.backup_exists_file', path=backup_path) if translator else f'Backup already exists: {backup_path}'}{Style.RESET_ALL}")
        except Exception as backup_err:
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.backup_failed_file', file=file_path, error=str(backup_err)) if translator else f'Could not create backup for {file_path}: {backup_err}'}{Style.RESET_ALL}")
             # Decide if you want to proceed without backup? Risky. Let's return False.
             return False


        # --- Modify Content ---
        modified_content = content
        found_any = False
        print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.applying_patches', file=os.path.basename(file_path)) if translator else f'Applying patches to {os.path.basename(file_path)}...'}{Style.RESET_ALL}")
        for i, (old_pattern, new_pattern) in enumerate(replacements):
            if is_js: # Use regex for JS
                if re.search(old_pattern, modified_content):
                    modified_content = re.sub(old_pattern, new_pattern, modified_content)
                    print(f"{Fore.GREEN}   {EMOJI['SUCCESS']} {translator.get('reset.patch_applied', index=i+1) if translator else f'Applied patch #{i+1}'}{Style.RESET_ALL}")
                    found_any = True
                else:
                    print(f"{Fore.YELLOW}   {EMOJI['INFO']} {translator.get('reset.patch_not_found', index=i+1) if translator else f'Patch #{i+1} pattern not found.'}{Style.RESET_ALL}")
            else: # Use simple string replacement
                if old_pattern in modified_content:
                    modified_content = modified_content.replace(old_pattern, new_pattern)
                    print(f"{Fore.GREEN}   {EMOJI['SUCCESS']} {translator.get('reset.replacement_applied', index=i+1) if translator else f'Applied replacement #{i+1}'}{Style.RESET_ALL}")
                    found_any = True
                else:
                    print(f"{Fore.YELLOW}   {EMOJI['INFO']} {translator.get('reset.replacement_not_found', index=i+1) if translator else f'Replacement #{i+1} pattern not found.'}{Style.RESET_ALL}")

        if not found_any:
             print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.no_patterns_found', file=os.path.basename(file_path)) if translator else f'No patterns found or replaced in {os.path.basename(file_path)}. File may already be patched or structure changed.'}{Style.RESET_ALL}")
             # Optionally return True here if no patching needed is not an error
             # return True # If you want to continue even if nothing was patched

        if modified_content == content and found_any:
             # This case should ideally not happen if found_any is True, but check anyway
              print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.content_unchanged', file=os.path.basename(file_path)) if translator else f'Content unchanged despite finding patterns in {os.path.basename(file_path)}. Check patterns.'}{Style.RESET_ALL}")
              # return False # Treat as failure? Or maybe just warn?

        # --- Write Modified Content ---
        # Use tempfile to avoid corrupting original on write error
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False, dir=os.path.dirname(file_path)) as tmp_file:
                tmp_file.write(modified_content)
                tmp_path = tmp_file.name # Get the temporary file path

            # Replace original with temp file
            shutil.move(tmp_path, file_path) # Atomic on most POSIX systems
            tmp_path = None # Indicate move was successful

            # Restore original permissions and ownership
            os.chmod(file_path, original_mode)
            if os.name != "nt": # Not Windows
                 # Attempt chown only if we might have permissions (e.g., running as root)
                 try:
                     os.chown(file_path, original_uid, original_gid)
                 except OSError as chown_err:
                      # Ignore permission errors here, as we might not be root
                      if chown_err.errno != errno.EPERM:
                          raise # Re-raise unexpected chown errors
                      else:
                          print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.chown_skipped', file=file_path) if translator else f'Skipped restoring ownership for {file_path} (requires root). Permissions restored.'}{Style.RESET_ALL}")


            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified_success', file=os.path.basename(file_path)) if translator else f'Successfully modified {os.path.basename(file_path)}'}{Style.RESET_ALL}")
            return True

        except Exception as write_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', file=file_path, error=str(write_err))}{Style.RESET_ALL}")
            # Attempt to restore backup if modification failed
            if os.path.exists(backup_path):
                try:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.restoring_backup', path=backup_path) if translator else f'Attempting to restore backup: {backup_path}'}{Style.RESET_ALL}")
                    shutil.move(backup_path, file_path) # Move backup back
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.restore_success') if translator else 'Backup restored.'}{Style.RESET_ALL}")
                except Exception as restore_err:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.restore_failed', error=str(restore_err)) if translator else f'Failed to restore backup: {restore_err}'}{Style.RESET_ALL}")
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.manual_restore_needed', original=file_path, backup=backup_path) if translator else f'Manual restore needed for {file_path} from {backup_path}'}{Style.RESET_ALL}")
            return False
        finally:
            # Clean up temp file if it wasn't moved
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass # Ignore cleanup errors

    except Exception as e:
        # Catch-all for unexpected errors during the process
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_unexpected_error', file=file_path, error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """Modify workbench.desktop.main.js content."""
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.modifying_workbench') if translator else 'Modifying workbench.desktop.main.js...'}{Style.RESET_ALL}")
    system = platform.system()

    # Define platform-specific patterns
    # Note: These patterns are FRAGILE and likely to break with Cursor updates.
    if system == "Windows":
        # Example: Change "Upgrade to Pro" button link/text
        # Original might look like: `...title:"Upgrade to Pro",...,get onClick(){return t.pay...`
        # New replaces `t.pay` with a function opening GitHub
        cbutton_old = r'title:"Upgrade to Pro",size:"small",get codicon\(\){return \w+\.rocket},get onClick\(\){return \w+\.pay}\}\),null\)' # Made regex more flexible
        cbutton_new = r'title:"VIP GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/your-repo","_blank")}}}),null)' # Use actual F or find correct var

    elif system == "Linux":
         # Often same as Windows, but verify in the actual JS file
        cbutton_old = r'title:"Upgrade to Pro",size:"small",get codicon\(\){return \w+\.rocket},get onClick\(\){return \w+\.pay}\}\),null\)'
        cbutton_new = r'title:"VIP GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/your-repo","_blank")}}}),null)'

    elif system == "Darwin":
        # macOS often uses slightly different variable names or structures
        cbutton_old = r'title:"Upgrade to Pro",size:"small",get codicon\(\){return \w+\.rocket},get onClick\(\){return \w+\.pay}\}\),null\)' # Adjust based on actual Mac JS
        cbutton_new = r'title:"VIP GitHub",size:"small",get codicon(){return $.rocket},get onClick(){return function(){window.open("https://github.com/your-repo","_blank")}}}),null)'

    else: # Should not happen if platform check is done before
         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.unsupported_os_patching') if translator else 'Unsupported OS for workbench patching.'}{Style.RESET_ALL}")
         return False


    # Other common patches (less platform dependent usually)
    cbadge_old = r'<div>Pro Trial' # Simple string replacement likely OK
    cbadge_new = r'<div>Pro'
    ctoast_old = r'notifications-toasts' # Simple string replacement
    ctoast_new = r'notifications-toasts hidden' # Add 'hidden' class to hide toast notifications

    replacements = [
        (cbadge_old, cbadge_new),
        (ctoast_old, ctoast_new),
        # Add the button replacement last, as it uses regex (is_js=True needed)
    ]
    button_replacement = (cbutton_old, cbutton_new)


    # Apply non-regex replacements first
    success = modify_file_content(file_path, replacements, translator, is_js=False)
    if not success:
         return False # Stop if initial replacements fail

    # Apply regex replacement for the button
    # We need to read the file again as modify_file_content wrote it
    # Or modify modify_file_content to handle mixed replacements (more complex)
    # Let's keep it simple and re-apply with is_js=True for the button pattern
    success_button = modify_file_content(file_path, [button_replacement], translator, is_js=True)

    return success_button # Return status of the last (button) modification


def modify_main_js(main_path: str, translator) -> bool:
    """Modify main.js file to bypass certain checks (use with caution)."""
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.modifying_mainjs') if translator else 'Modifying main.js...'}{Style.RESET_ALL}")
    # WARNING: These patches might break functionality or violate terms of service.
    # They aim to prevent the overriding of machine IDs generated by this script.
    # Patterns target functions that might fetch system IDs.
    # Example: `async getMachineId(){return external_fetch()??fallback}` becomes `async getMachineId(){return fallback}`
    replacements = [
        # Pattern 1: Look for async getMachineId(){ return ... ?? some_fallback }
        (r"async getMachineId\(\)\{return [^?]+\?\?([^}]+)\}", r"async getMachineId(){return \1}"),
        # Pattern 2: Look for async getMacMachineId(){ return ... ?? some_fallback }
        (r"async getMacMachineId\(\)\{return [^?]+\?\?([^}]+)\}", r"async getMacMachineId(){return \1}"),
        # Add more patterns here if needed based on main.js analysis
    ]

    return modify_file_content(main_path, replacements, translator, is_js=True)


def patch_cursor_get_machine_id(app_resource_dir: str, translator) -> bool:
    """Patch Cursor getMachineId function in main.js if version is >= 0.45.0."""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.start_patching_mainjs')}...{Style.RESET_ALL}")

        pkg_path, main_path = get_cursor_paths(app_resource_dir, translator)
        if not pkg_path or not main_path:
            return False # Error already printed by get_cursor_paths

        # Check version first (re-check or rely on previous check)
        # Let's assume check_cursor_version was called before and we know it's >= 0.45.0
        # If not, add the check here:
        # version_status = check_cursor_version(pkg_path, translator)
        # if version_status is None or version_status is False:
        #    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.patch_skipped_version')} {Style.RESET_ALL}")
        #    return True # Not an error, just skipped

        # Modify main.js
        if not modify_main_js(main_path, translator):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed_mainjs')}{Style.RESET_ALL}")
            return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_completed_mainjs')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e))}{Style.RESET_ALL}")
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

        self._find_paths()

    def _find_paths(self):
        """Locate all necessary Cursor paths."""
        print(f"{Fore.CYAN}{'='*20} Path Finding {'='*20}{Style.RESET_ALL}")
        self.config_dir = find_cursor_config_dir(self.translator)
        self.app_resource_dir = find_cursor_app_resource_dir(self.translator) # Find app dir too

        if self.config_dir:
            user_global_storage = os.path.join(self.config_dir, "User", "globalStorage")
            self.storage_json_path = os.path.join(user_global_storage, "storage.json")
            self.state_db_path = os.path.join(user_global_storage, "state.vscdb")
            # Machine ID file location varies slightly
            if platform.system() == "Linux":
                 # Often directly in .config/cursor, not User/globalStorage
                 self.machine_id_file_path = os.path.join(self.config_dir, "machineid")
            elif platform.system() == "Windows":
                 # In the root of %APPDATA%/Cursor
                 self.machine_id_file_path = os.path.join(self.config_dir, "machineId")
            elif platform.system() == "Darwin":
                 # In the root of Library/Application Support/Cursor
                 self.machine_id_file_path = os.path.join(self.config_dir, "machineId")
            else:
                self.machine_id_file_path = None # Fallback or error

            print(f"{EMOJI['PATH']}{Fore.GREEN}Config Dir:{Style.RESET_ALL} {self.config_dir}")
            print(f"{EMOJI['PATH']}{Fore.GREEN}Storage JSON:{Style.RESET_ALL} {self.storage_json_path}")
            print(f"{EMOJI['PATH']}{Fore.GREEN}State DB:{Style.RESET_ALL} {self.state_db_path}")
            if self.machine_id_file_path:
                print(f"{EMOJI['PATH']}{Fore.GREEN}Machine ID File:{Style.RESET_ALL} {self.machine_id_file_path}")
            else:
                 print(f"{EMOJI['PATH']}{Fore.YELLOW}Machine ID File:{Style.RESET_ALL} (Could not determine standard path)")

        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} Cannot proceed without configuration directory.{Style.RESET_ALL}")

        if self.app_resource_dir:
             print(f"{EMOJI['PATH']}{Fore.GREEN}App Resource Dir:{Style.RESET_ALL} {self.app_resource_dir}")
        else:
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} App resource directory not found. JS patching will be skipped.{Style.RESET_ALL}")

        print(f"{Fore.CYAN}{'='*53}{Style.RESET_ALL}")


    def _check_prerequisites(self) -> bool:
        """Check if essential paths and permissions are available."""
        if not self.config_dir or not self.storage_json_path or not self.state_db_path or not self.machine_id_file_path:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.error_missing_paths') if self.translator else 'One or more essential configuration paths not found. Cannot reset.'}{Style.RESET_ALL}")
             return False

        required_files = {
            "Storage JSON": self.storage_json_path,
            "State DB": self.state_db_path,
            # machineId file might not exist initially, so don't require it here
        }

        for name, path in required_files.items():
             if not os.path.exists(path):
                  print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.file_not_exist_warn', name=name, path=path) if self.translator else f'Warning: {name} file does not exist at {path}. It might be created or reset.'}{Style.RESET_ALL}")
                  # Continue, as we might be creating/resetting it.
             elif not os.access(path, os.R_OK | os.W_OK):
                  print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_permission_file', name=name, path=path) if self.translator else f'Read/Write permission denied for {name} file: {path}'}{Style.RESET_ALL}")
                  print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.try_sudo') if self.translator else 'Try running the script with sudo or as Administrator.'}{Style.RESET_ALL}")
                  return False

        # Check permissions for the directory containing machineId file
        machine_id_dir = os.path.dirname(self.machine_id_file_path)
        if not os.access(machine_id_dir, os.W_OK):
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_permission_dir', path=machine_id_dir) if self.translator else f'Write permission denied for directory: {machine_id_dir} (needed for machineId file)'}{Style.RESET_ALL}")
             print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.try_sudo') if self.translator else 'Try running the script with sudo or as Administrator.'}{Style.RESET_ALL}")
             return False

        return True


    def generate_new_ids(self) -> dict:
        """Generate new machine IDs."""
        print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.generating') if self.translator else 'Generating New Machine IDs...'}{Style.RESET_ALL}")
        dev_device_id = str(uuid.uuid4())
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest() # Often needs to be UUID format for newer versions? Check storage.json
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}" # Standard GUID format

        # Sometimes macMachineId is expected to be a UUID too, let's generate one
        # If the old one was SHA512, this might need adjustment based on Cursor version
        mac_machine_id_uuid = str(uuid.uuid4())

        new_ids = {
            "telemetry.telemetryLevel": "off", # Optional: Turn off telemetry
            "telemetry.instanceId": str(uuid.uuid4()), # Often present
            "telemetry.sessionId": str(uuid.uuid4()) + str(int(time.time() * 1000)), # Example format
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id_uuid, # Use UUID format
            "telemetry.machineId": machine_id, # Keep SHA256? Or also UUID? Needs verification in storage.json
            "telemetry.sqmId": sqm_id,
            "storage.serviceMachineId": dev_device_id, # Linked to devDeviceId
            # Potentially reset others? e.g., firstrun flags
            "workbench.startupEditor": "none",
            "extensions.ignoreRecommendations": True,
             # Reset potential trial/login related keys (use generic names, actual keys might differ)
            "cursor.internal.loginToken": "",
            "cursor.internal.userTier": "free", # Force free tier display?
            "cursor.internal.trialExpired": False,
            "cursor.internal.lastCheckTimestamp": 0,
        }
        for key, value in new_ids.items():
             print(f"  {EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")

        # Update the separate machineId file right after generating
        if not self.update_machine_id_file(machine_id): # Use the SHA256 ID here? Or devDeviceId? Check Cursor behavior. Let's use SHA256 for now.
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.machineid_update_failed_warn') if self.translator else 'Warning: Failed to update the separate machineId file.'}{Style.RESET_ALL}")
            # Continue reset? Or make it critical? Let's warn and continue.

        return new_ids


    def update_storage_json(self, new_ids: dict) -> bool:
        """Update the storage.json file."""
        if not self.storage_json_path: return False
        print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.updating_json') if self.translator else 'Updating storage.json...'}{Style.RESET_ALL}")

        # Backup
        backup_path = self.storage_json_path + ".bak"
        try:
            if os.path.exists(self.storage_json_path):
                 shutil.copy2(self.storage_json_path, backup_path)
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            else:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.json_not_exist_creating') if self.translator else 'storage.json does not exist, will create.'}{Style.RESET_ALL}")
        except Exception as backup_err:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.backup_failed_file', file='storage.json', error=str(backup_err)) if self.translator else f'Could not create backup for storage.json: {backup_err}'}{Style.RESET_ALL}")
            return False # Don't proceed without backup if file exists

        # Read existing or create new
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
                 print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.read_file_error', file='storage.json', error=str(read_err))}{Style.RESET_ALL}")
                 return False


        # Update with new IDs
        config_data.update(new_ids)

        # Write back
        try:
            with open(self.storage_json_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4) # Pretty print
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.json_update_success') if self.translator else 'storage.json updated successfully.'}{Style.RESET_ALL}")
            return True
        except Exception as write_err:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.write_file_error', file='storage.json', error=str(write_err))}{Style.RESET_ALL}")
             # Attempt restore from backup?
             if os.path.exists(backup_path):
                  try:
                      shutil.copy2(backup_path, self.storage_json_path) # Copy back
                      print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.json_restore_attempt') if self.translator else 'Attempted to restore storage.json from backup.'}{Style.RESET_ALL}")
                  except Exception as restore_err:
                      print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.restore_failed', error=str(restore_err))}{Style.RESET_ALL}")
             return False


    def update_sqlite_db(self, new_ids: dict) -> bool:
        """Update machine IDs in the SQLite state.vscdb database."""
        if not self.state_db_path: return False
        print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.updating_sqlite') if self.translator else 'Updating state.vscdb...'}{Style.RESET_ALL}")

        # Backup (important for DBs)
        backup_path = self.state_db_path + ".bak"
        try:
            if os.path.exists(self.state_db_path):
                shutil.copy2(self.state_db_path, backup_path)
                print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            else:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqlite_not_exist') if self.translator else 'state.vscdb does not exist. Skipping update.'}{Style.RESET_ALL}")
                 return True # Not an error if it doesn't exist
        except Exception as backup_err:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.backup_failed_file', file='state.vscdb', error=str(backup_err)) if self.translator else f'Could not create backup for state.vscdb: {backup_err}'}{Style.RESET_ALL}")
            return False

        conn = None
        try:
            conn = sqlite3.connect(self.state_db_path)
            cursor = conn.cursor()

            # Ensure the table exists (VSCode state DB schema)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY NOT NULL,
                    value BLOB
                )
            """)

            # Prepare updates - only update keys relevant to SQLite state if known
            # Often, the same keys as in storage.json are mirrored here.
            # Value must be stored as BLOB (bytes)
            updates = []
            for key, value in new_ids.items():
                 # Filter which keys actually go into the DB if needed
                 # Example: Only telemetry and storage keys
                 if key.startswith("telemetry.") or key.startswith("storage."):
                      updates.append((key, str(value).encode('utf-8'))) # Store as UTF-8 bytes

            if not updates:
                 print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqlite_no_keys') if self.translator else 'No relevant keys found to update in SQLite DB.'}{Style.RESET_ALL}")
                 conn.close()
                 return True

            # Use INSERT OR REPLACE (UPSERT)
            for key, value_blob in updates:
                print(f"  {EMOJI['INFO']} {self.translator.get('reset.updating_pair') if self.translator else 'Updating'}: {key}...")
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value)
                    VALUES (?, ?)
                """, (key, value_blob))

            conn.commit()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_success') if self.translator else 'SQLite database updated successfully.'}{Style.RESET_ALL}")
            return True

        except sqlite3.Error as db_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_error', error=str(db_err))}{Style.RESET_ALL}")
            # Attempt restore?
            if os.path.exists(backup_path):
                 try:
                     shutil.copy2(backup_path, self.state_db_path)
                     print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqlite_restore_attempt') if self.translator else 'Attempted to restore state.vscdb from backup.'}{Style.RESET_ALL}")
                 except Exception as restore_err:
                     print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.restore_failed', error=str(restore_err))}{Style.RESET_ALL}")
            return False
        finally:
            if conn:
                conn.close()


    def update_machine_id_file(self, new_machine_id: str) -> bool:
        """Update the separate machineId file."""
        if not self.machine_id_file_path:
             print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.machineid_path_unknown') if self.translator else 'MachineId file path is unknown, skipping update.'}{Style.RESET_ALL}")
             return False # Indicate failure to update this specific file

        print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.updating_machineid_file') if self.translator else 'Updating machineId file...'}{Style.RESET_ALL}")

        # Ensure directory exists
        machine_id_dir = os.path.dirname(self.machine_id_file_path)
        try:
             os.makedirs(machine_id_dir, exist_ok=True)
        except OSError as mkdir_err:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.mkdir_failed', path=machine_id_dir, error=str(mkdir_err)) if self.translator else f'Failed to create directory {machine_id_dir}: {mkdir_err}'}{Style.RESET_ALL}")
             return False

        # Backup existing file
        backup_path = self.machine_id_file_path + ".bak"
        if os.path.exists(self.machine_id_file_path):
             try:
                 shutil.copy2(self.machine_id_file_path, backup_path)
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
             except Exception as backup_err:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.backup_failed_file', file='machineId', error=str(backup_err)) if self.translator else f'Could not create backup for machineId file: {backup_err}'}{Style.RESET_ALL}")
                 # Decide whether to proceed without backup. Let's return False for safety.
                 return False

        # Write new ID
        try:
            with open(self.machine_id_file_path, "w", encoding="utf-8") as f:
                f.write(new_machine_id)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.machineid_update_success') if self.translator else 'machineId file updated successfully.'}{Style.RESET_ALL}")
            return True
        except Exception as write_err:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.write_file_error', file='machineId', error=str(write_err))}{Style.RESET_ALL}")
            # Attempt restore
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, self.machine_id_file_path)
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.machineid_restore_attempt') if self.translator else 'Attempted to restore machineId file from backup.'}{Style.RESET_ALL}")
                except Exception as restore_err:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.restore_failed', error=str(restore_err))}{Style.RESET_ALL}")
            return False


    # --- System ID Modification (Use with extreme caution!) ---

    def _update_windows_machine_guid(self, new_guid: str) -> bool:
        """Update Windows MachineGuid in Cryptography registry."""
        try:
            import winreg
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_win_guid') if self.translator else 'Updating Windows MachineGuid (Cryptography)...'}{Style.RESET_ALL}")
            key_path = r"SOFTWARE\Microsoft\Cryptography"
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY)
                winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
                winreg.CloseKey(key)
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.win_guid_updated') if self.translator else 'Windows MachineGuid updated.'}{Style.RESET_ALL}")
                return True
            except FileNotFoundError:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.reg_key_not_found', key=key_path) if self.translator else f'Registry key not found: {key_path}'}{Style.RESET_ALL}")
                 return False # Can't update if key doesn't exist
            except PermissionError:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied_reg', key=key_path) if self.translator else f'Permission denied for registry key: {key_path}'}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.run_as_admin') if self.translator else 'Run the script as Administrator.'}{Style.RESET_ALL}")
                return False
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_win_guid_failed', error=str(e))}{Style.RESET_ALL}")
                return False
        except ImportError:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.winreg_missing') if self.translator else 'winreg module not found (not on Windows?).'}{Style.RESET_ALL}")
             return False

    def _update_windows_sqm_machine_id(self, new_guid_braces: str) -> bool:
        """Update Windows MachineId in SQMClient registry."""
        try:
            import winreg
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_win_sqmid') if self.translator else 'Updating Windows MachineId (SQMClient)...'}{Style.RESET_ALL}")
            key_path = r"SOFTWARE\Microsoft\SQMClient"
            key = None
            try:
                # Try opening existing key first
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                # If key doesn't exist, try to create it
                try:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.sqm_key_creating', key=key_path) if self.translator else f'SQMClient key not found, attempting to create: {key_path}'}{Style.RESET_ALL}")
                    # Need to open parent key writeable to create subkey
                    parent_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft", 0, winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY)
                    key = winreg.CreateKey(parent_key, "SQMClient")
                    winreg.CloseKey(parent_key) # Close parent once subkey is created
                except PermissionError:
                     print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied_reg_create', key=key_path) if self.translator else f'Permission denied to create registry key: {key_path}'}{Style.RESET_ALL}")
                     print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.run_as_admin') if self.translator else 'Run the script as Administrator.'}{Style.RESET_ALL}")
                     return False
                except Exception as create_err:
                     print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.reg_create_failed', key=key_path, error=str(create_err)) if self.translator else f'Failed to create registry key {key_path}: {create_err}'}{Style.RESET_ALL}")
                     return False

            # If we have a key (opened or created), set the value
            if key:
                try:
                    winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, new_guid_braces)
                    winreg.CloseKey(key)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.win_sqmid_updated') if self.translator else 'Windows SQM MachineId updated.'}{Style.RESET_ALL}")
                    return True
                except PermissionError: # Should have been caught earlier, but double check
                    winreg.CloseKey(key) # Ensure key is closed on error too
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied_reg_write', key=key_path) if self.translator else f'Permission denied writing to registry key: {key_path}'}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['LOCK']} {self.translator.get('reset.run_as_admin') if self.translator else 'Run the script as Administrator.'}{Style.RESET_ALL}")
                    return False
                except Exception as e:
                    winreg.CloseKey(key)
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_win_sqmid_failed', error=str(e))}{Style.RESET_ALL}")
                    return False
            else:
                 # This case means creation failed above and error was already printed
                 return False # Key could not be opened or created

        except ImportError:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.winreg_missing') if self.translator else 'winreg module not found (not on Windows?).'}{Style.RESET_ALL}")
             return False


    def _update_macos_platform_uuid(self, new_uuid: str) -> bool:
        """Update macOS Platform UUID using system_profiler (safer) or plutil (requires sudo)."""
        # NOTE: Directly modifying system configuration files is risky.
        # Using system_profiler SPPlatformReporter DataType might show the ID, but changing it usually requires more invasive methods.
        # The original plutil method targets a specific plist, which might not be universal or safe.
        # Let's try a less direct approach or just warn the user.
        # For now, we will keep the plutil method but add strong warnings.

        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.macos_uuid_warn1') if self.translator else 'Attempting to update macOS Platform UUID is advanced and potentially risky.'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.macos_uuid_warn2') if self.translator else 'This step requires sudo privileges.'}{Style.RESET_ALL}")

        uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist" # Path requires root access

        if not os.path.exists(uuid_file):
            # This path might not exist on all macOS versions or configurations
            # Let's try finding it via system_profiler output first? Maybe too complex.
             print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.macos_plist_not_found', path=uuid_file) if self.translator else f'Platform UUID plist not found at the standard location: {uuid_file}. Skipping update.'}{Style.RESET_ALL}")
             return True # Not an error if the target doesn't exist

        # Check if running with sudo
        if os.geteuid() != 0:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.macos_sudo_required') if self.translator else 'Updating macOS Platform UUID requires running the script with sudo.'}{Style.RESET_ALL}")
             return False

        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_macos_uuid') if self.translator else 'Updating macOS Platform UUID using plutil...'}{Style.RESET_ALL}")
        try:
            # Backup the plist first
            backup_path = uuid_file + ".bak"
            try:
                 shutil.copy2(uuid_file, backup_path)
                 print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")
            except Exception as backup_err:
                 print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.backup_failed_file', file='Platform UUID plist', error=str(backup_err))}{Style.RESET_ALL}")
                 # Proceed with caution or return False? Let's proceed but warn heavily.
                 print(f"{Fore.RED}{EMOJI['WARNING']} {self.translator.get('reset.proceed_no_backup') if self.translator else 'Proceeding without backup. This is risky!'}{Style.RESET_ALL}")


            # Use plutil command to replace the UUID string
            # Ensure the new_uuid is in the correct format (usually uppercase hex string)
            formatted_uuid = new_uuid.upper()
            cmd = ['sudo', 'plutil', '-replace', 'IOPlatformUUID', '-string', formatted_uuid, uuid_file]
            # Check if 'IOPlatformUUID' is the correct key, might be just 'UUID' on older systems? Needs verification.
            # Let's stick to IOPlatformUUID as it's more common in hardware info.

            print(f"{Fore.CYAN}$ {' '.join(cmd)}{Style.RESET_ALL}") # Show command
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_uuid_updated') if self.translator else 'macOS Platform UUID updated successfully.'}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.macos_plutil_failed') if self.translator else 'Failed to execute plutil command.'}{Style.RESET_ALL}")
                print(f"{Fore.RED}Return Code: {result.returncode}{Style.RESET_ALL}")
                print(f"{Fore.RED}Stderr: {result.stderr}{Style.RESET_ALL}")
                # Attempt restore on failure
                if os.path.exists(backup_path):
                     try:
                         # Need sudo to move back too
                         restore_cmd = ['sudo', 'mv', backup_path, uuid_file]
                         print(f"{Fore.CYAN}$ {' '.join(restore_cmd)}{Style.RESET_ALL}")
                         subprocess.run(restore_cmd, check=True)
                         print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.restore_success') if self.translator else 'Backup restored.'}{Style.RESET_ALL}")
                     except Exception as restore_err:
                         print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.restore_failed_sudo', error=str(restore_err)) if self.translator else f'Failed to restore backup (needs sudo): {restore_err}'}{Style.RESET_ALL}")
                return False

        except ImportError:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.subprocess_missing') if self.translator else 'subprocess module not found.'}{Style.RESET_ALL}")
             return False
        except FileNotFoundError: # If sudo or plutil is not found
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.command_not_found', cmd='sudo/plutil') if self.translator else 'Error: sudo or plutil command not found.'}{Style.RESET_ALL}")
             return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_uuid_failed', error=str(e))}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
            return False


    def update_system_ids(self, new_ids: dict) -> bool:
        """Update system-level IDs (Windows Registry, macOS Plist). Requires Admin/sudo."""
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids') if self.translator else 'Updating System-Level IDs (Requires Admin/sudo)...'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.system_id_warning') if self.translator else 'Warning: Modifying system identifiers can have unintended consequences. Proceed with caution.'}{Style.RESET_ALL}")

        success = True
        system = platform.system()

        if system == "Windows":
             # Generate GUIDs in the correct formats
             guid_no_braces = new_ids.get("telemetry.devDeviceId", str(uuid.uuid4())) # Use devDeviceId or new UUID
             guid_with_braces = "{" + new_ids.get("telemetry.sqmId", str(uuid.uuid4()).upper()) + "}" # Use sqmId or new GUID

             print(f"{Fore.CYAN}  {EMOJI['INFO']} New MachineGuid: {guid_no_braces}{Style.RESET_ALL}")
             print(f"{Fore.CYAN}  {EMOJI['INFO']} New SQM MachineId: {guid_with_braces}{Style.RESET_ALL}")

             if not self._update_windows_machine_guid(guid_no_braces):
                 success = False # Logged failure inside function
             if not self._update_windows_sqm_machine_id(guid_with_braces):
                 success = False # Logged failure inside function

        elif system == "Darwin": # macOS
            # Use the macMachineId (which we generated as UUID)
            platform_uuid = new_ids.get("telemetry.macMachineId", str(uuid.uuid4()).upper())
            print(f"{Fore.CYAN}  {EMOJI['INFO']} New Platform UUID: {platform_uuid}{Style.RESET_ALL}")
            if not self._update_macos_platform_uuid(platform_uuid):
                success = False # Logged failure inside function

        elif system == "Linux":
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.linux_system_id_skip') if self.translator else 'System ID modification is typically not required or easily standardized on Linux. Skipping.'}{Style.RESET_ALL}")
            # No standard, widely used machine ID file like on Win/Mac.
            # /etc/machine-id is managed by systemd and shouldn't be changed lightly.
            # /var/lib/dbus/machine-id is another, also managed.
            # Best practice is to NOT modify these on Linux.
            pass # Intentionally do nothing

        else:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.unsupported_os_system_id') if self.translator else 'System ID modification not implemented for this OS.'}{Style.RESET_ALL}")


        if success:
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.system_ids_updated') if self.translator else 'System ID update process finished.'}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed') if self.translator else 'One or more system ID updates failed. Check logs above.'}{Style.RESET_ALL}")

        return success


    # --- Main Reset Orchestration ---

    def reset_machine_ids(self, skip_system_ids=False, skip_js_patches=False):
        """Orchestrate the full machine ID reset process."""
        print(f"\n{Fore.CYAN}{'='*18} Starting Cursor Reset {'='*18}{Style.RESET_ALL}")

        # 1. Check Prerequisites (Paths, Permissions)
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking_prereqs') if self.translator else 'Checking prerequisites...'}{Style.RESET_ALL}")
        if not self._check_prerequisites():
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.prereq_failed') if self.translator else 'Prerequisites check failed. Cannot proceed.'}{Style.RESET_ALL}")
            return False
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.prereq_ok') if self.translator else 'Prerequisites check passed.'}{Style.RESET_ALL}")

        # 2. Generate New IDs (and update machineId file)
        new_ids = self.generate_new_ids()
        if not new_ids: # Should not happen unless generation itself fails badly
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.id_generation_failed') if self.translator else 'Failed to generate new IDs.'}{Style.RESET_ALL}")
             return False


        # 3. Update Configuration Files (JSON & SQLite)
        json_success = self.update_storage_json(new_ids)
        sqlite_success = self.update_sqlite_db(new_ids)

        if not json_success or not sqlite_success:
             print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.config_update_failed') if self.translator else 'Failed to update core configuration files (storage.json / state.vscdb). Reset may be incomplete.'}{Style.RESET_ALL}")
             # Should we stop? Let's continue to patching/system IDs if requested, but warn heavily.
             # return False # Uncomment to make config update failure critical


        # 4. Update System-Level IDs (Optional)
        system_id_success = True
        if not skip_system_ids:
            system_id_success = self.update_system_ids(new_ids)
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.system_id_skipped') if self.translator else 'Skipping system-level ID update as requested.'}{Style.RESET_ALL}")


        # 5. Patch JavaScript Files (Optional)
        patch_success = True
        if not skip_js_patches:
            if self.app_resource_dir:
                print(f"\n{Fore.CYAN}{'='*18} Patching JavaScript {'='*18}{Style.RESET_ALL}")
                # 5a. Check version for main.js patch
                pkg_path, _ = get_cursor_paths(self.app_resource_dir, self.translator)
                version_status = None
                if pkg_path:
                     version_status = check_cursor_version(pkg_path, self.translator)

                if version_status is True: # Version >= 0.45.0
                     print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.version_ok_patching') if self.translator else 'Version >= 0.45.0, attempting main.js patch...'}{Style.RESET_ALL}")
                     if not patch_cursor_get_machine_id(self.app_resource_dir, self.translator):
                         patch_success = False # Error logged within function
                elif version_status is False: # Version < 0.45.0
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.version_low_skip_patch') if self.translator else 'Version < 0.45.0, skipping main.js patch.'}{Style.RESET_ALL}")
                else: # Error checking version
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.version_check_failed_skip_patch') if self.translator else 'Could not determine version, skipping main.js patch.'}{Style.RESET_ALL}")


                # 5b. Modify workbench.js (UI elements) - less version dependent, try anyway
                workbench_path = get_workbench_cursor_path(self.app_resource_dir, self.translator)
                if workbench_path:
                    if not modify_workbench_js(workbench_path, self.translator):
                        patch_success = False # Error logged within function
                else:
                     print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.workbench_js_not_found_skip') if self.translator else 'workbench.desktop.main.js not found, skipping UI patches.'}{Style.RESET_ALL}")
                     # Don't mark as failure if workbench.js wasn't found, maybe it's optional

            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.app_dir_not_found_skip_patches') if self.translator else 'App resource directory not found, skipping all JS patching.'}{Style.RESET_ALL}")
        else:
             print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.js_patch_skipped') if self.translator else 'Skipping JS patching as requested.'}{Style.RESET_ALL}")


        # --- Final Summary ---
        print(f"\n{Fore.CYAN}{'='*20} Reset Summary {'='*21}{Style.RESET_ALL}")
        if json_success and sqlite_success and system_id_success and patch_success:
             print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success_complete') if self.translator else 'Cursor reset process completed successfully!'}{Style.RESET_ALL}")
             print(f"\n{Fore.CYAN}{self.translator.get('reset.new_id_summary')}:{Style.RESET_ALL}")
             # Print key IDs
             print(f"  {EMOJI['INFO']} telemetry.devDeviceId: {Fore.GREEN}{new_ids.get('telemetry.devDeviceId')}{Style.RESET_ALL}")
             print(f"  {EMOJI['INFO']} telemetry.machineId: {Fore.GREEN}{new_ids.get('telemetry.machineId')}{Style.RESET_ALL}")
             print(f"  {EMOJI['INFO']} storage.serviceMachineId: {Fore.GREEN}{new_ids.get('storage.serviceMachineId')}{Style.RESET_ALL}")
             return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.success_partial') if self.translator else 'Cursor reset process finished with errors.'}{Style.RESET_ALL}")
            if not json_success: print(f"  {EMOJI['ERROR']} {self.translator.get('reset.summary_fail_json') if self.translator else 'Failed updating storage.json'}")
            if not sqlite_success: print(f"  {EMOJI['ERROR']} {self.translator.get('reset.summary_fail_sqlite') if self.translator else 'Failed updating state.vscdb'}")
            if not system_id_success and not skip_system_ids: print(f"  {EMOJI['ERROR']} {self.translator.get('reset.summary_fail_system_id') if self.translator else 'Failed updating system IDs'}")
            if not patch_success and not skip_js_patches: print(f"  {EMOJI['ERROR']} {self.translator.get('reset.summary_fail_patch') if self.translator else 'Failed applying JS patches'}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.check_logs_above') if self.translator else 'Please check the logs above for details.'}{Style.RESET_ALL}")
            return False


# --- Main Execution ---

def run(translator=None, skip_system=False, skip_patches=False):
    # Load optional config (e.g., for language, not paths)
    # config = get_config(translator) # If you have other settings

    if translator is None:
        # Basic fallback translator if none provided
        class FallbackTranslator:
            def get(self, key, **kwargs):
                text = key.replace('reset.', '').replace('_', ' ').title()
                if kwargs:
                    text += f" ({', '.join(f'{k}={v}' for k,v in kwargs.items())})"
                return text
        translator = FallbackTranslator()
        print(f"{Fore.YELLOW}Using basic fallback translator.{Style.RESET_ALL}")


    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    try:
        resetter = MachineIDResetter(translator)
        success = resetter.reset_machine_ids(skip_system_ids=skip_system, skip_js_patches=skip_patches)
    except Exception as e:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.process_error_unexpected', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        success = False

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    if success:
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.final_message_success') if translator else 'Operation finished.'}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.final_message_error') if translator else 'Operation finished with errors.'}{Style.RESET_ALL}")

    # Keep console open until user presses Enter
    try:
         input(f"{EMOJI['INFO']} {translator.get('reset.press_enter') if translator else 'Press Enter to exit...'}")
    except EOFError:
         pass # Handle case where input is piped


if __name__ == "__main__":
    import argparse
    import time # Needed for generate_new_ids
    import subprocess # Needed for macOS plutil
    import errno # Needed for chown error check

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

    # --- !!! ---
    # If you intend to use a translator object from your main script, import and pass it here.
    # Example:
    # try:
    #     from main import translator as main_translator
    # except ImportError:
    #     main_translator = None
    #     print("Could not import main translator, using fallback.")
    main_translator = None # Replace with your actual translator if available
    # --- !!! ---


    # Check for Admin/Root privileges if system IDs are NOT skipped
    needs_elevation = False
    if not args.skip_system_ids:
        system = platform.system()
        if system == "Windows":
             try:
                 # Check if the process has admin rights.
                 import ctypes
                 needs_elevation = not ctypes.windll.shell32.IsUserAnAdmin()
             except Exception:
                  print(f"{Fore.YELLOW}Warning: Could not check for Administrator privileges.{Style.RESET_ALL}")
                  needs_elevation = True # Assume needed if check fails
        elif system == "Darwin":
             needs_elevation = os.geteuid() != 0
        # No elevation needed for Linux system ID part as we skip it

    if needs_elevation:
         print(f"\n{Fore.RED}{EMOJI['LOCK']} {main_translator.get('reset.elevation_required_warn') if main_translator else 'WARNING: Modifying system IDs requires Administrator/root privileges.'}{Style.RESET_ALL}")
         print(f"{Fore.YELLOW}{main_translator.get('reset.rerun_elevated') if main_translator else 'Please re-run this script using "Run as Administrator" (Windows) or `sudo python totally_reset_cursor.py` (macOS).'}{Style.RESET_ALL}")
         print(f"{Fore.YELLOW}{main_translator.get('reset.use_skip_option') if main_translator else 'Alternatively, use the --skip-system-ids flag to proceed without modifying system identifiers.'}{Style.RESET_ALL}")
         sys.exit(1)


    run(translator=main_translator, skip_system=args.skip_system_ids, skip_patches=args.skip_js_patches)
