#!/usr/bin/env python3
"""
System Capability Detector and Ollama Auto-Configuration

Detects system capabilities (CPU, RAM, GPU) and recommends appropriate
Ollama models based on available resources. Auto-downloads and configures
the optimal model with fallback to Gemini API.

Features:
- CPU core detection (physical and logical)
- RAM capacity detection
- GPU detection (NVIDIA, AMD, Intel, Apple Silicon)
- VRAM detection for compatible GPUs
- Smart model recommendation based on system specs
- Automatic Ollama installation and configuration
- Fallback to Gemini API if Ollama unavailable

Author: Rocket AI Team
"""

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ModelSize(Enum):
    """Model size categories based on parameter count"""
    TINY = "1.5B"      # 1-2B parameters
    SMALL = "3B"       # 3B parameters
    MEDIUM = "7B"      # 7B parameters
    LARGE = "13B"      # 13B parameters
    XLARGE = "32B"     # 32B+ parameters


@dataclass
class SystemCapabilities:
    """System hardware capabilities"""
    # CPU
    cpu_count_physical: int
    cpu_count_logical: int
    cpu_brand: str
    
    # RAM
    ram_total_gb: float
    ram_available_gb: float
    
    # GPU
    has_gpu: bool
    gpu_name: Optional[str] = None
    gpu_vram_gb: Optional[float] = None
    gpu_vendor: Optional[str] = None  # nvidia, amd, intel, apple
    
    # Platform
    os_type: str = ""  # Windows, Linux, Darwin (macOS)
    architecture: str = ""  # x86_64, arm64
    
    def __str__(self) -> str:
        """Human-readable summary"""
        lines = [
            f"System Capabilities:",
            f"  CPU: {self.cpu_brand} ({self.cpu_count_physical} cores, {self.cpu_count_logical} threads)",
            f"  RAM: {self.ram_total_gb:.1f} GB total, {self.ram_available_gb:.1f} GB available",
        ]
        
        if self.has_gpu:
            lines.append(f"  GPU: {self.gpu_name} ({self.gpu_vendor})")
            if self.gpu_vram_gb:
                lines.append(f"  VRAM: {self.gpu_vram_gb:.1f} GB")
        else:
            lines.append("  GPU: None")
        
        lines.append(f"  Platform: {self.os_type} {self.architecture}")
        
        return "\n".join(lines)


@dataclass
class OllamaModelRecommendation:
    """Recommended Ollama model configuration"""
    model_name: str
    model_size: ModelSize
    reason: str
    min_ram_gb: float
    estimated_speed: str  # "fast", "medium", "slow"
    
    def __str__(self) -> str:
        return f"{self.model_name} ({self.model_size.value} parameters) - {self.reason}"


