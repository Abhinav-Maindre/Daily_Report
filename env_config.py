import os

def load_env_file(env_path=None):
    """Load key-value pairs from .env located in the current or parent directories into os.environ."""
    if env_path is None:
        search_dir = os.path.dirname(os.path.abspath(__file__))
        for _ in range(4):
            candidate = os.path.join(search_dir, ".env")
            if os.path.isfile(candidate):
                env_path = candidate
                break
            parent = os.path.dirname(search_dir)
            if parent == search_dir:
                break
            search_dir = parent

    if env_path and os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip().lstrip("\ufeff")
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass

# Automatically attempt to load local .env on import
load_env_file()

def get_pat():
    """Retrieve Azure DevOps Personal Access Token from environment or .env file.
    
    Raises:
        ValueError: If neither AZURE_DEVOPS_PAT nor PAT is configured.
    """
    pat = os.getenv("AZURE_DEVOPS_PAT") or os.getenv("PAT")
    if not pat:
        raise ValueError(
            "Azure DevOps PAT token not found!\n"
            "Please configure it on your local machine using one of the following methods:\n"
            "  1. Set the environment variable: set AZURE_DEVOPS_PAT=<your_token>\n"
            "  2. Create a local .env file in the project root: AZURE_DEVOPS_PAT=<your_token>\n"
            "  3. Set user environment variable in Windows PowerShell:\n"
            "     [System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_PAT', '<your_token>', 'User')"
        )
    return pat

def get_org(default="WLMTS"):
    """Retrieve Azure DevOps Organization name."""
    return os.getenv("AZURE_DEVOPS_ORG") or default
