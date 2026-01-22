#!/bin/bash
set -e

PYTHON_MIN_VERSION="3.12"
PYTHON_VERSION="3.12.8"
PACKAGE_NAME="donkit-ragops"
REPO_BASE_URL="https://raw.githubusercontent.com/donkit-ai/ragops/main"

echo ""
echo "===================================="
echo "   Installing Donkit RAGOps"
echo "===================================="
echo ""

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) OS="macos" ;;
        Linux*)  OS="linux" ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "Error: Please use install.ps1 for Windows"
            echo "Run: irm ${REPO_BASE_URL}/scripts/install.ps1 | iex"
            exit 1
            ;;
        *)
            echo "Error: Unsupported OS: $(uname -s)"
            exit 1
            ;;
    esac
    echo "[*] Detected: $OS"
}

# Check if Python 3.12+ is available
check_python() {
    # Check common Python locations
    for cmd in python3.12 python3 python; do
        if command -v $cmd &> /dev/null; then
            if $cmd -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
                PYTHON_CMD=$cmd
                version=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
                echo "[+] Python $version found ($cmd)"
                return 0
            fi
        fi
    done
    return 1
}

# Install Python on macOS
install_python_macos() {
    echo "[*] Installing Python $PYTHON_VERSION..."

    # Option 1: Homebrew (if available)
    if command -v brew &> /dev/null; then
        echo "    Using Homebrew..."
        brew install python@3.12
        # Link it
        brew link python@3.12 --overwrite 2>/dev/null || true
        return 0
    fi

    # Option 2: Official PKG installer
    echo "    Downloading official installer..."
    PKG_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macos11.pkg"
    PKG_FILE="/tmp/python-${PYTHON_VERSION}.pkg"

    curl -sSL "$PKG_URL" -o "$PKG_FILE"
    echo "    Installing (requires sudo)..."
    sudo installer -pkg "$PKG_FILE" -target /
    rm "$PKG_FILE"

    # Install SSL certificates (required for HTTPS on macOS)
    CERT_SCRIPT="/Applications/Python 3.12/Install Certificates.command"
    if [ -f "$CERT_SCRIPT" ]; then
        echo "    Installing SSL certificates..."
        "$CERT_SCRIPT" > /dev/null 2>&1 || true
    fi

    # Update PATH for this session
    export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH"
    PYTHON_CMD="python3.12"
}

# Install Python on Linux
install_python_linux() {
    echo "[*] Installing Python $PYTHON_VERSION..."

    # Detect distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi

    case "$DISTRO" in
        ubuntu|debian|pop)
            echo "    Using apt (deadsnakes PPA)..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3.12 python3.12-venv python3.12-dev python3-pip
            PYTHON_CMD="python3.12"
            ;;
        fedora)
            echo "    Using dnf..."
            sudo dnf install -y python3.12 python3.12-pip
            PYTHON_CMD="python3.12"
            ;;
        rhel|centos|rocky|almalinux)
            echo "    Using dnf..."
            sudo dnf install -y python3.12 python3.12-pip || {
                # Fallback for older versions
                sudo dnf install -y python312 python312-pip
            }
            PYTHON_CMD="python3.12"
            ;;
        arch|manjaro|endeavouros)
            echo "    Using pacman..."
            sudo pacman -Sy --noconfirm python
            PYTHON_CMD="python3"
            ;;
        opensuse*|sles)
            echo "    Using zypper..."
            sudo zypper install -y python312 python312-pip
            PYTHON_CMD="python3.12"
            ;;
        *)
            # Fallback: try pyenv
            echo "    Distribution not recognized, using pyenv..."
            if ! command -v pyenv &> /dev/null; then
                curl -sSL https://pyenv.run | bash
                export PYENV_ROOT="$HOME/.pyenv"
                export PATH="$PYENV_ROOT/bin:$PATH"
                eval "$(pyenv init -)"
            fi
            pyenv install $PYTHON_VERSION
            pyenv global $PYTHON_VERSION
            PYTHON_CMD="python3"
            ;;
    esac
}

# Install Python based on OS
install_python() {
    case "$OS" in
        macos) install_python_macos ;;
        linux) install_python_linux ;;
    esac

    # Verify installation
    if ! check_python; then
        echo ""
        echo "Error: Failed to install Python $PYTHON_MIN_VERSION+"
        echo "Please install manually from https://python.org/downloads/"
        exit 1
    fi
}

# Install pipx
install_pipx() {
    if command -v pipx &> /dev/null; then
        echo "[+] pipx already installed"
        return 0
    fi

    echo "[*] Installing pipx..."

    # Use the detected Python command
    $PYTHON_CMD -m pip install --user pipx --quiet 2>/dev/null || {
        # If pip module not available, try with ensurepip
        $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || true
        $PYTHON_CMD -m pip install --user pipx --quiet
    }

    # Ensure pipx is in PATH
    $PYTHON_CMD -m pipx ensurepath --force

    # Add to current session PATH
    export PATH="$HOME/.local/bin:$PATH"

    echo "[+] pipx installed"
}

