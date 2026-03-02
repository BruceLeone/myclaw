#!/usr/bin/env python3
"""
Speech-to-Text (STT) Service
Supports English and Chinese transcription
Uses Whisper (local or API)
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

class STTService:
    """Speech-to-Text service with English and Chinese support"""
    
    def __init__(self, use_local: bool = True, api_key: Optional[str] = None):
        self.use_local = use_local
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.supported_formats = ['.mp3', '.mp4', '.m4a', '.wav', '.webm', '.ogg', '.oga']
        self.progress_file = Path("/root/.openclaw/workspace/stt_progress.json")
        
    def check_whisper_local(self) -> bool:
        """Check if local whisper is installed"""
        try:
            result = subprocess.run(['whisper', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_whisper(self) -> bool:
        """Install local whisper"""
        print("Installing Whisper...")
        try:
            # Install whisper and dependencies
            subprocess.run([sys.executable, '-m', 'pip', 'install', 
                         'openai-whisper', '-q'], check=True)
            subprocess.run([sys.executable, '-m', 'pip', 'install', 
                         'ffmpeg-python', '-q'], check=True)
            print("✓ Whisper installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install Whisper: {e}")
            return False
    
    def transcribe_local(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe using local Whisper"""
        import whisper
        
        print(f"Loading Whisper model...")
        # Use base model for speed, can upgrade to 'small', 'medium', 'large' for accuracy
        model = whisper.load_model("base")
        
        print(f"Transcribing: {audio_path}")
        
        # Auto-detect language if not specified
        options = {}
        if language:
            options['language'] = language
        
        result = model.transcribe(audio_path, **options)
        
        return {
            'text': result['text'],
            'language': result.get('language', 'unknown'),
            'segments': result.get('segments', []),
            'source': 'local_whisper'
        }
    
    def transcribe_api(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe using OpenAI API"""
        from openai import OpenAI
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
        
        client = OpenAI(api_key=self.api_key)
        
        print(f"Sending to OpenAI API: {audio_path}")
        
        with open(audio_path, 'rb') as audio_file:
            options = {
                'model': 'whisper-1',
                'file': audio_file
            }
            if language:
                options['language'] = language
            
            response = client.audio.transcriptions.create(**options)
        
        return {
            'text': response.text,
            'language': language or 'auto',
            'source': 'openai_api'
        }
    
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Main transcription method"""
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if audio_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported format: {audio_path.suffix}. "
                           f"Supported: {self.supported_formats}")
        
        # Update progress
        self._update_progress('processing', str(audio_path))
        
        try:
            if self.use_local:
                if not self.check_whisper_local():
                    print("Whisper not found. Attempting to install...")
                    if not self.install_whisper():
                        raise RuntimeError("Failed to install Whisper. "
                                         "Please install manually: pip install openai-whisper")
                result = self.transcribe_local(str(audio_path), language)
            else:
                result = self.transcribe_api(str(audio_path), language)
            
            # Save progress
            self._update_progress('completed', str(audio_path), result)
            return result
            
        except Exception as e:
            self._update_progress('failed', str(audio_path), error=str(e))
            raise
    
    def _update_progress(self, status: str, file_path: str, 
                        result: Optional[Dict] = None, error: Optional[str] = None):
        """Update progress tracking"""
        progress = self._load_progress()
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'file': file_path
        }
        
        if result:
            entry['result'] = result
        if error:
            entry['error'] = error
        
        progress['history'].append(entry)
        progress['last_updated'] = datetime.now().isoformat()
        progress['stats']['total_processed'] = len([h for h in progress['history'] 
                                                     if h['status'] == 'completed'])
        progress['stats']['total_failed'] = len([h for h in progress['history'] 
                                                  if h['status'] == 'failed'])
        
        self.progress_file.write_text(json.dumps(progress, indent=2, ensure_ascii=False))
    
    def _load_progress(self) -> Dict:
        """Load progress file"""
        if self.progress_file.exists():
            return json.loads(self.progress_file.read_text())
        return {
            'history': [],
            'stats': {'total_processed': 0, 'total_failed': 0},
            'last_updated': None
        }
    
    def get_progress_report(self) -> str:
        """Generate progress report"""
        progress = self._load_progress()
        
        report = f"""
📊 STT Progress Report
━━━━━━━━━━━━━━━━━━━━━━
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 Statistics:
   • Total Processed: {progress['stats']['total_processed']}
   • Total Failed: {progress['stats']['total_failed']}
   • Success Rate: {self._calculate_success_rate(progress['stats']):.1f}%

🕐 Recent Activity (last 10):
"""
        
        recent = progress['history'][-10:]
        for entry in reversed(recent):
            status_emoji = '✅' if entry['status'] == 'completed' else '❌' if entry['status'] == 'failed' else '⏳'
            filename = Path(entry['file']).name
            time_str = entry['timestamp'].split('T')[1][:8] if 'T' in entry['timestamp'] else ''
            report += f"   {status_emoji} {time_str} - {filename[:40]}\n"
        
        return report
    
    def _calculate_success_rate(self, stats: Dict) -> float:
        """Calculate success rate percentage"""
        total = stats['total_processed'] + stats['total_failed']
        if total == 0:
            return 100.0
        return (stats['total_processed'] / total) * 100


def main():
    parser = argparse.ArgumentParser(description='Speech-to-Text Service')
    parser.add_argument('audio_file', nargs='?', help='Audio file to transcribe')
    parser.add_argument('--language', '-l', choices=['en', 'zh', 'auto'],
                       default='auto', help='Language (en=English, zh=Chinese)')
    parser.add_argument('--api', action='store_true', 
                       help='Use OpenAI API instead of local Whisper')
    parser.add_argument('--report', action='store_true',
                       help='Show progress report')
    parser.add_argument('--install', action='store_true',
                       help='Install dependencies only')
    
    args = parser.parse_args()
    
    # Map language codes
    lang_map = {'en': 'en', 'zh': 'zh', 'auto': None}
    language = lang_map[args.language]
    
    service = STTService(use_local=not args.api)
    
    if args.install:
        service.install_whisper()
        print("✓ Installation complete")
        return
    
    if args.report:
        print(service.get_progress_report())
        return
    
    if not args.audio_file:
        parser.print_help()
        return
    
    try:
        print(f"🎙️  Transcribing: {args.audio_file}")
        print(f"   Language: {args.language}")
        print(f"   Mode: {'API' if args.api else 'Local'}\n")
        
        result = service.transcribe(args.audio_file, language)
        
        print("\n" + "="*50)
        print("📝 TRANSCRIPTION:")
        print("="*50)
        print(result['text'])
        print("="*50)
        print(f"\n✓ Detected Language: {result.get('language', 'unknown')}")
        print(f"✓ Source: {result['source']}")
        
        # Save to file
        output_path = Path(args.audio_file).with_suffix('.txt')
        output_path.write_text(result['text'], encoding='utf-8')
        print(f"✓ Saved to: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
