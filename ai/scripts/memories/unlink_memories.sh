#!/usr/bin/env bash
# Clean up hardlink/mount/symlink for Claude memory folder

# Tested on:
# - Fedora 43

# Removes the links from `hardlink_memory.sh` - see that file for documentation.

set -euo pipefail

# -------------------------------------------------
# Helper: resolve absolute path without trailing slash
abs_path() {
    local p
    p=$(realpath -m "$1")
    echo "${p%/}"
}

# Helper: Check if a mount exists
is_mounted() {
    local target="$1"
    mountpoint -q "$target" 2>/dev/null
}

# Helper: Check if systemd is available
has_systemd() {
    [[ -d /etc/systemd/system ]] && command -v systemctl &>/dev/null
}

# Helper: get Claude memory folder path for a git repo
# Encodes git root path by replacing "/" with "-"
get_claude_memory_path() {
    local git_root="$1"
    local encoded
    encoded=$(echo "$git_root" | sed 's/\//\-/g')
    echo "$HOME/.claude/projects/$encoded/memory"
}

# Helper: Get systemd mount file path
get_systemd_mount_file() {
    local dst="$1"
    local escaped
    escaped=$(echo "$dst" | sed 's/^[\/]//' | sed 's/\//\-/g')
    echo "/etc/systemd/system/${escaped}.mount"
}

# -------------------------------------------------
# 1. Locate the git repository root
git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z $git_root ]]; then
    echo "Error: not inside a git repository."
    exit 1
fi

# 2. Determine target .claude directory
target_claude_dir=""

if existing=$(find "$git_root" -type d -name ".claude" -print -quit 2>/dev/null); then
    target_claude_dir=$(abs_path "$existing")
fi

if [[ -z $target_claude_dir ]]; then
    if md_file=$(find "$git_root" -type f -name "CLAUDE.md" -print -quit 2>/dev/null); then
        target_claude_dir=$(abs_path "$(dirname "$md_file")/.claude")
    fi
fi

if [[ -z $target_claude_dir ]]; then
    target_claude_dir=$(abs_path "$git_root/.claude")
fi

# 3. Source and destination paths
src_memory=$(get_claude_memory_path "$git_root")
dst_memory="$target_claude_dir/memory"

echo "Checking for links at: $dst_memory"

# 4. Check what type of link exists
if [[ ! -e "$dst_memory" && ! -L "$dst_memory" ]]; then
    echo "✓ Already cleaned up (nothing at $dst_memory)"
    exit 0
fi

# Check if it's a mount
if is_mounted "$dst_memory"; then
    echo "Found: Bind mount"
    read -rp "Unmount and remove from systemd/fstab? (y/n) " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Skipping unmount."
        exit 0
    fi

    # Unmount
    echo "Unmounting..."
    if ! sudo umount "$dst_memory"; then
        echo "✗ Failed to unmount. Make sure no processes are using it."
        exit 1
    fi

    # Remove from systemd
    mount_file=$(get_systemd_mount_file "$dst_memory")
    if [[ -f "$mount_file" ]]; then
        echo "Removing systemd mount unit..."
        sudo systemctl disable "$(basename "$mount_file")" 2>/dev/null || true
        sudo rm "$mount_file"
        sudo systemctl daemon-reload
        echo "Systemd mount unit removed."
    fi

    # Remove from fstab
    if grep -q "$(echo "$src_memory" | sed 's/\//\\\//g')" /etc/fstab 2>/dev/null; then
        echo "Removing fstab entry..."
        fstab_backup="/etc/fstab.bak.$(date +%s).unlink"
        sudo cp /etc/fstab "$fstab_backup"
        sudo sed -i "\|^$(echo "$src_memory" | sed 's/\//\\\//g')\s|d" /etc/fstab
        echo "fstab entry removed (backup: $fstab_backup)"
    fi

    # Remove the mount point directory if empty
    if [[ -d "$dst_memory" ]] && [[ -z "$(ls -A "$dst_memory" 2>/dev/null)" ]]; then
        rmdir "$dst_memory"
        echo "✓ Mount point directory removed."
    fi

    echo "✓ Mount cleaned up successfully."
    exit 0
fi

# Check if it's a symlink
if [[ -L "$dst_memory" ]]; then
    echo "Found: Symlink"
    target=$(readlink "$dst_memory")
    echo "  → $target"
    read -rp "Remove symlink? (y/n) " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Skipping removal."
        exit 0
    fi

    rm "$dst_memory"
    echo "✓ Symlink removed."
    exit 0
fi

# Check if it's a hardlink (same inode)
if [[ -d "$dst_memory" ]]; then
    src_ino=$(stat -c %i "$src_memory" 2>/dev/null || echo "")
    dst_ino=$(stat -c %i "$dst_memory" 2>/dev/null || echo "")
    if [[ -n "$src_ino" && -n "$dst_ino" && "$src_ino" == "$dst_ino" ]]; then
        echo "Found: Hardlink"
        echo "  inode: $dst_ino"
        read -rp "Remove hardlink? (y/n) " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Skipping removal."
            exit 0
        fi

        # For hardlinks, we can't just delete one side
        # We need to unlink the directory entry
        unlink "$dst_memory" 2>/dev/null || rm -rf "$dst_memory"
        echo "✓ Hardlink removed."
        exit 0
    fi
fi

# Unknown state
echo "Found: Unknown directory/file at $dst_memory"
echo "  Type: $(file "$dst_memory" 2>/dev/null | cut -d: -f2 || echo 'unknown')"
read -rp "Remove it? (y/n) " response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Skipping removal."
    exit 0
fi

if [[ -d "$dst_memory" ]]; then
    rm -rf "$dst_memory"
else
    rm "$dst_memory"
fi
echo "✓ Removed."