# Install donkit-ragops
install_ragops() {
    echo "[*] Installing $PACKAGE_NAME..."

    # Use pipx to install in isolated environment
    if command -v pipx &> /dev/null; then
        pipx install $PACKAGE_NAME --force --python $PYTHON_CMD
    else
        # Fallback: use python -m pipx
        $PYTHON_CMD -m pipx install $PACKAGE_NAME --force
    fi

    echo "[+] $PACKAGE_NAME installed"
}

# Fix SSL certificates on macOS
fix_ssl_certs_macos() {
    if [ "$OS" != "macos" ]; then
        return 0
    fi

    # Try running Install Certificates.command if it exists
    CERT_SCRIPT="/Applications/Python 3.12/Install Certificates.command"
    if [ -f "$CERT_SCRIPT" ]; then
        echo "[*] Configuring SSL certificates..."
        "$CERT_SCRIPT" > /dev/null 2>&1 || true
        echo "[+] SSL certificates configured"
        return 0
    fi

    # Fallback: ensure certifi is up to date in pipx venv
    PIPX_VENV="$HOME/.local/pipx/venvs/$PACKAGE_NAME"
    if [ -d "$PIPX_VENV" ]; then
        "$PIPX_VENV/bin/python" -m pip install --upgrade certifi --quiet 2>/dev/null || true
    fi
}

# Check if Node.js/npm is available
check_node() {
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        node_version=$(node --version)
        echo "[+] Node.js $node_version found"
        return 0
    fi
    return 1
}

# Install Node.js
install_node() {
    echo "[*] Installing Node.js..."

    case "$OS" in
        macos)
            if command -v brew &> /dev/null; then
                echo "    Using Homebrew..."
                brew install node
            else
                echo "    Using official installer..."
                NODE_PKG_URL="https://nodejs.org/dist/v20.11.0/node-v20.11.0.pkg"
                NODE_PKG_FILE="/tmp/node-v20.11.0.pkg"
                curl -sSL "$NODE_PKG_URL" -o "$NODE_PKG_FILE"
                echo "    Installing (requires sudo)..."
                sudo installer -pkg "$NODE_PKG_FILE" -target /
                rm "$NODE_PKG_FILE"
            fi
            ;;
        linux)
            # Use NodeSource for latest LTS
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                DISTRO=$ID
            fi

            case "$DISTRO" in
                ubuntu|debian|pop)
                    echo "    Using NodeSource..."
                    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                    sudo apt-get install -y -qq nodejs
                    ;;
                fedora)
                    sudo dnf install -y nodejs npm
                    ;;
                rhel|centos|rocky|almalinux)
                    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                    sudo dnf install -y nodejs
                    ;;
                arch|manjaro|endeavouros)
                    sudo pacman -Sy --noconfirm nodejs npm
                    ;;
                opensuse*|sles)
                    sudo zypper install -y nodejs20 npm20
                    ;;
                *)
                    echo "    Using nvm..."
                    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
                    export NVM_DIR="$HOME/.nvm"
                    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
                    nvm install 20
                    nvm use 20
                    ;;
            esac
            ;;
    esac

    echo "[+] Node.js installed"
}

# Check if Docker is available (optional)
check_docker() {
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            echo "[+] Docker found and running"
        else
            echo "[!] Docker found but not running (start Docker Desktop for full functionality)"
        fi
    else
        echo ""
        echo "[!] Docker not found (optional but recommended)"
        echo "    Install from: https://docker.com/products/docker-desktop"
    fi
}

# Print completion message
finish() {
    echo ""
    echo "===================================="
    echo "   Installation Complete!"
    echo "===================================="
    echo ""
    echo "Commands available:"
    echo "  donkit-ragops       - Start CLI agent"
    echo "  donkit-ragops-web   - Start Web UI (http://localhost:8067)"
    echo ""
    echo "Get started:"
    echo "  \$ donkit-ragops"
    echo ""

    # Check if PATH needs refresh
    if ! command -v donkit-ragops &> /dev/null; then
        echo "[!] Please restart your terminal or run:"
        case "$SHELL" in
            */zsh)  echo "    source ~/.zshrc" ;;
            */bash) echo "    source ~/.bashrc" ;;
            *)      echo "    source ~/.profile" ;;
        esac
        echo ""
    fi
}

# Main installation flow
main() {
    detect_os

    if ! check_python; then
        echo ""
        echo "[!] Python $PYTHON_MIN_VERSION+ not found"
        echo ""
        read -p "    Install Python automatically? [Y/n] " -n 1 -r response
        echo ""

        if [[ "$response" =~ ^[Nn]$ ]]; then
            echo "Please install Python $PYTHON_MIN_VERSION+ from https://python.org/downloads/"
            exit 1
        fi

        install_python
    fi

    install_pipx
    install_ragops
    fix_ssl_certs_macos

    if ! check_node; then
        echo ""
        echo "[!] Node.js not found (required for Web UI)"
        echo ""
        read -p "    Install Node.js automatically? [Y/n] " -n 1 -r response
        echo ""

        if [[ ! "$response" =~ ^[Nn]$ ]]; then
            install_node
        fi
    fi

    check_docker
    finish
}

# Run main
main
