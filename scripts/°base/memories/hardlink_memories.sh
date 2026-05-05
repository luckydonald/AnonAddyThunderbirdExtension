#!/usr/bin/env bash
# Set up a hard‑link (or merge) for Claude memory folder

# Tested on:
# - Fedora 43

# QUERY:
#
# I want to hardlink the claude memory folder of my project into the git's ./.claude/memory
#
# assuming the current path to `/home/user/git/luckydonald/product-dl/` for this example.
# the path to that folder would be `/home/user/.claude/projects/-home-user-git-luckydonald-product-dl/memory` for my git repo `/home/user/git/luckydonald/product-dl/.claude/memories`. So write a short bashscript to set up that hardlink, not failing it the hardlink already exists.
# If it contains stuff but is not a hardlink, merge the folders.
# Be smart about the path:
# 1. find a `.claude/` folder in the current git, into that goes the memory
# 2. find a `CLAUDE.md` file in the current git, on the same level create `.claude/`
# 3. create `.claude/` in the git's root.
#
# I get `hard link not allowed for directory`.
# Can you do it that it attempts all of those:
# 1. dir hardlink
# 2. sudo mount
# 3. softlink
#
# If needed to mount, ask for `sudo` permissions first.
# If the users cancels/fails that, skip to softlink.
# For the mount, it shall be persistent, and not duplicated.
# 1. check if that folder is already in fstab
# 2. check if we support systemd
# 3. check if we created an entry there
# 4. If systemd is supported but our path is not mounted there or fstab, add a systemd entry for the mount.
# 5. Otherwise add it to the fstab (keep a backup, retore if mounting fails!)

set -euo pipefail

# -------------------------------------------------
# Helper: resolve absolute path without trailing slash
abs_path() {
    local p
    p=$(realpath -m "$1")
    echo "${p%/}"
}

# Helper: get Claude memory folder path for a git repo
# Encodes git root path by replacing "/" with "-"
get_claude_memory_path() {
    local git_root="$1"
    local encoded
    encoded=$(echo "$git_root" | sed 's/\//\-/g')
    echo "$HOME/.claude/projects/$encoded/memory"
}
# -------------------------------------------------

# 1. Locate the git repository root (contains .git)
git_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z $git_root ]]; then
    echo "Error: not inside a git repository."
    exit 1
fi

# 2. Determine target .claude directory inside the repo
#    a) if a .claude folder already exists anywhere in the repo, use it
#    b) else if a CLAUDE.md exists, create .claude alongside it
#    c) otherwise create .claude at the repo root
target_claude_dir=""

# a) existing .claude folder (first match)
if existing=$(find "$git_root" -type d -name ".claude" -print -quit); then
    target_claude_dir=$(abs_path "$existing")
fi

# b) fallback to CLAUDE.md location
if [[ -z $target_claude_dir ]]; then
    if md_file=$(find "$git_root" -type f -name "CLAUDE.md" -print -quit); then
        target_claude_dir=$(abs_path "$(dirname "$md_file")/.claude")
    fi
fi

# c) final fallback: repo root
if [[ -z $target_claude_dir ]]; then
    target_claude_dir=$(abs_path "$git_root/.claude")
fi

# Ensure the .claude directory exists
mkdir -p "$target_claude_dir"

# 3. Source memory folder (the one you want to link)
src_memory=$(get_claude_memory_path "$git_root")

# 4. Destination memory path inside the repo
dst_memory="$target_claude_dir/memory"

# If destination already exists and is a hard link to the source → nothing to do
if [[ -e "$dst_memory" ]]; then
    src_inode=$(stat -c %i "$src_memory")
    dst_inode=$(stat -c %i "$dst_memory")
    if [[ $src_inode -eq $dst_inode ]]; then
        echo "Hard link already in place at $dst_memory"
        exit 0
    fi
fi

# 5. If destination exists but is NOT a hard link, merge contents
if [[ -d "$dst_memory" && ! -L "$dst_memory" ]]; then
    echo "Merging existing contents into source memory..."
    # copy only items that don't already exist in source
    rsync -a --ignore-existing "$dst_memory"/ "$src_memory"/
    # remove the now‑empty destination directory
    rm -rf "$dst_memory"
fi

# -------------------------------------------------
# Helper: Check if a mount already exists
is_mounted() {
    local target="$1"
    mountpoint -q "$target" 2>/dev/null
}

# Helper: Check if a path is in fstab
is_in_fstab() {
    local src="$1"
    local dst="$2"
    grep -qE "^\s*$(echo "$src" | sed 's/\//\\\//g')\s+$(echo "$dst" | sed 's/\//\\\//g')" /etc/fstab 2>/dev/null || false
}

# Helper: Check if systemd is available
has_systemd() {
    [[ -d /etc/systemd/system ]] && command -v systemctl &>/dev/null
}

# Helper: Get systemd mount file path
get_systemd_mount_file() {
    local dst="$1"
    local escaped
    escaped=$(echo "$dst" | sed 's/^[\/]//' | sed 's/\//\-/g')
    echo "/etc/systemd/system/${escaped}.mount"
}