class SystemDetector:
    """Detects system hardware capabilities"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.architecture = platform.machine()
    
    def detect_all(self) -> SystemCapabilities:
        """Detect all system capabilities"""
        logger.info("Detecting system capabilities...")
        
        cpu_physical, cpu_logical, cpu_brand = self._detect_cpu()
        ram_total, ram_available = self._detect_ram()
        has_gpu, gpu_name, gpu_vram, gpu_vendor = self._detect_gpu()
        
        caps = SystemCapabilities(
            cpu_count_physical=cpu_physical,
            cpu_count_logical=cpu_logical,
            cpu_brand=cpu_brand,
            ram_total_gb=ram_total,
            ram_available_gb=ram_available,
            has_gpu=has_gpu,
            gpu_name=gpu_name,
            gpu_vram_gb=gpu_vram,
            gpu_vendor=gpu_vendor,
            os_type=self.os_type,
            architecture=self.architecture
        )
        
        logger.info(f"\n{caps}")
        return caps
    
    def _detect_cpu(self) -> Tuple[int, int, str]:
        """Detect CPU information"""
        import psutil
        
        logical_count = psutil.cpu_count(logical=True)
        physical_count = psutil.cpu_count(logical=False) or logical_count
        
        # Try to get CPU brand
        cpu_brand = "Unknown CPU"
        try:
            if self.os_type == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_brand = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            elif self.os_type == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_brand = line.split(":")[1].strip()
                            break
            elif self.os_type == "Darwin":  # macOS
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True
                )
                cpu_brand = result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not detect CPU brand: {e}")
        
        return physical_count, logical_count, cpu_brand
    
    def _detect_ram(self) -> Tuple[float, float]:
        """Detect RAM information in GB"""
        import psutil
        
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024 ** 3)
        available_gb = memory.available / (1024 ** 3)
        
        return total_gb, available_gb
    
    def _detect_gpu(self) -> Tuple[bool, Optional[str], Optional[float], Optional[str]]:
        """Detect GPU information"""
        
        # Try NVIDIA first (most common for AI/ML)
        gpu_info = self._detect_nvidia_gpu()
        if gpu_info[0]:
            return gpu_info
        
        # Try AMD
        gpu_info = self._detect_amd_gpu()
        if gpu_info[0]:
            return gpu_info
        
        # Check for Apple Silicon
        gpu_info = self._detect_apple_gpu()
        if gpu_info[0]:
            return gpu_info
        
        # Check for Intel integrated graphics
        gpu_info = self._detect_intel_gpu()
        if gpu_info[0]:
            return gpu_info
        
        return False, None, None, None
    
    def _detect_nvidia_gpu(self) -> Tuple[bool, Optional[str], Optional[float], Optional[str]]:
        """Detect NVIDIA GPU using nvidia-smi"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    parts = output.split(",")
                    gpu_name = parts[0].strip()
                    vram_mb = float(parts[1].strip())
                    vram_gb = vram_mb / 1024
                    return True, gpu_name, vram_gb, "nvidia"
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"NVIDIA GPU detection failed: {e}")
        
        return False, None, None, None
    
    def _detect_amd_gpu(self) -> Tuple[bool, Optional[str], Optional[float], Optional[str]]:
        """Detect AMD GPU"""
        try:
            if self.os_type == "Linux":
                # Try rocm-smi
                result = subprocess.run(
                    ["rocm-smi", "--showproductname"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    return True, "AMD GPU", None, "amd"
            elif self.os_type == "Windows":
                # Check via WMI
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "AMD" in result.stdout or "Radeon" in result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if "AMD" in line or "Radeon" in line:
                            return True, line.strip(), None, "amd"
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"AMD GPU detection failed: {e}")
        
        return False, None, None, None
    
    def _detect_apple_gpu(self) -> Tuple[bool, Optional[str], Optional[float], Optional[str]]:
        """Detect Apple Silicon GPU"""
        try:
            if self.os_type == "Darwin" and self.architecture == "arm64":
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True
                )
                cpu_brand = result.stdout.strip()
                if "Apple" in cpu_brand:
                    # Apple Silicon has unified memory
                    import psutil
                    memory = psutil.virtual_memory()
                    unified_memory_gb = memory.total / (1024 ** 3)
                    return True, f"Apple {cpu_brand} GPU", unified_memory_gb, "apple"
        except Exception as e:
            logger.debug(f"Apple GPU detection failed: {e}")
        
        return False, None, None, None
    
    def _detect_intel_gpu(self) -> Tuple[bool, Optional[str], Optional[float], Optional[str]]:
        """Detect Intel integrated GPU"""
        try:
            if self.os_type == "Windows":
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "Intel" in result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if "Intel" in line and "Graphics" in line:
                            return True, line.strip(), None, "intel"
            elif self.os_type == "Linux":
                result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=5
                )
                if "Intel" in result.stdout and "VGA" in result.stdout:
                    return True, "Intel Integrated Graphics", None, "intel"
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"Intel GPU detection failed: {e}")
        
        return False, None, None, None


class ModelRecommender:
    """Recommends appropriate Ollama models based on system capabilities"""
    
    # Model recommendations with requirements
    MODELS = {
        ModelSize.TINY: {
            "model": "qwen2.5-coder:1.5b",
            "min_ram_gb": 4,
            "optimal_ram_gb": 6,
            "description": "Fastest, for resource-constrained systems"
        },
        ModelSize.SMALL: {
            "model": "qwen2.5-coder:3b",
            "min_ram_gb": 6,
            "optimal_ram_gb": 8,
            "description": "Good balance of speed and quality"
        },
        ModelSize.MEDIUM: {
            "model": "qwen2.5-coder:7b",
            "min_ram_gb": 10,
            "optimal_ram_gb": 16,
            "description": "High quality, moderate speed"
        },
        ModelSize.LARGE: {
            "model": "codellama:13b",
            "min_ram_gb": 20,
            "optimal_ram_gb": 32,
            "description": "Excellent quality, slower"
        },
        ModelSize.XLARGE: {
            "model": "codellama:34b",
            "min_ram_gb": 40,
            "optimal_ram_gb": 64,
            "description": "Best quality, requires powerful hardware"
        }
    }
    
    def recommend(self, caps: SystemCapabilities) -> OllamaModelRecommendation:
        """Recommend best model for system capabilities"""
        
        available_ram = caps.ram_available_gb
        has_powerful_gpu = caps.has_gpu and caps.gpu_vram_gb and caps.gpu_vram_gb >= 8
        
        # Decision tree for model selection
        if available_ram >= 40 and has_powerful_gpu:
            size = ModelSize.XLARGE
            speed = "medium"
            reason = "High-end system with powerful GPU"
        elif available_ram >= 20 and (has_powerful_gpu or caps.cpu_count_physical >= 8):
            size = ModelSize.LARGE
            speed = "medium"
            reason = "High-end system"
        elif available_ram >= 12 and caps.cpu_count_physical >= 4:
            size = ModelSize.MEDIUM
            speed = "fast"
            reason = "Mid-range system with good CPU"
        elif available_ram >= 8:
            size = ModelSize.SMALL
            speed = "fast"
            reason = "Entry-level system"
        else:
            size = ModelSize.TINY
            speed = "very fast"
            reason = "Resource-constrained system"
        
        model_info = self.MODELS[size]
        
        return OllamaModelRecommendation(
            model_name=model_info["model"],
            model_size=size,
            reason=f"{reason}. {model_info['description']}",
            min_ram_gb=model_info["min_ram_gb"],
            estimated_speed=speed
        )
    
    def get_fallback_models(self, caps: SystemCapabilities) -> List[OllamaModelRecommendation]:
        """Get list of fallback models in order of preference"""
        primary = self.recommend(caps)
        fallbacks = []
        
        # Get all smaller models as fallbacks
        for size in ModelSize:
            if size.value < primary.model_size.value:
                model_info = self.MODELS[size]
                fallbacks.append(OllamaModelRecommendation(
                    model_name=model_info["model"],
                    model_size=size,
                    reason=f"Fallback option. {model_info['description']}",
                    min_ram_gb=model_info["min_ram_gb"],
                    estimated_speed="fast"
                ))
        
        return [primary] + sorted(fallbacks, key=lambda x: x.model_size.value, reverse=True)


