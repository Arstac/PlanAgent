#!/bin/bash

# Setup script for Plan-and-Spawn Agent System
# This script sets up the complete environment

set -e  # Exit on error

echo "================================================"
echo "Plan-and-Spawn Agent System - Setup"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python 3.9+ is required (found $python_version)"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Install package in development mode
echo "Installing plan-spawn package in development mode..."
pip install -e .
echo "✓ Package installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   You can get an API key from: https://console.anthropic.com/"
else
    echo ".env file already exists"
fi
echo ""

# Create artifacts directory
echo "Creating artifacts directory..."
mkdir -p artifacts
echo "✓ Artifacts directory created"
echo ""

# Create project structure
echo "Setting up project structure..."
mkdir -p src/plan_spawn/core/storage
mkdir -p src/plan_spawn/core/tools
mkdir -p src/plan_spawn/config

# Create __init__.py files if they don't exist
touch src/plan_spawn/__init__.py
touch src/plan_spawn/core/__init__.py
touch src/plan_spawn/core/storage/__init__.py
touch src/plan_spawn/core/tools/__init__.py
touch src/plan_spawn/config/__init__.py

echo "✓ Project structure created"
echo ""

# Final instructions
echo "================================================"
echo "Setup Complete! 🎉"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Configure your API key in .env:"
echo "   ANTHROPIC_API_KEY=your_key_here"
echo ""
echo "3. Test the installation:"
echo "   python -m plan_spawn.main help"
echo ""
echo "4. Generate your first article:"
echo "   python -m plan_spawn.main article \"Your topic here\""
echo ""
echo "For more information, see README.md"
echo ""