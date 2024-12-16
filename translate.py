from openai import AzureOpenAI, OpenAI
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
import logging
from typing import Optional

from config import (
    OpenAIConfig, AzureOpenAIConfig,
    get_openai_config, get_azure_openai_config
)
from prompts import get_translation_messages

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseTranslator:
    """基础翻译器类"""
    def translate_text(self, text: str, target_language: str) -> str:
        """翻译文本
        
        Args:
            text: 要翻译的文本
            target_language: 目标语言
            
        Returns:
            翻译后的文本
        """
        raise NotImplementedError

class OpenAITranslator(BaseTranslator):
    """OpenAI翻译器"""
    def __init__(self, config: OpenAIConfig):
        """初始化OpenAI翻译器
        
        Args:
            config: OpenAI配置
        """
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self.model = config.model

    def translate_text(self, text: str, target_language: str) -> str:
        """使用OpenAI API翻译文本"""
        messages = get_translation_messages(text, target_language)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI translation error: {str(e)}")
            raise

class AzureOpenAITranslator(BaseTranslator):
    """Azure OpenAI翻译器"""
    def __init__(self, config: AzureOpenAIConfig):
        """初始化Azure OpenAI翻译器
        
        Args:
            config: Azure OpenAI配置
        """
        self.client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint
        )
        self.model = config.model

    def translate_text(self, text: str, target_language: str) -> str:
        """使用Azure OpenAI API翻译文本"""
        messages = get_translation_messages(text, target_language)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Azure OpenAI translation error: {str(e)}")
            raise

class TranslationClient:
    """翻译客户端基类"""
    def __init__(self, translator: BaseTranslator, max_retries: int = 3):
        self.translator = translator
        self.max_retries = max_retries

    def translate(self, text: str, target_language: str = 'English') -> str:
        """翻译方法"""
        for attempt in range(self.max_retries):
            try:
                return self.translator.translate_text(text, target_language)
            except Exception as e:
                logger.error(f"Translation attempt {attempt + 1} failed: {str(e)}")
                if attempt + 1 == self.max_retries:
                    return "error"