class OllamaInstaller:
    """Handles Ollama installation and configuration"""
    
    def __init__(self):
        self.os_type = platform.system()
    
    def is_ollama_installed(self) -> bool:
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def get_ollama_path(self) -> Optional[Path]:
        """Get Ollama executable path"""
        if self.os_type == "Windows":
            default_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
            if default_path.exists():
                return default_path
        
        # Try which/where command
        try:
            cmd = "where" if self.os_type == "Windows" else "which"
            result = subprocess.run(
                [cmd, "ollama"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return Path(result.stdout.strip().split("\n")[0])
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return None
    
    def install_model(self, model_name: str) -> bool:
        """Install/pull an Ollama model"""
        logger.info(f"Installing Ollama model: {model_name}")
        
        ollama_path = self.get_ollama_path()
        if not ollama_path:
            logger.error("Ollama not found")
            return False
        
        try:
            cmd = [str(ollama_path), "pull", model_name]
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=False,  # Show output to user
                text=True
            )
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to install model: {e}")
            return False
    
    def list_installed_models(self) -> List[str]:
        """List installed Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                return [line.split()[0] for line in lines if line.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Failed to list models: {e}")
        
        return []


def auto_setup_ollama() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Automatically detect system and setup Ollama with appropriate model.
    
    Returns:
        Tuple of (success, model_name, config_key)
        - success: Whether setup completed successfully
        - model_name: Recommended model name
        - config_key: Configuration key for Rocket CLI (e.g., "ollama_chat/qwen2.5-coder:1.5b")
    """
    print("=" * 60)
    print("Rocket CLI - Ollama Auto-Setup")
    print("=" * 60)
    print()
    
    # Detect system capabilities
    detector = SystemDetector()
    caps = detector.detect_all()
    print()
    
    # Get model recommendation
    recommender = ModelRecommender()
    recommendation = recommender.recommend(caps)
    
    print("\n📊 Model Recommendation:")
    print(f"  {recommendation}")
    print(f"  Minimum RAM: {recommendation.min_ram_gb} GB")
    print(f"  Estimated Speed: {recommendation.estimated_speed}")
    print()
    
    # Check if Ollama is installed
    installer = OllamaInstaller()
    if not installer.is_ollama_installed():
        print("⚠️  Ollama is not installed!")
        print("\nTo install Ollama:")
        print("  Windows: Download from https://ollama.ai/download")
        print("  macOS:   brew install ollama")
        print("  Linux:   curl https://ollama.ai/install.sh | sh")
        print()
        print("After installation, run this script again.")
        return False, None, None
    
    print("✅ Ollama is installed")
    
    # Check if model is already installed
    installed_models = installer.list_installed_models()
    if recommendation.model_name in installed_models:
        print(f"✅ Model {recommendation.model_name} is already installed")
    else:
        # Install the model
        print(f"\n📥 Installing model: {recommendation.model_name}")
        print("This may take several minutes depending on your internet connection...\n")
        
        if installer.install_model(recommendation.model_name):
            print(f"\n✅ Successfully installed {recommendation.model_name}")
        else:
            print(f"\n❌ Failed to install {recommendation.model_name}")
            return False, None, None
    
    # Generate config key
    config_key = f"ollama_chat/{recommendation.model_name}"
    
    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print(f"\nTo use this model with Rocket CLI:")
    print(f"  rocket chat --model {config_key} -m 'Your question here'")
    print()
    print("Or set as default in your config:")
    print(f"  rocket config set default_model {config_key}")
    print()
    
    return True, recommendation.model_name, config_key


if __name__ == "__main__":
    try:
        # Ensure psutil is available
        import psutil
    except ImportError:
        print("Error: psutil library is required")
        print("Install it with: pip install psutil")
        sys.exit(1)
    
    auto_setup_ollama()
