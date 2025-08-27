#!/usr/bin/env python3
"""
Verilog Analyzer MCP Server

This MCP server exposes Verilog analysis functionality as tools that can be used
by LLMs to interactively analyze Verilog files and generate specification documents.
"""

import asyncio
import os
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

# Import our existing Verilog analyzer
from verilog_analyzer import VerilogAnalyzer, VerilogModule

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verilog-mcp-server")

# Global analyzer instance
analyzer_instance: Optional[VerilogAnalyzer] = None

# Create the MCP server
server = Server("verilog-analyzer")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available Verilog analysis tools"""
    return [
        Tool(
            name="initialize_analyzer",
            description="Initialize the Verilog analyzer with configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Path to configuration file (default: config.yaml)",
                        "default": "config.yaml"
                    }
                }
            }
        ),
        Tool(
            name="load_verilog_files",
            description="Load Verilog files from a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "Directory path containing Verilog files"
                    }
                },
                "required": ["input_dir"]
            }
        ),
        Tool(
            name="get_loaded_modules",
            description="Get information about currently loaded Verilog modules",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="parse_verilog_file",
            description="Parse a specific Verilog file and extract module information",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Verilog file to parse"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="extract_ports",
            description="Extract port information from Verilog code",
            inputSchema={
                "type": "object",
                "properties": {
                    "verilog_code": {
                        "type": "string",
                        "description": "Verilog code to analyze for ports"
                    }
                },
                "required": ["verilog_code"]
            }
        ),
        Tool(
            name="analyze_single_module",
            description="Perform LLM analysis on a specific module",
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to analyze"
                    }
                },
                "required": ["module_name"]
            }
        ),
        Tool(
            name="analyze_all_modules",
            description="Perform LLM analysis on all loaded modules",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="generate_latex_document",
            description="Generate LaTeX specification document from analyzed modules",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_path": {
                        "type": "string",
                        "description": "Path to LaTeX template file",
                        "default": "template.tex"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for generated LaTeX document"
                    }
                }
            }
        ),
        Tool(
            name="run_complete_analysis",
            description="Run the complete analysis pipeline from directory to LaTeX document",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "Directory path containing Verilog files"
                    },
                    "template_path": {
                        "type": "string",
                        "description": "Path to LaTeX template file",
                        "default": "template.tex"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for generated LaTeX document"
                    }
                },
                "required": ["input_dir"]
            }
        ),
        Tool(
            name="get_module_details",
            description="Get detailed information about a specific module",
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to get details for"
                    }
                },
                "required": ["module_name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls"""
    global analyzer_instance
    
    try:
        if name == "initialize_analyzer":
            config_path = arguments.get("config_path", "config.yaml")
            analyzer_instance = VerilogAnalyzer(config_path)
            return [types.TextContent(
                type="text",
                text=f"Verilog analyzer initialized successfully with config: {config_path}"
            )]
        
        # Ensure analyzer is initialized for other operations
        if analyzer_instance is None:
            analyzer_instance = VerilogAnalyzer()
        
        if name == "load_verilog_files":
            input_dir = arguments["input_dir"]
            if not os.path.exists(input_dir):
                return [types.TextContent(
                    type="text",
                    text=f"Error: Directory {input_dir} does not exist"
                )]
            
            analyzer_instance.load_verilog_files(input_dir)
            module_names = [module.name for module in analyzer_instance.modules]
            
            return [types.TextContent(
                type="text",
                text=f"Successfully loaded {len(analyzer_instance.modules)} Verilog modules from {input_dir}:\n" + 
                     f"Modules: {', '.join(module_names)}"
            )]
        
        elif name == "get_loaded_modules":
            if not analyzer_instance.modules:
                return [types.TextContent(
                    type="text",
                    text="No modules currently loaded. Use load_verilog_files first."
                )]
            
            modules_info = []
            for module in analyzer_instance.modules:
                modules_info.append(f"- {module.name} (from {module.filename})")
            
            return [types.TextContent(
                type="text",
                text=f"Currently loaded modules ({len(analyzer_instance.modules)}):\n" + 
                     "\n".join(modules_info)
            )]
        
        elif name == "parse_verilog_file":
            file_path = arguments["file_path"]
            if not os.path.exists(file_path):
                return [types.TextContent(
                    type="text",
                    text=f"Error: File {file_path} does not exist"
                )]
            
            # Parse the file
            analyzer_instance._parse_verilog_file(file_path)
            
            # Find the newly parsed module
            module = analyzer_instance.modules[-1] if analyzer_instance.modules else None
            if module:
                return [types.TextContent(
                    type="text",
                    text=f"Successfully parsed {file_path}:\n" +
                         f"Module: {module.name}\n" +
                         f"Inputs: {', '.join(module.ports['inputs']) if module.ports['inputs'] else 'None'}\n" +
                         f"Outputs: {', '.join(module.ports['outputs']) if module.ports['outputs'] else 'None'}\n" +
                         f"Parameters: {', '.join([f'{p[0]}={p[1]}' for p in module.ports['parameters']]) if module.ports['parameters'] else 'None'}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to parse module from {file_path}"
                )]
        
        elif name == "extract_ports":
            verilog_code = arguments["verilog_code"]
            ports = analyzer_instance._extract_ports(verilog_code)
            
            return [types.TextContent(
                type="text",
                text=f"Extracted ports from Verilog code:\n" +
                     f"Inputs: {', '.join(ports['inputs']) if ports['inputs'] else 'None'}\n" +
                     f"Outputs: {', '.join(ports['outputs']) if ports['outputs'] else 'None'}\n" +
                     f"Parameters: {', '.join([f'{p[0]}={p[1]}' for p in ports['parameters']]) if ports['parameters'] else 'None'}"
            )]
        
        elif name == "analyze_single_module":
            module_name = arguments["module_name"]
            module = next((m for m in analyzer_instance.modules if m.name == module_name), None)
            
            if not module:
                return [types.TextContent(
                    type="text",
                    text=f"Module '{module_name}' not found. Available modules: {', '.join([m.name for m in analyzer_instance.modules])}"
                )]
            
            analysis = analyzer_instance._analyze_single_module(module)
            module.analysis = analysis
            
            return [types.TextContent(
                type="text",
                text=f"Analysis completed for module '{module_name}':\n\n{analysis}"
            )]
        
        elif name == "analyze_all_modules":
            if not analyzer_instance.modules:
                return [types.TextContent(
                    type="text",
                    text="No modules loaded. Use load_verilog_files first."
                )]
            
            analyzer_instance.analyze_modules()
            
            results = []
            for module in analyzer_instance.modules:
                results.append(f"Module: {module.name}\nAnalysis: {module.analysis[:200]}...")
            
            return [types.TextContent(
                type="text",
                text=f"Analysis completed for {len(analyzer_instance.modules)} modules:\n\n" + 
                     "\n\n".join(results)
            )]
        
        elif name == "generate_latex_document":
            if not analyzer_instance.modules:
                return [types.TextContent(
                    type="text",
                    text="No modules loaded. Load and analyze modules first."
                )]
            
            template_path = arguments.get("template_path", "template.tex")
            output_path = arguments.get("output_path")
            
            analyzer_instance.generate_latex_document(template_path, output_path)
            
            final_output = output_path or analyzer_instance.config['output']['latex_filename']
            return [types.TextContent(
                type="text",
                text=f"LaTeX document generated successfully: {final_output}"
            )]
        
        elif name == "run_complete_analysis":
            input_dir = arguments["input_dir"]
            template_path = arguments.get("template_path", "template.tex")
            output_path = arguments.get("output_path")
            
            analyzer_instance.run_complete_analysis(input_dir, template_path, output_path)
            
            final_output = output_path or analyzer_instance.config['output']['latex_filename']
            return [types.TextContent(
                type="text",
                text=f"Complete analysis pipeline finished successfully!\n" +
                     f"Processed {len(analyzer_instance.modules)} modules\n" +
                     f"Generated document: {final_output}\n" +
                     f"Modules: {', '.join([m.name for m in analyzer_instance.modules])}"
            )]
        
        elif name == "get_module_details":
            module_name = arguments["module_name"]
            module = next((m for m in analyzer_instance.modules if m.name == module_name), None)
            
            if not module:
                return [types.TextContent(
                    type="text",
                    text=f"Module '{module_name}' not found. Available modules: {', '.join([m.name for m in analyzer_instance.modules])}"
                )]
            
            details = f"Module: {module.name}\n"
            details += f"File: {module.filename}\n"
            details += f"Inputs: {', '.join(module.ports['inputs']) if module.ports['inputs'] else 'None'}\n"
            details += f"Outputs: {', '.join(module.ports['outputs']) if module.ports['outputs'] else 'None'}\n"
            details += f"Parameters: {', '.join([f'{p[0]}={p[1]}' for p in module.ports['parameters']]) if module.ports['parameters'] else 'None'}\n"
            details += f"Has Analysis: {'Yes' if module.analysis else 'No'}\n"
            
            if module.analysis:
                details += f"\nAnalysis Preview:\n{module.analysis[:300]}..."
            
            return [types.TextContent(
                type="text",
                text=details
            )]
        
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [types.TextContent(
            type="text",
            text=f"Error executing tool {name}: {str(e)}"
        )]

async def main():
    """Run the MCP server"""
    logger.info("Initializing Verilog Analyzer MCP Server")
    
    # Import the stdio server functionality
    from mcp.server.stdio import stdio_server
    
    logger.info("Starting Verilog Analyzer MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP server connected via stdio")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="verilog-analyzer",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
