import os
import sys
import json
import shutil
import platform
import configparser
import time
import glob
import traceback

try:
    from colorama import Fore, Style, init
    init() # Initialize colorama
except ImportError:
    print("Warning: colorama not found. Output will not be colored.")
    class DummyStyle:
        def __getattr__(self, name):
            return ""
    Fore = DummyStyle()
    Style = DummyStyle()
    def init(): pass
    init()

# Define emoji constants
EMOJI = {
    'INFO': 'ℹ️',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WARNING': '⚠️',
    'FILE': '📄',
    'BACKUP': '💾',
    'RESET': '🔄',
    'VERSION': '🏷️',
    'SEARCH': '🔍',
    'PATH': '➡️ ',
    'LOCK': '🔒',
}

# --- Utility Functions ---

try:
    # Attempt to import from a potential shared utils module
    from utils import get_user_documents_path
except ImportError:
    print(f"{Fore.YELLOW}Warning: Could not import get_user_documents_path from utils. Using fallback.{Style.RESET_ALL}")
    def get_user_documents_path():
        """Fallback function to get user's documents/home directory."""
        # Simple fallback: use home directory. A more robust version might check specific OS conventions.
        return os.path.expanduser("~")

def get_actual_home_dir() -> str:
    """Gets the actual user's home directory, even when run with sudo on Linux."""
    if platform.system() == "Linux" and os.environ.get('SUDO_USER'):
        # Important for finding user config/dirs when script is run with sudo
        return os.path.expanduser(f"~{os.environ.get('SUDO_USER')}")
    return os.path.expanduser("~")

def find_cursor_app_resource_dir(translator=None) -> str | None:
    """
    Finds the Cursor application 'resources/app' directory across different OSes and installations.
    Returns the path string if found, None otherwise.
    """
    print(f"{Fore.CYAN}{EMOJI['SEARCH']} {translator.get('find_path.searching_app') if translator else 'Searching for Cursor application resource directory...'}{Style.RESET_ALL}")
    system = platform.system()
    potential_paths = []
    home_dir = get_actual_home_dir() # Use actual home for user-specific searches

    if system == "Windows":
        # Order matters: check user install first, then system-wide
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
        # Check user Applications first, then system Applications
        potential_paths.append(os.path.join(home_dir, "Applications/Cursor.app/Contents/Resources/app"))
        potential_paths.append("/Applications/Cursor.app/Contents/Resources/app")


    elif system == "Linux":
        # Standard package manager locations (order by common preference)
        potential_paths.extend([
            "/opt/Cursor/resources/app",          # Common for manual/some packages
            "/usr/share/cursor/resources/app",    # Common for system packages
            "/usr/lib/cursor/resources/app",      # Another possibility for packages
            "/usr/local/share/cursor/resources/app", # Less common system install
        ])
        # User-local installation (e.g., extracted tarball, some install scripts)
        potential_paths.append(os.path.join(home_dir, ".local/share/cursor/resources/app"))

        # AppImage extractions (common patterns) - Use glob for flexibility
        # Look in home directory
        potential_paths.extend(glob.glob(os.path.join(home_dir, "squashfs-root*/resources/app")))
        potential_paths.extend(glob.glob(os.path.join(home_dir, "squashfs-root*/usr/share/cursor/resources/app"))) # If structure inside AppImage differs
        potential_paths.extend(glob.glob(os.path.join(home_dir, ".mount_Cursor*/resources/app"))) # Some AppImage mount points
        potential_paths.extend(glob.glob(os.path.join(home_dir, "Applications/Cursor*/resources/app"))) # If extracted to ~/Applications
        # Look in /tmp (temporary extractions)
        potential_paths.extend(glob.glob("/tmp/squashfs-root*/resources/app"))
        potential_paths.extend(glob.glob("/tmp/.mount_Cursor*/resources/app"))
        # Look relative to current dir (if script is run from near extraction)
        potential_paths.extend(glob.glob("squashfs-root*/resources/app"))
        potential_paths.extend(glob.glob("squashfs-root*/usr/share/cursor/resources/app"))
        # Flatpak (sandboxed, harder to modify directly usually, but check path)
        # Note: Modifying Flatpak install might require specific commands or permissions
        potential_paths.append("/var/lib/flatpak/app/com.cursor.Cursor/current/active/files/share/cursor/resources/app") # Check actual flatpak ID if different
        # Snap (also sandboxed)
        # Path might look like /snap/cursor/current/usr/share/cursor/resources/app - check actual snap structure
        potential_paths.append("/snap/cursor/current/resources/app") # Adjust based on actual snap structure
        potential_paths.append(os.path.join(home_dir, "snap/cursor/current/resources/app")) # Newer snaps might use home dir

    else:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.unsupported_os', system=system) if translator else f'Unsupported operating system for path finding: {system}'}{Style.RESET_ALL}")
        return None

    # --- Check found paths ---
    checked_paths = set()
    for path in potential_paths:
        # Normalize path and handle potential glob results that aren't directories
        normalized_path = os.path.abspath(path)
        if normalized_path in checked_paths or not os.path.isdir(normalized_path):
            continue
        checked_paths.add(normalized_path)

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('find_path.checking', path=normalized_path) if translator else f'Checking: {normalized_path}'}{Style.RESET_ALL}")
        # Check for a key file presence within the 'app' directory to validate
        product_json_in_path = os.path.join(normalized_path, "product.json")
        if os.path.isfile(product_json_in_path):
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('find_path.found_app_at', path=normalized_path) if translator else f'Found valid app resource directory at: {normalized_path}'}{Style.RESET_ALL}")
            return normalized_path # Return the first valid path found

    # If loop finishes without finding a valid path
    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('find_path.app_not_found') if translator else 'Cursor application resource directory not found.'}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('find_path.checked_paths_app', paths=', '.join(sorted(list(checked_paths)))) if translator else f'Checked paths: {", ".join(sorted(list(checked_paths)))}'}{Style.RESET_ALL}")
    return None