class DocxTranslator:
    """文档翻译器"""
    def __init__(self, translator: TranslationClient):
        self.translator = translator
        self.ns = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'
        }

    def is_math_element(self, element: ET.Element) -> bool:
        """检查元素是否为数学公式
        
        Args:
            element: XML元素
            
        Returns:
            bool: 是否为数学公式
        """
        return any(child.tag.startswith('{' + self.ns['m'] + '}') for child in element.iter())

    def extract_text(self, element: ET.Element) -> str:
        """提取需要翻译的文本
        
        Args:
            element: XML元素
            
        Returns:
            str: 提取的文本
        """
        # 如果是数学公式，直接返回空字符串，不进行翻译
        if self.is_math_element(element):
            return ''
            
        text = []
        for t in element.iter('{' + self.ns['w'] + '}t'):
            if t.text:
                text.append(t.text)
        return ''.join(text).strip()

    def update_text(self, element: ET.Element, translated_text: str) -> None:
        """更新元素的文本内容
        
        Args:
            element: XML元素
            translated_text: 翻译后的文本
        """
        if not translated_text.strip():
            return

        text_elements = list(element.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        if not text_elements:
            return

        if len(text_elements) == 1:
            text_elements[0].text = translated_text
            return

        words = translated_text.split()
        total_words = len(words)
        words_per_element = max(1, total_words // len(text_elements))

        for i, t_element in enumerate(text_elements):
            start_idx = i * words_per_element
            end_idx = start_idx + words_per_element if i < len(text_elements) - 1 else None
            if start_idx < len(words):
                t_element.text = ' '.join(words[start_idx:end_idx])
            else:
                t_element.text = ''

    def process_table(self, table: ET.Element, target_language: str = 'English') -> None:
        """处理表格
        
        Args:
            table: 表格元素
            target_language: 目标语言（默认为英语）
        """
        for row_idx, row in enumerate(table.findall('.//w:tr', self.ns)):
            for cell_idx, cell in enumerate(row.findall('.//w:tc', self.ns)):
                try:
                    cell_text = ''
                    for para in cell.findall('.//w:p', self.ns):
                        text = self.extract_text(para)
                        if text.strip():
                            cell_text += text + ' '

                    cell_text = cell_text.strip()
                    if cell_text:
                        logger.info(f"Translating cell at row {row_idx+1}, column {cell_idx+1}")
                        translated_text = self.translator.translate(cell_text, target_language)
                        if translated_text and translated_text != "error":
                            paras = cell.findall('.//w:p', self.ns)
                            if paras:
                                self.update_text(paras[0], translated_text)
                                for para in paras[1:]:
                                    for t in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                                        t.text = ''
                        else:
                            logger.warning(f"Translation failed for cell at row {row_idx+1}, column {cell_idx+1}")
                except Exception as e:
                    logger.error(f"Error processing cell at row {row_idx+1}, column {cell_idx+1}: {str(e)}")

    def translate_document(self, input_file: str, output_file: str, target_language: str = 'English') -> None:
        """翻译文档
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            target_language: 目标语言（默认为英语）
        """
        temp_dir = "temp_docx"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        try:
            with zipfile.ZipFile(input_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
            tree = ET.parse(doc_xml_path)
            root = tree.getroot()

            # 处理段落
            for element in root.findall('.//w:p', self.ns):
                text = self.extract_text(element)
                if text.strip():
                    translated_text = self.translator.translate(text, target_language)
                    self.update_text(element, translated_text)

            # 处理表格
            for table in root.findall('.//w:tbl', self.ns):
                self.process_table(table, target_language)

            tree.write(doc_xml_path, encoding='UTF-8', xml_declaration=True)

            with zipfile.ZipFile(output_file, 'w') as outzip:
                for foldername, subfolders, filenames in os.walk(temp_dir):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, temp_dir)
                        outzip.write(file_path, arcname)

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

def translate_file(input_file: str, output_file: Optional[str] = None, 
                  translator: Optional[BaseTranslator] = None,
                  target_language: str = 'English') -> str:
    """
    翻译文档的主入口函数
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径（可选）
        translator: 翻译客户端（可选）
        target_language: 目标语言（默认为英语）
    
    Returns:
        str: 输出文件路径
    """
    if not output_file:
        file_name, file_ext = os.path.splitext(input_file)
        output_file = f"{file_name}_translated{file_ext}"
    
    if not input_file.endswith('.docx'):
        raise ValueError("Input file must be a .docx file")

    if translator is None:
        # 使用默认的Azure OpenAI配置
        config = get_azure_openai_config()
        translator = AzureOpenAITranslator(config)

    docx_translator = DocxTranslator(TranslationClient(translator))
    docx_translator.translate_document(input_file, output_file, target_language)
    
    return output_file

def translate_oai(text: str, target_language: str = 'English') -> str:
    """使用OpenAI服务翻译文本
    
    Args:
        text: 要翻译的文本
        target_language: 目标语言（默认为英语）
    
    Returns:
        str: 翻译后的文本
    """
    config = get_openai_config()
    translator = OpenAITranslator(config)
    return translator.translate_text(text, target_language)

def translate_aoai(text: str, target_language: str = 'English') -> str:
    """使用Azure OpenAI服务翻译文本
    
    Args:
        text: 要翻译的文本
        target_language: 目标语言（默认为英语）
    
    Returns:
        str: 翻译后的文本
    """
    config = get_azure_openai_config()
    translator = AzureOpenAITranslator(config)
    return translator.translate_text(text, target_language)

if __name__ == "__main__":
    input_file = "./docs/大模型简介.docx"
    output_file = "./docs/translated_大模型简介 .docx"
    translate_file(input_file, output_file)