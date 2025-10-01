"""Teraslice cluster aliases management."""

from pathlib import Path
from typing import Dict, Optional

import yaml


class ClusterAliases:
    """Manages cluster aliases from ~/.teraslice/aliases.yaml"""

    def __init__(self, aliases_path: Optional[Path] = None):
        """Initialize cluster aliases.

        Args:
            aliases_path: Path to aliases file. Defaults to ~/.teraslice/aliases.yaml
        """
        if aliases_path is None:
            self.aliases_path = Path.home() / ".teraslice" / "aliases.yaml"
        else:
            self.aliases_path = aliases_path

        self._aliases: Dict[str, Dict[str, str]] = {}
        self._load_aliases()

    def _load_aliases(self) -> None:
        """Load aliases from the YAML file."""
        if not self.aliases_path.exists():
            return

        try:
            with open(self.aliases_path) as f:
                data = yaml.safe_load(f)
                if data and "clusters" in data:
                    self._aliases = data["clusters"]
        except Exception:
            # Silently fail if file can't be read or parsed
            pass

    def has_aliases(self) -> bool:
        """Check if any aliases are configured."""
        return len(self._aliases) > 0

    def get_clusters(self) -> Dict[str, str]:
        """Get mapping of cluster names to URLs.

        Returns:
            Dictionary mapping cluster name to host URL
        """
        return {name: config.get("host", "") for name, config in self._aliases.items()}

    def get_url(self, cluster_name: str) -> Optional[str]:
        """Get URL for a specific cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            URL if cluster exists, None otherwise
        """
        if cluster_name in self._aliases:
            return self._aliases[cluster_name].get("host")
        return None

    def add_cluster(self, name: str, host: str) -> None:
        """Add or update a cluster alias.

        Args:
            name: Cluster name
            host: Cluster host URL
        """
        self._aliases[name] = {"host": host}
        self._save_aliases()

    def _save_aliases(self) -> None:
        """Save aliases to the YAML file."""
        # Create directory if it doesn't exist
        self.aliases_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the aliases
        data = {"clusters": self._aliases}
        with open(self.aliases_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
