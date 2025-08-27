#!/usr/bin/env python3
"""
Verilog Code Analyzer and LaTeX Documentation Generator

This script analyzes Verilog files using Azure OpenAI's GPT models and generates
a comprehensive specification document in LaTeX format based on a template.
"""

import os
import yaml
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass
import logging

try:
    from openai import AzureOpenAI
except ImportError:
    print("Error: OpenAI library not installed. Please run: pip install openai")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class VerilogModule:
    """Data class to store information about a Verilog module"""
    name: str
    filename: str
    code: str
    ports: Dict[str, Any]
    description: str = ""
    analysis: str = ""

class VerilogAnalyzer:
    """Main class for analyzing Verilog files and generating LaTeX documentation"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the analyzer with configuration"""
        self.config = self._load_config(config_path)
        self.client = self._initialize_openai_client()
        self.modules: List[VerilogModule] = []
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file {config_path} not found")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
    
    def _initialize_openai_client(self) -> AzureOpenAI:
        """Initialize Azure OpenAI client"""
        config = self.config['azure_openai']
        
        # Get configuration values
        api_key = config['api_key']
        endpoint = config['endpoint']
        api_version = config['api_version']
        
        # Handle environment variables
        if api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]  # Remove ${ and }
            api_key = os.getenv(env_var)
            if not api_key:
                logger.error(f"Azure OpenAI API key not found. Please set {env_var} environment variable or update config.yaml")
                raise ValueError("Azure OpenAI API key not configured")
        
        if endpoint.startswith('${') and endpoint.endswith('}'):
            env_var = endpoint[2:-1]  # Remove ${ and }
            endpoint = os.getenv(env_var)
            if not endpoint:
                logger.error(f"Azure OpenAI endpoint not found. Please set {env_var} environment variable or update config.yaml")
                raise ValueError("Azure OpenAI endpoint not configured")
        
        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
    
    def load_verilog_files(self, input_dir: str = None) -> None:
        """Load all Verilog files from the input directory"""
        if input_dir is None:
            input_dir = self.config['input']['directory']
        
        extensions = self.config['input']['file_extensions']
        verilog_files = []
        
        for ext in extensions:
            pattern = os.path.join(input_dir, f"*{ext}")
            verilog_files.extend(glob.glob(pattern))
        
        logger.info(f"Found {len(verilog_files)} Verilog files")
        
        for file_path in verilog_files:
            self._parse_verilog_file(file_path)
    
    def _parse_verilog_file(self, file_path: str) -> None:
        """Parse a single Verilog file and extract module information"""
        try:
            with open(file_path, 'r') as file:
                code = file.read()
            
            # Extract module name using regex
            module_match = re.search(r'module\s+(\w+)', code)
            if not module_match:
                logger.warning(f"No module found in {file_path}")
                return
            
            module_name = module_match.group(1)
            filename = os.path.basename(file_path)
            
            # Extract ports (simplified parsing)
            ports = self._extract_ports(code)
            
            module = VerilogModule(
                name=module_name,
                filename=filename,
                code=code,
                ports=ports
            )
            
            self.modules.append(module)
            logger.info(f"Loaded module '{module_name}' from {filename}")
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
    
    def _extract_ports(self, code: str) -> Dict[str, Any]:
        """Extract port information from Verilog code (simplified)"""
        ports = {'inputs': [], 'outputs': [], 'parameters': []}
        
        # Find input ports
        input_matches = re.findall(r'input\s+(?:wire\s+|reg\s+)?(?:\[[\d:\s]+\]\s+)?(\w+)', code)
        ports['inputs'] = input_matches
        
        # Find output ports
        output_matches = re.findall(r'output\s+(?:wire\s+|reg\s+)?(?:\[[\d:\s]+\]\s+)?(\w+)', code)
        ports['outputs'] = output_matches
        
        # Find parameters
        param_matches = re.findall(r'parameter\s+(\w+)\s*=\s*([^,\)]+)', code)
        ports['parameters'] = param_matches
        
        return ports
    
    def analyze_modules(self) -> None:
        """Analyze all loaded modules using LLM"""
        logger.info("Starting LLM analysis of modules...")
        
        for module in self.modules:
            logger.info(f"Analyzing module: {module.name}")
            analysis = self._analyze_single_module(module)
            module.analysis = analysis
    
    def _analyze_single_module(self, module: VerilogModule) -> str:
        """Analyze a single Verilog module using LLM"""
        prompt = self._create_analysis_prompt(module)
        
        try:
            response = self.client.chat.completions.create(
                model=self.config['azure_openai']['deployment_name'],
                messages=[
                    {"role": "system", "content": "You are an expert digital design engineer specializing in Verilog HDL analysis and documentation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config['azure_openai']['temperature'],
                max_tokens=self.config['azure_openai']['max_tokens']
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error analyzing module {module.name}: {e}")
            return f"Analysis failed for module {module.name}: {str(e)}"
    
    def _create_analysis_prompt(self, module: VerilogModule) -> str:
        """Create a detailed analysis prompt for the LLM"""
        sections = self.config['analysis']['include_sections']
        max_length = self.config['analysis']['output_format']['max_section_length']
        
        prompt = f"""
        Analyze the following Verilog module and provide a comprehensive technical analysis suitable for a specification document.

        Module Name: {module.name}
        File: {module.filename}

        Verilog Code:
        ```verilog
        {module.code}
        ```

        Please provide analysis covering these sections (keep each section under {max_length} words):
        """
        
        section_descriptions = {
            'functionality_overview': 'High-level description of what this module does',
            'module_interface': 'Detailed description of inputs, outputs, and parameters',
            'behavioral_description': 'How the module behaves and its internal logic',
            'timing_analysis': 'Clock domains, timing constraints, and synchronization',
            'design_patterns': 'Design patterns and coding practices used',
            'potential_improvements': 'Suggestions for optimization or enhancement',
            'test_considerations': 'Testing strategies and verification considerations'
        }
        
        for section in sections:
            if section in section_descriptions:
                prompt += f"\n- {section.replace('_', ' ').title()}: {section_descriptions[section]}"
        
        prompt += """

        Format your response as clear, technical prose suitable for inclusion in an professional specification document. 
        Use proper technical terminology and maintain a professional tone throughout.
        Focus on the design intent, functionality, and implementation details. Do not include any other text or comments. Do not output in markdown format.
        """
        
        return prompt
    
    def generate_latex_document(self, template_path: str = "template.tex", output_path: str = None) -> None:
        """Generate LaTeX documentation using the template"""
        if output_path is None:
            output_path = self.config['output']['latex_filename']
        
        logger.info(f"Generating LaTeX document: {output_path}")
        
        # Read the template
        with open(template_path, 'r') as file:
            template_content = file.read()
        
        # Generate complete document content with LLM-defined structure
        document_content = self._generate_complete_document()
        
        # Replace all content between \begin{document} and \end{document}
        template_content = self._replace_entire_document_content(template_content, document_content)
        
        # Write the output file
        with open(output_path, 'w') as file:
            file.write(template_content)
        
        logger.info(f"LaTeX document generated successfully: {output_path}")
    

    
    def _generate_complete_document(self) -> str:
        """Generate the complete document content with LLM-defined structure"""
        # Prepare detailed module information for the LLM
        detailed_modules = []
        for module in self.modules:
            detailed_modules.append({
                'name': module.name,
                'filename': module.filename,
                'code': module.code,
                'analysis': module.analysis,
                'ports': module.ports
            })
        
        # Create comprehensive prompt for entire document
        document_prompt = f"""
        Create a comprehensive digital design specification document for the following Verilog modules. 
        You have complete freedom to create appropriate headings and structure the document as you see fit.
        
        MODULES TO ANALYZE:
        {self._format_modules_for_prompt(detailed_modules)}
        
        FORMATTING REQUIREMENTS:
        - Use LaTeX formatting (\\section{{}}, \\subsection{{}}, etc.)
        - Do NOT include \\documentclass, \\usepackage, \\begin{{document}} or \\end{{document}} 
        - Do NOT include any preamble or document setup commands
        - ONLY provide the content that goes inside the document body
        - Start with a title page using \\begin{{center}} environment
        - After the title page, add: \\newpage followed by \\tableofcontents followed by \\newpage
        - Include detailed technical analysis of each module
        - Create logical sections and subsections as appropriate
        - Use proper LaTeX syntax for all formatting
        - Include academic-style content suitable for a university specification document
        
        CONTENT REQUIREMENTS:
        1. Title page (center environment with title, institution, date)
        2. Table of contents (\\tableofcontents)
        3. Create an introduction/overview section
        4. For EACH module, create a dedicated section with:
           - Complete code listing (use \\begin{{verbatim}} \\end{{verbatim}} for code)
           - Detailed functional analysis
           - Interface description (inputs, outputs, parameters)
           - Behavioral analysis
           - Timing considerations
           - Design patterns used
           - Potential improvements
        5. Create a conclusions/summary section
        6. Add any other sections you deem appropriate (references, appendices, etc.)
        
        Make the document comprehensive, technical, and professionally structured.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.config['azure_openai']['deployment_name'],
                messages=[
                    {"role": "system", "content": "You are an expert digital design engineer and technical writer. Create comprehensive, professional documentation."},
                    {"role": "user", "content": document_prompt}
                ],
                temperature=self.config['azure_openai']['temperature'],
                max_tokens=4000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating document content: {e}")
            return self._generate_fallback_document()
    
    def _format_modules_for_prompt(self, modules) -> str:
        """Format module information for the LLM prompt"""
        formatted = []
        for module in modules:
            formatted.append(f"""
MODULE: {module['name']} (File: {module['filename']})
CODE:
```verilog
{module['code']}
```

ANALYSIS:
{module['analysis']}

INTERFACE:
- Inputs: {', '.join(module['ports']['inputs']) if module['ports']['inputs'] else 'None'}
- Outputs: {', '.join(module['ports']['outputs']) if module['ports']['outputs'] else 'None'}
- Parameters: {', '.join([f"{p[0]}={p[1]}" for p in module['ports']['parameters']]) if module['ports']['parameters'] else 'None'}
""")
        return '\n'.join(formatted)
    
    def _generate_fallback_document(self) -> str:
        """Generate a fallback document if LLM generation fails"""
        content = """
\\begin{center}
{\\Huge{Verilog Module Specification}} \\\\
\\vspace{2mm}
{\\Large{Digital Design Analysis}} \\\\
\\vspace{1mm}
{\\Large{Technical Documentation}}
\\end{center}

\\newpage
\\tableofcontents
\\newpage

\\section{Introduction}
This document provides a comprehensive analysis of Verilog modules for digital design applications.

\\section{Module Analysis}
Detailed analysis of each module would be provided here.

\\section{Conclusions}
Summary and conclusions would be provided here.
"""
        return content
    
    def _replace_entire_document_content(self, template_content: str, new_content: str) -> str:
        """Replace everything between \\begin{document} and \\end{document}"""
        begin_doc = template_content.find('\\begin{document}')
        end_doc = template_content.find('\\end{document}')
        
        if begin_doc == -1 or end_doc == -1:
            logger.error("Could not find document boundaries in template")
            return template_content
        
        # Keep everything before \\begin{document} and after \\end{document}
        before_doc = template_content[:begin_doc + len('\\begin{document}')]
        after_doc = template_content[end_doc:]
        
        # Insert new content
        new_document = before_doc + '\n\n' + new_content + '\n\n' + after_doc
        
        return new_document
    

    
    def run_complete_analysis(self, input_dir: str = None, template_path: str = "template.tex", output_path: str = None) -> None:
        """Run the complete analysis pipeline"""
        logger.info("Starting complete Verilog analysis pipeline...")
        
        # Load Verilog files
        self.load_verilog_files(input_dir)
        
        if not self.modules:
            logger.error("No Verilog modules found. Exiting.")
            return
        
        # Analyze modules with LLM
        self.analyze_modules()
        
        # Generate LaTeX document
        self.generate_latex_document(template_path, output_path)
        
        logger.info("Analysis pipeline completed successfully!")
        
        # Print summary
        print(f"\nAnalysis Summary:")
        print(f"- Processed {len(self.modules)} Verilog modules")
        print(f"- Generated LaTeX document: {output_path or self.config['output']['latex_filename']}")
        print(f"- Modules analyzed: {', '.join([m.name for m in self.modules])}")

def main():
    """Main function to run the analyzer"""
    try:
        analyzer = VerilogAnalyzer()
        analyzer.run_complete_analysis()
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
