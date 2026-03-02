#!/bin/bash
# Setup script for STT Service

echo "🔧 Setting up Speech-to-Text Service..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install required packages
echo "📦 Installing dependencies..."
pip3 install -q openai-whisper ffmpeg-python openai

# Make scripts executable
chmod +x /root/.openclaw/workspace/stt_service.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  python3 /root/.openclaw/workspace/stt_service.py <audio_file>"
echo "  python3 /root/.openclaw/workspace/stt_service.py <audio_file> --language zh"
echo "  python3 /root/.openclaw/workspace/stt_service.py --report"
echo ""
echo "Supported formats: mp3, mp4, m4a, wav, webm, ogg, oga"
