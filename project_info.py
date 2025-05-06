"""
Project information module - reads all project metadata from pyproject.toml
Import this module in any file that needs project information.
"""
import os
import sys

# Use built-in tomllib in Python 3.11+, or fallback to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("Please install tomli package: pip install tomli")

def get_project_info():
    """Get all project information from pyproject.toml"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pyproject_path = os.path.join(current_dir, 'pyproject.toml')
    
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
            return pyproject_data.get("project", {})
    except (FileNotFoundError, KeyError):
        return {}

# Load project info once at module level
project_info = get_project_info()

# Easy access to common attributes
VERSION = project_info.get("version", "1.0.0")
NAME = project_info.get("name", "cursor-free-vip")
DESCRIPTION = project_info.get("description", "")
AUTHORS = project_info.get("authors", [])
DEPENDENCIES = project_info.get("dependencies", [])

# For accessing any other project field
def get(key, default=None):
    """Get any project field by key name"""
    return project_info.get(key, default) 