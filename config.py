"""
配置管理模块
"""
import os
import json
from dataclasses import dataclass
from typing import Optional

# 默认配置文件路径
CONFIG_FILE = "translator_config.json"

# OpenAI默认配置
OPENAI_DEFAULT_BASE_URL = "https://api.openai.com"
OPENAI_DEFAULT_MODEL = "gpt-4"

# Azure OpenAI默认配置
AZURE_OPENAI_DEFAULT_API_VERSION = "2024-02-01"

# 模型配置
AZURE_MODELS = {
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini"
}

AZURE_OPENAI_DEFAULT_MODEL = AZURE_MODELS["gpt-4o"]

# 语言配置
SUPPORTED_LANGUAGES = {
    "English": "English",
    "Chinese": "Simplified Chinese",  # 使用"Simplified Chinese"更准确地指定简体中文
    "Japanese": "Japanese",
    "Korean": "Korean",
    "German": "German",
    "French": "French",
    "Spanish": "Spanish"
}

# 默认语言
DEFAULT_TARGET_LANGUAGE = "English"

@dataclass
class OpenAIConfig:
    """OpenAI配置类"""
    api_key: str
    base_url: str = OPENAI_DEFAULT_BASE_URL
    model: str = OPENAI_DEFAULT_MODEL

@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI配置类"""
    endpoint: str
    api_key: str
    api_version: str = AZURE_OPENAI_DEFAULT_API_VERSION
    model: str = AZURE_OPENAI_DEFAULT_MODEL

def load_config() -> dict:
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {str(e)}")
    return {
        "openai": {
            "api_key": "",
            "base_url": OPENAI_DEFAULT_BASE_URL,
            "model": OPENAI_DEFAULT_MODEL
        },
        "azure_openai": {
            "endpoint": "",
            "api_key": "",
            "api_version": AZURE_OPENAI_DEFAULT_API_VERSION,
            "model": AZURE_OPENAI_DEFAULT_MODEL
        }
    }

def save_config(config: dict) -> None:
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {str(e)}")

def get_openai_config() -> OpenAIConfig:
    """获取OpenAI配置"""
    config = load_config()
    return OpenAIConfig(
        api_key=os.getenv('OPENAI_API_KEY', config['openai']['api_key']),
        base_url=os.getenv('OPENAI_BASE_URL', config['openai']['base_url']),
        model=config['openai']['model']
    )

def get_azure_openai_config() -> AzureOpenAIConfig:
    """获取Azure OpenAI配置"""
    config = load_config()
    return AzureOpenAIConfig(
        endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', config['azure_openai']['endpoint']),
        api_key=os.getenv('AZURE_OPENAI_API_KEY', config['azure_openai']['api_key']),
        api_version=config['azure_openai']['api_version'],
        model=config['azure_openai']['model']
    )

def update_config(
    service: str,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> None:
    """更新配置
    
    Args:
        service: 服务类型 ('openai' 或 'azure_openai')
        api_key: API密钥
        endpoint: Azure OpenAI端点
        base_url: OpenAI基础URL
        model: 模型名称
    """
    config = load_config()
    
    if service == 'openai':
        if api_key is not None:
            config['openai']['api_key'] = api_key
        if base_url is not None:
            config['openai']['base_url'] = base_url
        if model is not None:
            config['openai']['model'] = model
    
    elif service == 'azure_openai':
        if api_key is not None:
            config['azure_openai']['api_key'] = api_key
        if endpoint is not None:
            config['azure_openai']['endpoint'] = endpoint
        if model is not None:
            config['azure_openai']['model'] = model
    
    save_config(config)
