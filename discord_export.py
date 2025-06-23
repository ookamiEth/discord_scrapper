#!/usr/bin/env python3
"""
Discord Chat Export Script with DiscordChatExporter Integration
Automatically downloads and uses DiscordChatExporter to export Discord chat logs
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class DiscordExporter:
    """Main class for Discord chat export functionality"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.dce_dir = self.script_dir / "dce"
        self.exports_dir = self.script_dir / "exports"
        self.config_file = self.script_dir / "config.json"
        self.dce_executable = self._get_dce_executable_name()
        self.dce_path = self.dce_dir / self.dce_executable
        
    def _get_dce_executable_name(self) -> str:
        """Get the appropriate DCE executable name for the current platform"""
        system = platform.system()
        if system == "Windows":
            return "DiscordChatExporter.Cli.exe"
        else:
            return "DiscordChatExporter.Cli"
    
    def _get_dce_download_url(self) -> str:
        """Get the appropriate DCE download URL for the current platform"""
        system = platform.system()
        base_url = "https://github.com/Tyrrrz/DiscordChatExporter/releases/latest/download/"
        
        if system == "Windows":
            return base_url + "DiscordChatExporter.Cli.win-x64.zip"
        elif system == "Darwin":  # macOS
            return base_url + "DiscordChatExporter.Cli.osx-x64.zip"
        elif system == "Linux":
            return base_url + "DiscordChatExporter.Cli.linux-x64.zip"
        else:
            raise OSError(f"Unsupported operating system: {system}")
    
    def _download_file(self, url: str, destination: Path, desc: str = "Downloading") -> bool:
        """Download a file with progress indication"""
        try:
            print(f"{desc}...")
            
            # Create request with headers to avoid potential blocking
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; DiscordExporter/1.0)'}
            )
            
            with urllib.request.urlopen(req) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(destination, 'wb') as f:
                    while True:
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}%", end='', flush=True)
                
                print("\nDownload complete!")
                return True
                
        except Exception as e:
            print(f"\nError downloading file: {e}")
            return False
    
    def _setup_dce(self) -> bool:
        """Download and set up DiscordChatExporter if not present"""
        if self.dce_path.exists():
            return True
        
        print("DiscordChatExporter not found. Setting up...")
        
        # Create DCE directory
        self.dce_dir.mkdir(exist_ok=True)
        
        # Download DCE
        zip_path = self.dce_dir / "dce_temp.zip"
        download_url = self._get_dce_download_url()
        
        if not self._download_file(download_url, zip_path, "Downloading DiscordChatExporter"):
            print("\nFailed to download DiscordChatExporter.")
            print("Please install manually from: https://github.com/Tyrrrz/DiscordChatExporter/releases")
            return False
        
        # Extract DCE
        try:
            print("Extracting DiscordChatExporter...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.dce_dir)
            
            # Make executable on Unix-like systems
            if platform.system() != "Windows":
                os.chmod(self.dce_path, 0o755)
            
            # Clean up zip file
            zip_path.unlink()
            
            print("DiscordChatExporter setup complete!")
            return True
            
        except Exception as e:
            print(f"Error extracting DiscordChatExporter: {e}")
            if zip_path.exists():
                zip_path.unlink()
            return False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file if it exists"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        return {}
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
    
    def _validate_bot_token(self, token: str) -> bool:
        """Basic validation of Discord bot token format"""
        # Discord bot tokens have a specific format
        # They're base64 encoded and have multiple parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Basic length check
        if len(token) < 50:
            return False
        
        return True
    
    def export_channel(self, channel_id: str, token: str, format: str = "html",
                      output_dir: Optional[str] = None, date_after: Optional[str] = None,
                      date_before: Optional[str] = None, media: bool = True) -> bool:
        """Export a Discord channel using DiscordChatExporter"""
        
        # Validate token
        if not self._validate_bot_token(token):
            print("Error: Invalid bot token format.")
            print("Bot tokens should be in the format: [user_id].[timestamp].[hmac]")
            print("Please check your token and try again.")
            return False
        
        # Set up output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.exports_dir
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Prepare DCE command
        cmd = [
            str(self.dce_path),
            "export",
            "-c", channel_id,
            "-t", token,
            "-f", format,
            "-o", str(output_path / f"{channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}")
        ]
        
        # Add optional parameters
        if date_after:
            cmd.extend(["--after", date_after])
        if date_before:
            cmd.extend(["--before", date_before])
        if media:
            cmd.append("--media")
        
        # Run DCE
        try:
            print(f"Exporting channel {channel_id} to {format.upper()} format...")
            print("This may take a while for large channels...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Export completed successfully!")
                return True
            else:
                print(f"Export failed with error:\n{result.stderr}")
                
                # Provide helpful error messages
                if "Unauthorized" in result.stderr:
                    print("\nError: Bot token is invalid or bot doesn't have access to the channel.")
                    print("Please ensure:")
                    print("1. The bot token is correct")
                    print("2. The bot is added to the server")
                    print("3. The bot has 'Read Message History' permission in the channel")
                elif "NotFound" in result.stderr:
                    print("\nError: Channel not found.")
                    print("Please check the channel ID is correct.")
                
                return False
                
        except FileNotFoundError:
            print("Error: DiscordChatExporter executable not found.")
            return False
        except Exception as e:
            print(f"Error running DiscordChatExporter: {e}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Export Discord chat logs using DiscordChatExporter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c 123456789012345678 -t YOUR_BOT_TOKEN
  %(prog)s -c 123456789012345678 -t YOUR_BOT_TOKEN -f json -o ./backups
  %(prog)s -c 123456789012345678 --config config.json --after 2024-01-01
        """
    )
    
    parser.add_argument("-c", "--channel", required=True, help="Discord channel ID to export")
    parser.add_argument("-t", "--token", help="Discord bot token (can also be set in config file)")
    parser.add_argument("-f", "--format", choices=["html", "json", "csv", "txt"], 
                       default="html", help="Export format (default: html)")
    parser.add_argument("-o", "--output", help="Output directory (default: ./exports)")
    parser.add_argument("--after", help="Export messages after this date (YYYY-MM-DD)")
    parser.add_argument("--before", help="Export messages before this date (YYYY-MM-DD)")
    parser.add_argument("--no-media", action="store_true", help="Don't download media attachments")
    parser.add_argument("--config", help="Path to config file (default: ./config.json)")
    parser.add_argument("--save-config", action="store_true", 
                       help="Save current settings to config file")
    
    args = parser.parse_args()
    
    # Initialize exporter
    exporter = DiscordExporter()
    
    # Load config if specified
    config = {}
    if args.config:
        exporter.config_file = Path(args.config)
    config = exporter._load_config()
    
    # Get token (command line takes precedence over config)
    token = args.token or config.get("bot_token")
    if not token:
        print("Error: No bot token provided.")
        print("Provide token via -t/--token argument or in config file.")
        return 1
    
    # Get other settings with config fallbacks
    format = args.format or config.get("default_format", "html")
    output_dir = args.output or config.get("output_directory")
    include_media = not args.no_media and config.get("include_attachments", True)
    
    # Save config if requested
    if args.save_config:
        save_config = {
            "bot_token": token,
            "default_format": format,
            "output_directory": output_dir or "./exports",
            "include_attachments": include_media
        }
        exporter._save_config(save_config)
        print("Configuration saved to:", exporter.config_file)
    
    # Set up DCE if needed
    if not exporter._setup_dce():
        return 1
    
    # Perform export
    success = exporter.export_channel(
        channel_id=args.channel,
        token=token,
        format=format,
        output_dir=output_dir,
        date_after=args.after,
        date_before=args.before,
        media=include_media
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())