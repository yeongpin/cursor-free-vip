#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logo
print_logo() {
    echo -e "${CYAN}"
    cat << "EOF"
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗      ██████╗ ██████╗  ██████╗   
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗     ██╔══██╗██╔══██╗██╔═══██╗  
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝     ██████╔╝██████╔╝██║   ██║  
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗     ██╔═══╝ ██╔══██╗██║   ██║  
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║     ██║     ██║  ██║╚██████╔╝  
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝  
EOF
    echo -e "${NC}"
}

# Get download folder path
get_downloads_dir() {
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "$HOME/Downloads"
    else
        if [ -f "$HOME/.config/user-dirs.dirs" ]; then
            . "$HOME/.config/user-dirs.dirs"
            echo "${XDG_DOWNLOAD_DIR:-$HOME/Downloads}"
        else
            echo "$HOME/Downloads"
        fi
    fi
}

# Get latest version
get_latest_version() {
    echo -e "${CYAN}ℹ️ Checking latest version...${NC}"
    latest_release=$(curl -s https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest) || {
        echo -e "${RED}❌ Cannot get latest version information${NC}"
        exit 1
    }
    
    VERSION=$(echo "$latest_release" | grep -o '"tag_name": ".*"' | cut -d'"' -f4 | tr -d 'v')
    if [ -z "$VERSION" ]; then
        echo -e "${RED}❌ Failed to parse version from GitHub API response:\n${latest_release}"
        exit 1
    fi

    echo -e "${GREEN}✅ Found latest version: ${VERSION}${NC}"
}

# Detect system type and architecture
detect_os() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # Detect macOS architecture
        ARCH=$(uname -m)
        if [[ "$ARCH" == "arm64" ]]; then
            OS="mac_arm64"
            echo -e "${CYAN}ℹ️ Detected macOS ARM64 architecture${NC}"
        else
            OS="mac_intel"
            echo -e "${CYAN}ℹ️ Detected macOS Intel architecture${NC}"
        fi
    elif [[ "$(uname)" == "Linux" ]]; then
        # Detect Linux architecture
        ARCH=$(uname -m)
        if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
            OS="linux_arm64"
            echo -e "${CYAN}ℹ️ Detected Linux ARM64 architecture${NC}"
        else
            OS="linux_x64"
            echo -e "${CYAN}ℹ️ Detected Linux x64 architecture${NC}"
        fi
    else
        # Assume Windows
        OS="windows"
        echo -e "${CYAN}ℹ️ Detected Windows system${NC}"
    fi
}

# Install and download
install_cursor_free_vip() {
    local downloads_dir=$(get_downloads_dir)
    local binary_name="CursorFreeVIP_${VERSION}_${OS}"
    local binary_path="${downloads_dir}/${binary_name}"
    local download_url="https://github.com/yeongpin/cursor-free-vip/releases/download/v${VERSION}/${binary_name}"
    
    # Check if file already exists
    if [ -f "${binary_path}" ]; then
        echo -e "${GREEN}✅ Found existing installation file${NC}"
        echo -e "${CYAN}ℹ️ Location: ${binary_path}${NC}"
        
        # Check if running as root
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}⚠️ Requesting administrator privileges...${NC}"
            if command -v sudo >/dev/null 2>&1; then
                echo -e "${CYAN}ℹ️ Starting program with sudo...${NC}"
                sudo chmod +x "${binary_path}"
                sudo "${binary_path}"
            else
                echo -e "${YELLOW}⚠️ sudo not found, trying to run normally...${NC}"
                chmod +x "${binary_path}"
                "${binary_path}"
            fi
        else
            # Already running as root
            echo -e "${CYAN}ℹ️ Already running as root, starting program...${NC}"
            chmod +x "${binary_path}"
            "${binary_path}"
        fi
        return
    fi
    
    echo -e "${CYAN}ℹ️ No existing installation file found, starting download...${NC}"
    echo -e "${CYAN}ℹ️ Downloading to ${downloads_dir}...${NC}"
    echo -e "${CYAN}ℹ️ Download link: ${download_url}${NC}"
    
    # Check if file exists
    if curl --output /dev/null --silent --head --fail "$download_url"; then
        echo -e "${GREEN}✅ File exists, starting download...${NC}"
    else
        echo -e "${RED}❌ Download link does not exist: ${download_url}${NC}"
        echo -e "${YELLOW}⚠️ Trying without architecture...${NC}"
        
        # Try without architecture
        if [[ "$OS" == "mac_arm64" || "$OS" == "mac_intel" ]]; then
            OS="mac"
            binary_name="CursorFreeVIP_${VERSION}_${OS}"
            download_url="https://github.com/yeongpin/cursor-free-vip/releases/download/v${VERSION}/${binary_name}"
            echo -e "${CYAN}ℹ️ New download link: ${download_url}${NC}"
            
            if ! curl --output /dev/null --silent --head --fail "$download_url"; then
                echo -e "${RED}❌ New download link does not exist${NC}"
                exit 1
            fi
        elif [[ "$OS" == "linux_x64" || "$OS" == "linux_arm64" ]]; then
            OS="linux"
            binary_name="CursorFreeVIP_${VERSION}_${OS}"
            download_url="https://github.com/yeongpin/cursor-free-vip/releases/download/v${VERSION}/${binary_name}"
            echo -e "${CYAN}ℹ️ New download link: ${download_url}${NC}"
            
            if ! curl --output /dev/null --silent --head --fail "$download_url"; then
                echo -e "${RED}❌ New download link does not exist${NC}"
                exit 1
            fi
        else
            exit 1
        fi
    fi
    
    # Download file
    if ! curl -L -o "${binary_path}" "$download_url"; then
        echo -e "${RED}❌ Download failed${NC}"
        exit 1
    fi
    
    # Check downloaded file size
    local file_size=$(stat -f%z "${binary_path}" 2>/dev/null || stat -c%s "${binary_path}" 2>/dev/null)
    echo -e "${CYAN}ℹ️ Downloaded file size: ${file_size} bytes${NC}"
    
    # If file is too small, it might be an error message
    if [ "$file_size" -lt 1000 ]; then
        echo -e "${YELLOW}⚠️ Warning: Downloaded file is too small, possibly not a valid executable file${NC}"
        echo -e "${YELLOW}⚠️ File content:${NC}"
        cat "${binary_path}"
        echo ""
        echo -e "${RED}❌ Download failed, please check version and operating system${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}ℹ️ Setting executable permissions...${NC}"
    if chmod +x "${binary_path}"; then
        echo -e "${GREEN}✅ Installation completed!${NC}"
        echo -e "${CYAN}ℹ️ Program downloaded to: ${binary_path}${NC}"
        echo -e "${CYAN}ℹ️ Starting program...${NC}"
        
        # Run program directly
        "${binary_path}"
    else
        echo -e "${RED}❌ Installation failed${NC}"
        exit 1
    fi
}

# Main program
main() {
    print_logo
    get_latest_version
    detect_os
    install_cursor_free_vip
}

# Run main program
main 