def get_product_json_path(translator=None) -> str:
    """
    Finds the path to Cursor's product.json using the robust directory search.
    Raises OSError if not found.
    """
    # Use the robust finder first
    app_resource_dir = find_cursor_app_resource_dir(translator)

    if not app_resource_dir:
        # Error messages are printed inside find_cursor_app_resource_dir
        raise OSError(translator.get('bypass.app_dir_not_found') if translator else "Could not locate Cursor's resource/app directory.")

    # Construct the final path
    product_json_path = os.path.join(app_resource_dir, "product.json")

    # Final check if product.json actually exists at the constructed path
    if not os.path.isfile(product_json_path):
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('bypass.product_json_missing_in_app', path=app_resource_dir) if translator else f'Warning: Found app directory ({app_resource_dir}) but product.json is missing inside.'}{Style.RESET_ALL}")
        raise OSError(translator.get('bypass.file_not_found', path=product_json_path) if translator else f"File not found: {product_json_path}")

    print(f"{Fore.GREEN}{EMOJI['PATH']} {translator.get('bypass.product_json_located', path=product_json_path) if translator else f'Located product.json at: {product_json_path}'}{Style.RESET_ALL}")
    return product_json_path


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings (e.g., "0.45.0", "0.46.0").
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    Handles versions with potentially different numbers of parts.
    """
    try:
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        for i in range(max(len(v1_parts), len(v2_parts))):
            p1 = v1_parts[i] if i < len(v1_parts) else 0
            p2 = v2_parts[i] if i < len(v2_parts) else 0
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1

        return 0
    except ValueError:
        # Handle cases where version parts are not integers (e.g., "0.45.0-dev")
        # For simplicity here, treat non-numeric versions as potentially older or incomparable
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} Could not compare versions numerically: '{version1}' vs '{version2}'. Treating as equal for bypass logic.{Style.RESET_ALL}")
        return 0 # Default to no bypass needed if comparison fails


def bypass_version(translator=None):
    """Bypass Cursor version check by modifying product.json if needed."""
    try:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('bypass.title') if translator else 'Cursor Version Bypass Tool'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('bypass.starting') if translator else 'Starting Cursor version bypass attempt...'}{Style.RESET_ALL}")

        # --- 1. Find product.json ---
        product_json_path = get_product_json_path(translator) # This will raise OSError if not found

        # --- 2. Check Permissions ---
        if not os.access(product_json_path, os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.no_write_permission', path=product_json_path) if translator else f'No write permission for file: {product_json_path}'}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['LOCK']} {translator.get('bypass.try_sudo') if translator else 'Try running the script with sudo or as Administrator.'}{Style.RESET_ALL}")
            return False # Cannot proceed without write permission

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.permission_ok') if translator else 'Write permissions check passed.'}{Style.RESET_ALL}")

        # --- 3. Read and Check Version ---
        try:
            print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('bypass.reading_file', file='product.json') if translator else 'Reading product.json...'}{Style.RESET_ALL}")
            with open(product_json_path, "r", encoding="utf-8") as f:
                product_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.read_failed_json', error=str(e)) if translator else f'Failed to parse product.json (invalid JSON): {str(e)}'}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.read_failed', error=str(e)) if translator else f'Failed to read product.json: {str(e)}'}{Style.RESET_ALL}")
            return False

        current_version = product_data.get("version")
        if not current_version or not isinstance(current_version, str):
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('bypass.version_not_found_in_json') if translator else 'Warning: Could not find a valid "version" string in product.json.'}{Style.RESET_ALL}")
            # Decide how to handle: skip bypass or assume modification needed? Let's skip.
            return True # Indicate success (no action needed)

        print(f"{Fore.CYAN}{EMOJI['VERSION']} {translator.get('bypass.current_version', version=current_version) if translator else f'Current version found: {current_version}'}{Style.RESET_ALL}")

        # --- 4. Compare and Modify (if needed) ---
        target_version_threshold = "0.46.0"
        target_set_version = "0.48.7" # The version to set if bypass is needed

        if compare_versions(current_version, target_version_threshold) < 0:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.update_needed', current=current_version, target=target_version_threshold) if translator else f'Current version {current_version} is less than {target_version_threshold}. Attempting update...'}{Style.RESET_ALL}")

            # --- 4a. Create Backup ---
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_path = f"{product_json_path}.{timestamp}.bak"
                shutil.copy2(product_json_path, backup_path) # copy2 preserves metadata
                print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('bypass.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            except Exception as backup_err:
                 print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.backup_failed', error=str(backup_err)) if translator else f'Failed to create backup: {backup_err}'}{Style.RESET_ALL}")
                 return False # Critical failure if backup cannot be made

            # --- 4b. Modify Version in Memory ---
            product_data["version"] = target_set_version

            # --- 4c. Write Modified Data ---
            try:
                print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('bypass.writing_file', file='product.json') if translator else 'Writing modified product.json...'}{Style.RESET_ALL}")
                # Write to temp file first for safety
                temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(product_json_path), prefix="product.json.tmp")
                with os.fdopen(temp_fd, "w", encoding="utf-8") as tmp_file:
                    json.dump(product_data, tmp_file, indent=2) # Use indent for readability

                # Replace original file with temp file (atomic on most systems)
                shutil.move(temp_path, product_json_path)

                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.version_updated', old=current_version, new=target_set_version) if translator else f'Version updated from {current_version} to {target_set_version}'}{Style.RESET_ALL}")
                return True # Bypass successful

            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.write_failed', error=str(e)) if translator else f'Failed to write modified product.json: {str(e)}'}{Style.RESET_ALL}")
                # Attempt to restore backup
                if 'backup_path' in locals() and os.path.exists(backup_path):
                    try:
                         print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.restoring_backup') if translator else 'Attempting to restore backup...'}{Style.RESET_ALL}")
                         shutil.move(backup_path, product_json_path) # Move backup back
                         print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.restore_success') if translator else 'Backup restored.'}{Style.RESET_ALL}")
                    except Exception as restore_err:
                         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.restore_failed', error=str(restore_err)) if translator else f'Failed to restore backup: {restore_err}'}{Style.RESET_ALL}")
                         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.manual_restore_needed', original=product_json_path, backup=backup_path) if translator else f'Manual restore needed for {product_json_path} from {backup_path}'}{Style.RESET_ALL}")
                return False # Bypass failed
            finally:
                # Clean up temp file if it still exists (shouldn't if move succeeded)
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except OSError: pass

        else:
            # Version is already >= threshold
            print(f"{Fore.GREEN}{EMOJI['INFO']} {translator.get('bypass.no_update_needed', version=current_version, target=target_version_threshold) if translator else f'No update needed. Current version {current_version} is >= {target_version_threshold}.'}{Style.RESET_ALL}")
            return True # Indicate success (no action needed)

    except OSError as e:
         # Catch errors from get_product_json_path (path not found)
         print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.path_find_failed', error=str(e)) if translator else f'Could not find Cursor installation path: {str(e)}'}{Style.RESET_ALL}")
         return False
    except Exception as e:
        # Catch any other unexpected errors
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.bypass_failed_unexpected', error=str(e)) if translator else f'Version bypass process failed unexpectedly: {str(e)}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.stack_trace') if translator else 'Stack trace'}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False
    finally:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")


def main(translator=None):
    """Main function to run the bypass."""
    # --- !!! ---
    # If you have a translator object from your main application, pass it here.
    # Example: from main import translator
    # success = bypass_version(translator=translator)
    # --- !!! ---
    success = bypass_version(translator=translator) # Using None for now or your imported translator

    if success:
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.finished_ok') if translator else 'Bypass process finished.'}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.finished_error') if translator else 'Bypass process finished with errors.'}{Style.RESET_ALL}")

    return success


if __name__ == "__main__":
    import tempfile # Add this import for the safe writing part

    # Check if running with elevated privileges might be needed (for writing)
    # This is a simple check, might not catch all scenarios
    try:
         test_path = find_cursor_app_resource_dir() # Find path first
         if test_path:
              product_json_test_path = os.path.join(test_path, "product.json")
              if os.path.exists(product_json_test_path) and not os.access(product_json_test_path, os.W_OK):
                   print(f"\n{Fore.YELLOW}{EMOJI['LOCK']} {Style.BRIGHT}Warning:{Style.NORMAL} Write access to product.json might be required.{Style.RESET_ALL}")
                   print(f"{Fore.YELLOW}If the script fails with a permission error, try running it with{Style.RESET_ALL}")
                   if platform.system() == "Windows":
                        print(f"{Fore.YELLOW} 'Run as Administrator'.{Style.RESET_ALL}")
                   else:
                        print(f"{Fore.YELLOW} `sudo python {os.path.basename(__file__)}`.{Style.RESET_ALL}")
    except Exception:
         pass # Ignore errors during this pre-check

    main() # Run the main bypass logic

    # Optional: Pause at the end if run directly
    # input(f"\n{EMOJI['INFO']} Press Enter to exit...")