# Helper: Create systemd mount unit
create_systemd_mount() {
    local src="$1"
    local dst="$2"
    local mount_file

    mount_file=$(get_systemd_mount_file "$dst")

    if [[ -f "$mount_file" ]]; then
        echo "Systemd mount unit already exists: $mount_file"
        # Check if it's actually mounted
        if is_mounted "$dst"; then
            echo "Mount is active."
            return 0
        else
            echo "Mount unit exists but is not active. Trying to start it..."
            sudo systemctl start "$(basename "$mount_file")" || return 1
            if is_mounted "$dst"; then
                echo "Mount is now active."
                return 0
            else
                echo "Failed to activate mount."
                return 1
            fi
        fi
    fi

    echo "Creating systemd mount unit at $mount_file..."

    # Create the mount unit content
    # MakeDirectory=yes ensures the mount point is created if it doesn't exist
    local unit_content="[Unit]
Description=Bind mount for Claude memory folder
After=local-fs.target

[Mount]
What=$src
Where=$dst
Type=none
Options=bind
MakeDirectory=yes

[Install]
WantedBy=multi-user.target
"

    # Write with sudo and set permissions
    echo "$unit_content" | sudo tee "$mount_file" > /dev/null
    sudo systemctl daemon-reload
    echo "Systemd mount unit created. Enabling and starting..."
    sudo systemctl enable "$(basename "$mount_file")"
    sudo systemctl start "$(basename "$mount_file")"
}

# Helper: Add to fstab with backup
add_to_fstab() {
    local src="$1"
    local dst="$2"
    local timestamp
    local fstab_backup

    timestamp=$(date +%s)
    fstab_backup="/etc/fstab.bak.$timestamp"

    if is_in_fstab "$src" "$dst"; then
        echo "Entry already in fstab"
        return 0
    fi

    # Ensure mount point exists
    if [[ ! -d "$dst" ]]; then
        echo "Creating mount point directory: $dst"
        mkdir -p "$dst"
    fi

    echo "Backing up /etc/fstab to $fstab_backup..."
    sudo cp /etc/fstab "$fstab_backup"

    echo "Adding entry to /etc/fstab..."
    echo "$src $dst none bind 0 0" | sudo tee -a /etc/fstab > /dev/null

    echo "Mounting..."
    if sudo mount "$dst"; then
        echo "Successfully mounted and added to fstab"
        return 0
    else
        echo "Mount failed! Restoring /etc/fstab from backup..."
        sudo mv "$fstab_backup" /etc/fstab
        return 1
    fi
}

# Helper: Try mount approach
try_mount() {
    local src="$1"
    local dst="$2"

    echo "Attempting bind mount..."

    # Check if already mounted
    if is_mounted "$dst"; then
        echo "Already mounted at $dst"
        return 0
    fi

    # Ask for sudo permission
    echo "Bind mount requires sudo. Do you want to proceed? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Skipping mount, will try softlink instead."
        return 1
    fi

    # Check if we can use sudo
    if ! sudo -n true 2>/dev/null; then
        echo "Requesting sudo permissions..."
        if ! sudo -v; then
            echo "Sudo permission denied, skipping mount."
            return 1
        fi
    fi

    # Try systemd mount first if available
    if has_systemd; then
        echo "Systemd detected, using systemd mount unit..."
        if create_systemd_mount "$src" "$dst"; then
            return 0
        fi
    fi

    # Fall back to fstab
    echo "Using fstab for persistent mount..."
    if add_to_fstab "$src" "$dst"; then
        return 0
    fi

    return 1
}

# -------------------------------------------------
# 6. Attempt linking/mounting in order: hardlink → mount → softlink

# Try hard link (directory hard link)
#    Use ln -d on Linux; on macOS use ln -T
if ln -d "$src_memory" "$dst_memory" 2>/dev/null; then
    echo "✓ Hard link created: $dst_memory → $src_memory"
    exit 0
fi

# macOS fallback (junction)
if ln -T "$src_memory" "$dst_memory" 2>/dev/null; then
    echo "✓ Hard link (junction) created on macOS: $dst_memory → $src_memory"
    exit 0
fi

echo "✗ Hard linking failed (not supported on this filesystem)"

# Try mount
if try_mount "$src_memory" "$dst_memory"; then
    # Verify mount is actually active
    if is_mounted "$dst_memory"; then
        echo "✓ Mount successful and verified: $dst_memory → $src_memory"
        exit 0
    else
        echo "⚠ Mount function returned success but mount is not active!"
    fi
fi

echo "✗ Mount failed or declined"

# Fall back to softlink
echo "Creating softlink as final fallback..."
if ln -s "$src_memory" "$dst_memory"; then
    # Verify symlink
    if [[ -L "$dst_memory" ]] && [[ "$(readlink "$dst_memory")" == "$src_memory" ]]; then
        echo "✓ Softlink created and verified: $dst_memory → $src_memory"
        echo "⚠ Note: This is a softlink, not a hardlink or mount. It may not work in all contexts."
        exit 0
    fi
fi

echo "✗ All linking methods failed!"
exit 1
