"""
Script: export_conversation_docx.py
Descrição: Converte o histórico completo da conversa (.jsonl) em um documento do Microsoft Word (.docx) 
com formatação profissional (títulos, estilos, cores da Shopee e cabeçalhos de mensagens).
"""

import os
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

TRANSCRIPT_PATH = "/Users/paulovasconcelos/.gemini/antigravity/brain/5c02b062-8dee-4138-afd4-5abf6c048944/.system_generated/logs/transcript_full.jsonl"
OUTPUT_DOCX = "/Users/paulovasconcelos/Documents/Carrinho/Conversacao_Projeto_ML_Carrinho_Shopee.docx"
OUTPUT_MD = "/Users/paulovasconcelos/Documents/Carrinho/Conversacao_Projeto_ML_Carrinho_Shopee.md"


def parse_transcript(jsonl_path):
    messages = []
    if not os.path.exists(jsonl_path):
        jsonl_path = jsonl_path.replace("transcript_full.jsonl", "transcript.jsonl")
        
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                step = json.loads(line)
                step_type = step.get("type", "")
                content = step.get("content", "")
                
                # Captura os inputs do usuário
                if step_type == "USER_INPUT":
                    if content and not content.startswith("[Notice]") and not content.startswith("Error invalid tool call"):
                        messages.append({
                            "role": "USER",
                            "text": content,
                            "timestamp": step.get("created_at", "")
                        })
                # Captura as respostas do assistente
                elif step_type == "PLANNER_RESPONSE":
                    if content:
                        messages.append({
                            "role": "ASSISTANT",
                            "text": content,
                            "timestamp": step.get("created_at", "")
                        })
            except Exception:
                pass
                
    # Deduplica ou organiza se necessário
    return messages


def escape_xml(text):
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


def create_docx(messages, output_docx):
    # XML templates para compor o .docx
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:docDefaults>
        <w:rPrDefault>
            <w:rPr>
                <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                <w:sz w:val="22"/>
                <w:color w:val="1F2937"/>
            </w:rPr>
        </w:rPrDefault>
    </w:docDefaults>
</w:styles>"""

    # Construção dos parágrafos no word/document.xml
    body_paragraphs = []
    
    # Título do Documento
    body_paragraphs.append("""
    <w:p>
        <w:pPr>
            <w:pStyle w:val="Heading1"/>
            <w:jc w:val="center"/>
            <w:spacing w:before="240" w:after="120"/>
        </w:pPr>
        <w:r>
            <w:rPr>
                <w:b/>
                <w:sz w:val="36"/>
                <w:color w:val="FF5722"/>
            </w:rPr>
            <w:t>Relatório da Conversa - Projeto de Machine Learning (Shopee Cart)</w:t>
        </w:r>
    </w:p>
    """)
    
    # Subtítulo
    sub_text = f"MBA em Engenharia de Dados - Mackenzie | Exportado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
    body_paragraphs.append(f"""
    <w:p>
        <w:pPr>
            <w:jc w:val="center"/>
            <w:spacing w:after="360"/>
        </w:pPr>
        <w:r>
            <w:rPr>
                <w:i/>
                <w:sz w:val="20"/>
                <w:color w:val="6B7280"/>
            </w:rPr>
            <w:t>{escape_xml(sub_text)}</w:t>
        </w:r>
    </w:p>
    """)

    # Adiciona cada mensagem da conversa
    for msg in messages:
        role = msg["role"]
        raw_text = msg["text"]
        
        if role == "USER":
            header_color = "2563EB" # Azul
            header_text = "👤 SOLICITAÇÃO DO USUÁRIO"
            bg_shading = "F0F9FF"
        else:
            header_color = "FF5722" # Laranja Shopee
            header_text = "🤖 RESPOSTA DO ASSISTENTE (ANTIGRAVITY)"
            bg_shading = "FFF7ED"
            
        # Cabeçalho da mensagem
        body_paragraphs.append(f"""
        <w:p>
            <w:pPr>
                <w:spacing w:before="240" w:after="60"/>
                <w:pBdr>
                    <w:bottom w:val="single" w:sz="12" w:space="4" w:color="{header_color}"/>
                </w:pBdr>
            </w:pPr>
            <w:r>
                <w:rPr>
                    <w:b/>
                    <w:sz w:val="24"/>
                    <w:color w:val="{header_color}"/>
                </w:rPr>
                <w:t>{escape_xml(header_text)}</w:t>
            </w:r>
        </w:p>
        """)
        
        # Parágrafos do texto da mensagem
        lines = raw_text.split("\n")
        for line in lines:
            if not line.strip():
                continue
            escaped_line = escape_xml(line)
            body_paragraphs.append(f"""
            <w:p>
                <w:pPr>
                    <w:spacing w:after="100" w:line="276" w:lineRule="auto"/>
                </w:pPr>
                <w:r>
                    <w:rPr>
                        <w:sz w:val="22"/>
                        <w:color w:val="1F2937"/>
                    </w:rPr>
                    <w:t xml:space="preserve">{escaped_line}</w:t>
                </w:r>
            </w:p>
            """)

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        {"".join(body_paragraphs)}
        <w:sectPr>
            <w:pgSz w:w="12240" w:h="15840"/>
            <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
        </w:sectPr>
    </w:body>
</w:document>"""

    # Pacote de arquivos no arquivo ZIP .docx
    with zipfile.ZipFile(output_docx, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types_xml)
        docx.writestr("_rels/.rels", rels_xml)
        docx.writestr("word/_rels/document.xml.rels", doc_rels_xml)
        docx.writestr("word/styles.xml", styles_xml)
        docx.writestr("word/document.xml", document_xml)
        
    print(f"Documento Word salvo com sucesso em: {output_docx}")


def create_md(messages, output_md):
    md_lines = [
        "# Relatório da Conversa - Projeto de Machine Learning (Shopee Cart)",
        f"*MBA em Engenharia de Dados - Mackenzie | Exportado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}*\n",
        "---"
    ]
    for msg in messages:
        if msg["role"] == "USER":
            md_lines.append(f"\n### 👤 SOLICITAÇÃO DO USUÁRIO\n")
        else:
            md_lines.append(f"\n### 🤖 RESPOSTA DO ASSISTENTE (ANTIGRAVITY)\n")
        md_lines.append(msg["text"])
        md_lines.append("\n---")
        
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Documento Markdown salvo com sucesso em: {output_md}")


if __name__ == "__main__":
    msgs = parse_transcript(TRANSCRIPT_PATH)
    print(f"Total de mensagens extraídas do histórico: {len(msgs)}")
    create_docx(msgs, OUTPUT_DOCX)
    create_md(msgs, OUTPUT_MD)
