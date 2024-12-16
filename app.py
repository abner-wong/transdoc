"""
Document translation application
"""
import streamlit as st
from config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_TARGET_LANGUAGE,
    OpenAIConfig,
    AzureOpenAIConfig,
    load_config,
    save_config,
    OPENAI_DEFAULT_BASE_URL,
    OPENAI_DEFAULT_MODEL,
    AZURE_MODELS,
    AZURE_OPENAI_DEFAULT_MODEL
)
from translate import (
    OpenAITranslator,
    AzureOpenAITranslator,
    DocxTranslator,
    BaseTranslator,
    TranslationClient
)
import os
import tempfile

# UI Language configuration
UI_LANGUAGES = {
    "English": {
        # Common
        "app_title": "Document Translator",
        "configuration": "Configuration",
        "select_service": "Select Service",
        "api_configuration": "API Configuration",
        "save_config": "Save {} Config",
        "config_saved": "{} configuration saved!",
        "api_key_required": "API Key is required",
        "both_required": "Both API Key and Endpoint are required for Azure OpenAI",
        
        # Translation
        "target_language": "Target Language",
        "text_translation": "Text Translation",
        "document_translation": "Document Translation",
        "enter_text": "Enter text to translate:",
        "translate_text": "Translate Text",
        "translated_text": "Translated Text:",
        "please_enter_text": "Please enter some text to translate.",
        "choose_file": "Choose a DOCX file",
        "start_translation": "🔄 Start Translation",
        "translating": "Translating...",
        "preparing_doc": "Preparing document...",
        "translating_content": "Translating content...",
        "preparing_download": "Preparing download...",
        "translation_completed": "Translation completed!",
        "download_translated": "📥 Download Translated Document",
        "translation_process": """
        📝 **Translation Process**:
        1. Click "Start Translation" to begin
        2. Wait for the translation to complete
        3. Download the translated document
        4. To ensure consistent formatting, the script will unzip and re-compress the docx files. You might need to open the file and save it as a new document
        
        ⏱️ Translation time depends on document size
        """,
        "configure_api": "⚠️ Please configure your API settings in the sidebar first.",
        "upload_prompt": "👆 Please upload a DOCX file to begin",
        "file_uploaded": "File uploaded: {}",
        "file_info": {
            "filename": "Filename",
            "filesize": "File size"
        }
    },
    "中文": {
        # Common
        "app_title": "文档翻译工具",
        "configuration": "配置",
        "select_service": "选择服务",
        "api_configuration": "API 配置",
        "save_config": "保存 {} 配置",
        "config_saved": "{} 配置已保存！",
        "api_key_required": "需要填写 API Key",
        "both_required": "Azure OpenAI 需要同时填写 API Key 和 Endpoint",
        
        # Translation
        "target_language": "目标语言",
        "text_translation": "文本翻译",
        "document_translation": "文档翻译",
        "enter_text": "输入要翻译的文本：",
        "translate_text": "翻译文本",
        "translated_text": "翻译结果：",
        "please_enter_text": "请输入要翻译的文本。",
        "choose_file": "选择 DOCX 文件",
        "start_translation": "🔄 开始翻译",
        "translating": "正在翻译...",
        "preparing_doc": "正在准备文档...",
        "translating_content": "正在翻译内容...",
        "preparing_download": "正在准备下载...",
        "translation_completed": "翻译完成！",
        "download_translated": "📥 下载翻译后的文档",
        "translation_process": """
        📝 **翻译流程**：
        1. 点击"开始翻译"按钮
        2. 等待翻译完成
        3. 下载翻译后的文档
        4. 为了保证格式一致，脚本将会解压并重新压缩docx文件，你可能需要打开文件并另存为新文件。
        
        ⏱️ 翻译时间取决于文档大小
        """,
        "configure_api": "⚠️ 请先在侧边栏配置 API 设置。",
        "upload_prompt": "👆 请上传一个 DOCX 文件",
        "file_uploaded": "已上传文件：{}",
        "file_info": {
            "filename": "文件名",
            "filesize": "文件大小"
        }
    }
}

def get_translator(service_type: str) -> BaseTranslator:
    """Get appropriate translator based on configuration"""
    config = load_config()
    
    if service_type.startswith("openai"):
        # 检查 OpenAI 配置
        openai_config = config.get("openai", {})
        if not openai_config.get("api_key"):
            st.error("Please configure OpenAI API key in the sidebar.")
            return None
            
        return TranslationClient(OpenAITranslator(OpenAIConfig(
            api_key=openai_config["api_key"],
            base_url=openai_config.get("base_url", OPENAI_DEFAULT_BASE_URL),
            model=openai_config.get("model", OPENAI_DEFAULT_MODEL)
        )))
    
    elif service_type.startswith("azure"):
        # 检查 Azure OpenAI 配置
        azure_config = config.get("azure_openai", {})
        if not azure_config.get("api_key") or not azure_config.get("endpoint"):
            st.error("Please configure both API key and Endpoint for Azure OpenAI in the sidebar.")
            return None
            
        return TranslationClient(AzureOpenAITranslator(AzureOpenAIConfig(
            api_key=azure_config["api_key"],
            endpoint=azure_config["endpoint"],
            api_version=azure_config.get("api_version", "2023-05-15"),
            model=azure_config.get("model", AZURE_OPENAI_DEFAULT_MODEL)
        )))
        
    return None

def main():
    st.set_page_config(page_title="Document Translator", layout="wide")
    
    # Language selector in the top right corner
    col1, col2 = st.columns([6, 1])
    with col2:
        ui_language = st.selectbox("🌐", options=list(UI_LANGUAGES.keys()), key="ui_language")
    
    # Get text based on selected language
    txt = UI_LANGUAGES[ui_language]
    
    with col1:
        st.title(txt["app_title"])

    # Sidebar for configuration
    with st.sidebar:
        st.header(txt["configuration"])
        service_type = st.radio(txt["select_service"], ["OpenAI", "Azure OpenAI"], key="service_type")
        
        # Configuration section
        st.subheader(txt["api_configuration"])
        config = load_config()
        
        if service_type == "OpenAI":
            api_key = st.text_input("OpenAI API Key", 
                                  value=config.get("openai", {}).get("api_key", ""),
                                  type="password")
            base_url = st.text_input("Base URL (Optional)", 
                                   value=config.get("openai", {}).get("base_url", OPENAI_DEFAULT_BASE_URL))
            model = st.text_input("Model (Optional)", 
                                value=config.get("openai", {}).get("model", OPENAI_DEFAULT_MODEL))
            
            if st.button(txt["save_config"].format("OpenAI")):
                if not api_key:
                    st.error(txt["api_key_required"])
                else:
                    config["openai"] = {
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model
                    }
                    save_config(config)
                    st.success(txt["config_saved"].format("OpenAI"))
        
        else:  # Azure OpenAI
            api_key = st.text_input("Azure OpenAI API Key", 
                                  value=config.get("azure_openai", {}).get("api_key", ""),
                                  type="password")
            endpoint = st.text_input("Endpoint", 
                                   value=config.get("azure_openai", {}).get("endpoint", ""))
            model = st.selectbox("Model (Optional)", 
                               options=list(AZURE_MODELS.keys()),
                               index=0)
            
            if st.button(txt["save_config"].format("Azure OpenAI")):
                if not api_key or not endpoint:
                    st.error(txt["both_required"])
                else:
                    config["azure_openai"] = {
                        "api_key": api_key,
                        "endpoint": endpoint,
                        "model": model
                    }
                    save_config(config)
                    st.success(txt["config_saved"].format("Azure OpenAI"))

    # Main content
    target_language = st.selectbox(txt["target_language"], 
                                 options=list(SUPPORTED_LANGUAGES.keys()),
                                 index=list(SUPPORTED_LANGUAGES.keys()).index(DEFAULT_TARGET_LANGUAGE))

    # Add tabs for different translation modes
    tab1, tab2 = st.tabs([txt["text_translation"], txt["document_translation"]])

    with tab1:
        st.subheader(txt["text_translation"])
        input_text = st.text_area(txt["enter_text"], height=200)
        if st.button(txt["translate_text"]):
            if not input_text.strip():
                st.warning(txt["please_enter_text"])
            else:
                translator = get_translator(service_type.lower().replace(" ", ""))
                if translator:
                    with st.spinner(txt["translating"]):
                        try:
                            translated_text = translator.translate(input_text, SUPPORTED_LANGUAGES[target_language])
                            st.text_area(txt["translated_text"], value=translated_text, height=200)
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")
                else:
                    st.warning(txt["configure_api"])

    with tab2:
        st.subheader(txt["document_translation"])
        uploaded_file = st.file_uploader(txt["choose_file"], type=['docx'])
        
        if uploaded_file is not None:
            st.success(txt["file_uploaded"].format(uploaded_file.name))
            
            # Show file info
            file_details = {
                txt["file_info"]["filename"]: uploaded_file.name,
                txt["file_info"]["filesize"]: f"{uploaded_file.size / 1024:.2f} KB"
            }
            st.json(file_details)
            
            # Create translator
            translator = get_translator(service_type.lower().replace(" ", ""))
            
            if translator:
                col1, col2 = st.columns([1, 2])
                with col1:
                    if st.button(txt["start_translation"], use_container_width=True):
                        with st.spinner(txt["translating"]):
                            try:
                                # Progress bar
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                # Save uploaded file temporarily
                                status_text.text(txt["preparing_doc"])
                                progress_bar.progress(10)
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_input:
                                    tmp_input.write(uploaded_file.getvalue())
                                    input_path = tmp_input.name
                                
                                progress_bar.progress(30)
                                status_text.text(txt["translating_content"])
                                
                                # Create output path
                                output_filename = f"translated_{uploaded_file.name}"
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_output:
                                    output_path = tmp_output.name
                                
                                # Translate document
                                docx_translator = DocxTranslator(translator)
                                docx_translator.translate_document(input_path, output_path, SUPPORTED_LANGUAGES[target_language])
                                
                                progress_bar.progress(80)
                                status_text.text(txt["preparing_download"])
                                
                                # Offer download
                                with open(output_path, 'rb') as file:
                                    file_content = file.read()
                                    
                                progress_bar.progress(100)
                                status_text.text(txt["translation_completed"])
                                
                                # Show download button in a prominent way
                                st.success(txt["translation_completed"])
                                st.download_button(
                                    label=txt["download_translated"],
                                    data=file_content,
                                    file_name=output_filename,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    use_container_width=True
                                )
                                
                                # Cleanup temporary files
                                os.unlink(input_path)
                                os.unlink(output_path)
                                
                            except Exception as e:
                                st.error(f"An error occurred: {str(e)}")
                                if 'progress_bar' in locals():
                                    progress_bar.empty()
                                if 'status_text' in locals():
                                    status_text.empty()
                
                with col2:
                    st.info(txt["translation_process"])
            else:
                st.warning(txt["configure_api"])
        else:
            st.info(txt["upload_prompt"])

if __name__ == "__main__":
    main()
